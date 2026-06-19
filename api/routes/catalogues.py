"""
Routes REST pour les catalogues.

GET   /catalogues/                            → liste résumée (DB)
GET   /catalogues/rechercher                  → recherche DB avec filtres, fallback site
GET   /catalogues/site/rechercher             → scrape /catalogue/ avec filtres URL
GET   /catalogues/sync/status                 → état de toutes les syncs actives
GET   /catalogues/{slug}                      → catalogue complet (DB ou scrape+sauvegarde)
POST  /catalogues/{slug}/rafraichir           → force re-scrape de la structure
POST  /catalogues/{slug}/sync-content        → démarre la sync (HTTP, sans streaming)
GET   /catalogues/{slug}/sync-content/status → état de la sync pour ce slug
WS    /catalogues/{slug}/sync-content/ws     → streaming WebSocket de la progression
GET   /catalogues/{slug}/saisons/{s}/episodes → épisodes on-demand
POST  /catalogues/mettre-a-jour-tous          → update tous les EN_COURS en fond
DELETE /catalogues/{slug}                     → supprime de la DB
"""

import asyncio
from typing import Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, WebSocket, WebSocketDisconnect
from services.catalogue_service import (
    rechercher,
    rechercher_sur_site,
    get_catalogue,
    rafraichir_catalogue,
    sync_content_bg,
    mettre_a_jour_tous,
)
from services.scraper import get_episodes as scraper_get_episodes
from services.sync_manager import sync_manager
import db.repository as repo
from params import BASE_SAMA_URL

router = APIRouter(prefix="/catalogues", tags=["Catalogues"])


# ------------------------------------------------------------------
# Routes fixes (avant les routes dynamiques {slug})
# ------------------------------------------------------------------

@router.get("/", summary="Liste les catalogues en DB")
async def lister_db():
    return await repo.get_all_summary()


@router.get("/rechercher", summary="Recherche avec filtres")
async def rechercher_catalogue(
    q:     Optional[str] = Query(None, description="Titre (recherche partielle)"),
    type:  Optional[str] = Query(None, description="anime | scan | film | autre"),
    lang:  Optional[str] = Query(None, description="vostfr | vf | vo | …"),
    etat:  Optional[str] = Query(None, description="en_cours | termine | abandonne"),
    genre: Optional[str] = Query(None, description="Genres séparés par virgule : action,aventure"),
    page:  int           = Query(1, ge=1),
):
    """
    Cherche en DB avec filtres. Si vide et `q` fourni → scrape la barre de recherche.
    """
    genres_list = [g.strip() for g in genre.split(",")] if genre else None
    results = await rechercher(
        q=q, type_contenu=type, lang=lang, etat=etat, genres=genres_list, page=page
    )
    if not results:
        raise HTTPException(status_code=404, detail="Aucun résultat trouvé")
    return results


@router.get("/site/rechercher", summary="Scrape /catalogue/ avec filtres")
async def rechercher_sur_site_route(
    q:      Optional[str] = Query(None, description="Titre"),
    type:   Optional[str] = Query(None, description="anime | scans | film | autres"),
    lang:   Optional[str] = Query(None, description="vostfr | vf | vastfr"),
    statut: Optional[str] = Query(None, description="en-cours | termine"),
    genre:  Optional[str] = Query(None, description="Genres séparés par virgule"),
    page:   int           = Query(1, ge=1),
):
    genres_list = [g.strip() for g in genre.split(",")] if genre else None
    results = await rechercher_sur_site(
        q=q, type_contenu=type, lang=lang, statut=statut, genres=genres_list, page=page
    )
    if not results:
        raise HTTPException(status_code=404, detail="Aucun résultat sur le site")
    return results


@router.get("/sync/status", summary="État de toutes les syncs actives")
async def sync_global_status():
    return {
        "active_syncs":   sync_manager.active_syncs(),
        "max_concurrent": 3,
        "cooldown_hours": 7,
    }


@router.post("/mettre-a-jour-tous", summary="Update tous les catalogues EN_COURS")
async def update_all(background_tasks: BackgroundTasks):
    background_tasks.add_task(mettre_a_jour_tous)
    return {"message": "Mise à jour lancée en arrière-plan"}


# ------------------------------------------------------------------
# Routes dynamiques {slug}
# ------------------------------------------------------------------

@router.get("/{slug}", summary="Catalogue complet")
async def obtenir_catalogue(slug: str):
    """
    Retourne le catalogue depuis la DB. Scrape + sauvegarde si absent.
    Les épisodes sont vides tant que `sync-content` n'a pas été appelé.
    """
    catalogue = await get_catalogue(slug)
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Catalogue '{slug}' introuvable")
    return catalogue


@router.post("/{slug}/rafraichir", summary="Re-scrape la structure")
async def rafraichir(slug: str):
    catalogue = await rafraichir_catalogue(slug)
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Impossible de rafraîchir '{slug}'")
    return catalogue


@router.get("/{slug}/sync-content/status", summary="État de la sync pour ce slug")
async def sync_status(slug: str):
    """
    Retourne l'état de synchronisation du catalogue :
    - `syncing` : en cours
    - `idle` : terminé, avec cooldown restant
    - `never_synced` : jamais synchronisé
    """
    return sync_manager.status(slug)


@router.post("/{slug}/sync-content", summary="Démarre la sync (HTTP)")
async def start_sync_http(slug: str):
    """
    Démarre la synchronisation de tout le contenu (saisons, films, scans).

    Règles :
    - Si slug déjà en cours → 409 (Conflict)
    - Si cooldown 7h actif → 429 (Too Many Requests)
    - Si MAX concurrent atteint → 429

    Pour le suivi en temps réel, connectez-vous au WebSocket :
    `WS /catalogues/{slug}/sync-content/ws`
    """
    doc = await repo.find_by_slug(slug)
    if not doc:
        raise HTTPException(status_code=404, detail=f"'{slug}' absent de la DB")

    can, reason = sync_manager.can_start(slug)
    if not can:
        if reason == "already_syncing":
            raise HTTPException(
                status_code=409,
                detail={
                    "error":   "already_syncing",
                    "message": f"'{slug}' est déjà en cours de synchronisation",
                    "ws":      f"/catalogues/{slug}/sync-content/ws",
                }
            )
        raise HTTPException(
            status_code=429,
            detail={"error": reason, "ws": f"/catalogues/{slug}/sync-content/ws"}
        )

    task = asyncio.create_task(sync_manager.run_sync(slug))
    sync_manager.register(slug, task)

    return {
        "status":     "started",
        "slug":       slug,
        "nb_saisons": len(doc.get("saisons", [])),
        "nb_films":   len(doc.get("films",   [])),
        "nb_scans":   len(doc.get("scans",   [])),
        "ws":         f"/catalogues/{slug}/sync-content/ws",
    }


@router.websocket("/{slug}/sync-content/ws")
async def ws_sync_episodes(websocket: WebSocket, slug: str):
    """
    WebSocket de suivi de synchronisation.

    Comportement :
    - Si le slug est déjà en cours de sync → se connecte au flux existant
    - Si le slug peut démarrer → démarre la sync et streame la progression
    - Si cooldown ou max concurrent → envoie un événement `error` et ferme

    Événements envoyés :
      {"type": "started",       "slug": "naruto"}
      {"type": "progress_init",  "nb_saisons": 3, "nb_films": 1, "nb_scans": 1}
      {"type": "saison_start",  "index": 0, "nom": "Saison 1 VOSTFR", "url": "…"}
      {"type": "saison_done",   "index": 0, "nom": "…", "episodes_count": 220, "progress": 33}
      {"type": "saison_skip",   "index": 1, "nom": "…", "reason": "already_synced"}
      {"type": "saison_error",  "index": 2, "nom": "…"}
      {"type": "film_start",    "index": 0, "nom": "Film 1 VF", "url": "…"}
      {"type": "film_done",     "index": 0, "nom": "…", "progress": 80}
      {"type": "scan_start",    "index": 0, "nom": "Scan VF", "url": "…"}
      {"type": "scan_done",     "index": 0, "nom": "…", "chapitres_count": 700, "progress": 90}
      {"type": "scan_skip",     "index": 0, "nom": "…", "reason": "already_synced"}
      {"type": "completed",     "slug": "naruto", "total_episodes": 720}
      {"type": "error",         "slug": "naruto", "message": "…"}
      {"type": "ping"}          (keep-alive toutes les 30s)
    """
    await websocket.accept()

    # Abonnement AVANT de vérifier can_start pour ne rater aucun événement
    conn_id, q = sync_manager.subscribe(slug)

    try:
        already_active = sync_manager.is_active(slug)
        can, reason    = sync_manager.can_start(slug)

        if not already_active:
            if not can:
                await websocket.send_json({"type": "error", "reason": reason, "slug": slug})
                return

            # Démarrer la sync
            task = asyncio.create_task(sync_manager.run_sync(slug))
            sync_manager.register(slug, task)
        else:
            # Sync déjà en cours : on informe juste qu'on s'y abonne
            await websocket.send_json({
                "type":    "info",
                "message": f"Sync de '{slug}' déjà en cours, abonnement au flux existant",
            })

        # Streamer les événements jusqu'à la fin
        while True:
            try:
                event = await asyncio.wait_for(q.get(), timeout=30.0)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
                continue

            if event is None:       # sentinel → sync terminée
                break

            await websocket.send_json(event)

            if event.get("type") in ("completed", "error"):
                break

    except (WebSocketDisconnect, Exception):
        pass
    finally:
        sync_manager.unsubscribe(slug, conn_id)
        try:
            await websocket.close()
        except Exception:
            pass


@router.get(
    "/{slug}/saisons/{saison}/episodes",
    summary="Épisodes d'une saison (on-demand)"
)
async def obtenir_episodes(
    slug:   str,
    saison: str,
    lang:   str = Query("vostfr", description="Code langue : vostfr | vf | vo | …"),
):
    """Extrait les épisodes directement depuis le site (Playwright). Ne modifie pas la DB."""
    url  = f"{BASE_SAMA_URL}catalogue/{slug}/{saison}/{lang}/"
    data = await scraper_get_episodes(url)
    if not data:
        raise HTTPException(
            status_code=404,
            detail=f"Aucun épisode pour {slug}/{saison}/{lang}"
        )
    return data


@router.delete("/{slug}", summary="Supprime un catalogue de la DB")
async def supprimer_catalogue(slug: str):
    deleted = await repo.delete_by_slug(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Catalogue '{slug}' introuvable")
    return {"message": f"Catalogue '{slug}' supprimé"}
