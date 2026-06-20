"""
API d'administration (montée sur le serveur principal — port API).

GET  /admin/api/catalogues                     → liste enrichie (admin)
GET  /admin/api/catalogues/{slug}              → détail complet (admin)
GET  /admin/api/catalogues/{slug}/contenu      → contenu allégé (sans images/vidéos)
PUT  /admin/api/catalogues/{slug}              → mise à jour métadonnées (admin)
PUT  /admin/api/catalogues/{slug}/visibility   → mise à jour visibilité (admin)

GET    /admin/api/clients                      → liste des clients API (admin)
POST   /admin/api/clients                      → créer un client (retourne le secret une fois)
GET    /admin/api/clients/{cid}                → détail d'un client (admin)
PUT    /admin/api/clients/{cid}                → modifier un client (admin)
DELETE /admin/api/clients/{cid}                → supprimer un client (admin)
POST   /admin/api/clients/{cid}/regenerate-secret → nouveau secret (admin)

GET    /admin/api/schedules                    → liste des programmations auto (admin)
POST   /admin/api/schedules                    → créer une programmation (admin)
PUT    /admin/api/schedules/{sid}              → modifier une programmation (admin)
DELETE /admin/api/schedules/{sid}              → supprimer une programmation (admin)
POST   /admin/api/schedules/{sid}/run          → déclencher manuellement (admin)

GET    /admin/api/history                      → historique des syncs (admin)
GET    /admin/api/history/{slug}               → historique d'un catalogue (admin)
"""

import secrets as _secrets
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from models.catalogue import CatalogueVisibility
from models.api_client import APIClientCreate, APIClientUpdate
from models.schedule import ScheduleCreate, ScheduleUpdate
import db.repository as repo
import db.clients_repository as clients_repo
import db.schedules_repository as schedules_repo
import db.sync_history_repository as history_repo
from api.dependencies import require_admin, hash_password
import services.scheduler_service as sched_svc

router = APIRouter(prefix="/admin", tags=["Administration"])


# ---------------------------------------------------------------------------
# Helpers clients
# ---------------------------------------------------------------------------

def _new_client_id() -> str:
    return "cli_" + _secrets.token_urlsafe(16)


def _new_secret() -> tuple[str, str]:
    """Retourne (secret_plain, secret_hash)."""
    plain = _secrets.token_urlsafe(32)
    return plain, hash_password(plain)


# ---------------------------------------------------------------------------
# Modèles
# ---------------------------------------------------------------------------

class CatalogueMetaUpdate(BaseModel):
    nom:              Optional[str]       = None
    titre_alternatif: Optional[str]       = None
    synopsis:         Optional[str]       = None
    genres:           Optional[list[str]] = None
    langues:          Optional[list[str]] = None
    etat:             Optional[str]       = None
    type_contenu:     Optional[str]       = None


# ---------------------------------------------------------------------------
# Catalogues
# ---------------------------------------------------------------------------

@router.get("/api/catalogues", summary="Catalogues avec visibilité et statut (admin)")
async def list_catalogues_admin(_: dict = Depends(require_admin)):
    items = await repo.get_all_summary()
    result = []
    for item in items:
        doc = await repo.find_by_slug(item["slug"])
        if doc:
            result.append(_catalogue_summary(doc))
    return result


@router.get("/api/catalogues/{slug}", summary="Détail complet d'un catalogue (admin)")
async def get_catalogue_admin(slug: str, _: dict = Depends(require_admin)):
    doc = await repo.find_by_slug(slug)
    if not doc:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")
    return doc


@router.get("/api/catalogues/{slug}/contenu", summary="Contenu allégé d'un catalogue (admin)")
async def get_catalogue_content(slug: str, _: dict = Depends(require_admin)):
    """Retourne épisodes/chapitres avec URLs lecteurs (sans images)."""
    doc = await repo.find_by_slug(slug)
    if not doc:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")

    def _vids(raw: list) -> list:
        return [{"lecteur": v.get("lecteur"), "player_url": v.get("player_url")}
                for v in raw if v.get("player_url")]

    saisons = []
    for i, s in enumerate(doc.get("saisons", [])):
        eps = s.get("episodes", [])
        saisons.append({
            "index":          i,
            "slug":           s.get("slug"),
            "nom":            s.get("nom"),
            "lang":           s.get("lang"),
            "url":            s.get("url"),
            "total_episodes": s.get("total_episodes", len(eps)),
            "episodes": [
                {"numero": e.get("numero"), "titre": e.get("titre"),
                 "videos": _vids(e.get("videos", []))}
                for e in eps
            ],
        })

    films = []
    for j, f in enumerate(doc.get("films", [])):
        vids = f.get("videos", [])
        films.append({
            "index":        j,
            "slug":         f.get("slug"),
            "nom":          f.get("nom"),
            "lang":         f.get("lang"),
            "url":          f.get("url"),
            "videos_count": len(vids),
            "videos":       _vids(vids),
            "lecteurs":     [v.get("lecteur") for v in vids if v.get("lecteur")],
        })

    scans = []
    for k, sc in enumerate(doc.get("scans", [])):
        chaps = sc.get("chapitres", [])
        scans.append({
            "index":           k,
            "slug":            sc.get("slug"),
            "nom":             sc.get("nom"),
            "lang":            sc.get("lang"),
            "url":             sc.get("url"),
            "total_chapitres": len(chaps),
            "chapitres":       [{"numero": c.get("numero"), "titre": c.get("titre")} for c in chaps],
        })

    return {
        "slug":            doc.get("slug"),
        "nom":             doc.get("nom"),
        "episodes_synced": doc.get("episodes_synced", False),
        "saisons":         saisons,
        "films":           films,
        "scans":           scans,
    }


@router.delete("/api/catalogues/{slug}", status_code=204, summary="Supprimer un catalogue (admin)")
async def delete_catalogue(slug: str, _: dict = Depends(require_admin)):
    deleted = await repo.delete_by_slug(slug)
    if not deleted:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")


@router.put("/api/catalogues/{slug}", summary="Mise à jour des métadonnées (admin)")
async def update_catalogue_meta(
    slug: str,
    body: CatalogueMetaUpdate,
    _:    dict = Depends(require_admin),
):
    found = await repo.update_catalogue_metadata(slug, body.model_dump(exclude_none=True))
    if not found:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")
    return {"ok": True}


@router.put("/api/catalogues/{slug}/visibility", summary="Mise à jour de la visibilité (admin)")
async def update_visibility(
    slug: str,
    body: CatalogueVisibility,
    _:    dict = Depends(require_admin),
):
    found = await repo.update_catalogue_visibility(slug, body.model_dump())
    if not found:
        raise HTTPException(404, f"Catalogue '{slug}' introuvable")
    return {"ok": True, "slug": slug, "visibility": body.model_dump()}


# ---------------------------------------------------------------------------
# Clients API
# ---------------------------------------------------------------------------

@router.get("/api/clients", summary="Liste des clients API (admin)")
async def list_api_clients(_: dict = Depends(require_admin)):
    return await clients_repo.list_clients()


@router.post("/api/clients", status_code=201, summary="Créer un client API (admin)")
async def create_api_client(body: APIClientCreate, _: dict = Depends(require_admin)):
    """
    Crée un nouveau client API. Le secret est retourné **une seule fois** dans
    cette réponse — il ne peut pas être récupéré ensuite (seul le hash est stocké).
    """
    cid = _new_client_id()
    plain, hashed = _new_secret()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "client_id":          cid,
        "client_secret_hash": hashed,
        "name":               body.name,
        "description":        body.description,
        "is_active":          True,
        "permissions":        body.permissions.model_dump(),
        "created_at":         now,
        "updated_at":         now,
    }
    await clients_repo.create_client(doc)
    return {
        "client_id":     cid,
        "client_secret": plain,   # affiché une seule fois
        "name":          body.name,
        "is_active":     True,
        "permissions":   body.permissions.model_dump(),
        "created_at":    now,
    }


@router.get("/api/clients/{cid}", summary="Détail d'un client API (admin)")
async def get_api_client(cid: str, _: dict = Depends(require_admin)):
    doc = await clients_repo.find_by_client_id(cid)
    if not doc:
        raise HTTPException(404, f"Client '{cid}' introuvable")
    doc = dict(doc)
    doc.pop("client_secret_hash", None)
    doc["_id"] = str(doc.get("_id", ""))
    return doc


@router.put("/api/clients/{cid}", summary="Modifier un client API (admin)")
async def update_api_client(cid: str, body: APIClientUpdate, _: dict = Depends(require_admin)):
    fields: dict = {}
    if body.name        is not None: fields["name"]        = body.name
    if body.description is not None: fields["description"] = body.description
    if body.is_active   is not None: fields["is_active"]   = body.is_active
    if body.permissions is not None: fields["permissions"] = body.permissions.model_dump()
    if not fields:
        return {"ok": True}
    found = await clients_repo.update_client(cid, fields)
    if not found:
        raise HTTPException(404, f"Client '{cid}' introuvable")
    return {"ok": True}


@router.delete("/api/clients/{cid}", status_code=204, summary="Supprimer un client API (admin)")
async def delete_api_client(cid: str, _: dict = Depends(require_admin)):
    deleted = await clients_repo.delete_client(cid)
    if not deleted:
        raise HTTPException(404, f"Client '{cid}' introuvable")


@router.post("/api/clients/{cid}/regenerate-secret", summary="Régénérer le secret (admin)")
async def regenerate_client_secret(cid: str, _: dict = Depends(require_admin)):
    """
    Génère un nouveau secret et invalide l'ancien.
    Le nouveau secret est retourné **une seule fois**.
    """
    plain, hashed = _new_secret()
    found = await clients_repo.update_client(cid, {"client_secret_hash": hashed})
    if not found:
        raise HTTPException(404, f"Client '{cid}' introuvable")
    return {"client_id": cid, "client_secret": plain}


# ---------------------------------------------------------------------------
# Helpers catalogues
# ---------------------------------------------------------------------------

def _catalogue_summary(doc: dict) -> dict:
    return {
        "slug":             doc.get("slug"),
        "nom":              doc.get("nom"),
        "titre_alternatif": doc.get("titre_alternatif"),
        "synopsis":         (doc.get("synopsis") or "")[:200],
        "type_contenu":     doc.get("type_contenu", "anime"),
        "etat":             doc.get("etat", "en_cours"),
        "genres":           doc.get("genres", []),
        "langues":          doc.get("langues", []),
        "episodes_synced":  doc.get("episodes_synced", False),
        "updated_at":       doc.get("updated_at"),
        "created_at":       doc.get("created_at"),
        "saisons": [{"slug": s.get("slug"), "nom": s.get("nom"), "lang": s.get("lang"),
                     "total_episodes": s.get("total_episodes", 0)}
                    for s in doc.get("saisons", [])],
        "films":   [{"slug": f.get("slug"), "nom": f.get("nom"), "lang": f.get("lang")}
                    for f in doc.get("films", [])],
        "scans":   [{"slug": s.get("slug"), "nom": s.get("nom")}
                    for s in doc.get("scans", [])],
        "visibility": doc.get("visibility", {
            "is_public": True, "public_saisons": [], "public_films": [], "public_scans": [],
        }),
    }


# ---------------------------------------------------------------------------
# Programmations automatiques (schedules)
# ---------------------------------------------------------------------------

@router.get("/api/schedules", summary="Liste des programmations auto (admin)")
async def list_schedules(_: dict = Depends(require_admin)):
    schedules = await schedules_repo.list_all()
    # Enrichir avec la prochaine exécution APScheduler
    for s in schedules:
        s["next_run"] = sched_svc.get_next_run(s["id"])
    return schedules


@router.post("/api/schedules", status_code=201, summary="Créer une programmation (admin)")
async def create_schedule(body: ScheduleCreate, _: dict = Depends(require_admin)):
    # Vérifier que le catalogue existe
    doc = await repo.find_by_slug(body.slug)
    if not doc:
        raise HTTPException(404, f"Catalogue '{body.slug}' introuvable en DB")
    now = datetime.now(timezone.utc).isoformat()
    sched_doc = {
        **body.model_dump(),
        "created_at": now,
        "updated_at": now,
        "last_run":   None,
    }
    sid = await schedules_repo.create(sched_doc)
    sched_doc["id"] = sid
    if body.active:
        sched_svc.add_job(sched_doc)
    sched_doc["next_run"] = sched_svc.get_next_run(sid)
    return sched_doc


@router.put("/api/schedules/{sid}", summary="Modifier une programmation (admin)")
async def update_schedule(sid: str, body: ScheduleUpdate, _: dict = Depends(require_admin)):
    existing = await schedules_repo.find_by_id(sid)
    if not existing:
        raise HTTPException(404, f"Programmation '{sid}' introuvable")
    fields = body.model_dump(exclude_none=True)
    await schedules_repo.update(sid, fields)
    updated = await schedules_repo.find_by_id(sid)
    # Reconfigurer le job APScheduler
    if updated.get("active", True):
        sched_svc.add_job(updated)
    else:
        sched_svc.remove_job(sid)
    updated["next_run"] = sched_svc.get_next_run(sid)
    return updated


@router.delete("/api/schedules/{sid}", status_code=204, summary="Supprimer une programmation (admin)")
async def delete_schedule(sid: str, _: dict = Depends(require_admin)):
    deleted = await schedules_repo.delete(sid)
    if not deleted:
        raise HTTPException(404, f"Programmation '{sid}' introuvable")
    sched_svc.remove_job(sid)


@router.post("/api/schedules/{sid}/run", summary="Déclencher manuellement une programmation (admin)")
async def run_schedule_now(sid: str, _: dict = Depends(require_admin)):
    """Lance immédiatement la sync programmée, sans attendre l'heure prévue."""
    import asyncio
    from services.sync_manager import sync_manager

    sched = await schedules_repo.find_by_id(sid)
    if not sched:
        raise HTTPException(404, f"Programmation '{sid}' introuvable")
    slug = sched["slug"]
    if sync_manager.is_active(slug):
        raise HTTPException(409, f"'{slug}' est déjà en cours de synchronisation")
    can, reason = sync_manager.can_start(slug)
    if not can:
        raise HTTPException(429, {"error": reason})
    task = asyncio.create_task(
        sync_manager.run_sync(slug, triggered_by=f"schedule:{sid}:manual")
    )
    sync_manager.register(slug, task)
    return {"status": "started", "slug": slug}


# ---------------------------------------------------------------------------
# Historique des synchronisations
# ---------------------------------------------------------------------------

@router.get("/api/history", summary="Historique récent des syncs (admin)")
async def get_history(_: dict = Depends(require_admin)):
    return await history_repo.get_recent(limit=60)


@router.get("/api/history/{slug}", summary="Historique d'un catalogue (admin)")
async def get_history_for_slug(slug: str, _: dict = Depends(require_admin)):
    return await history_repo.get_for_slug(slug, limit=30)
