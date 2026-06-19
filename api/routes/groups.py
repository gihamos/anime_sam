"""
Routes admin pour la gestion des groupes.

GET    /admin/api/groups                        → liste des groupes
POST   /admin/api/groups                        → créer un groupe (201)
GET    /admin/api/groups/{gid}                  → détail
PUT    /admin/api/groups/{gid}                  → modifier
DELETE /admin/api/groups/{gid}                  → supprimer (204)
GET    /admin/api/groups/{gid}/members          → membres
POST   /admin/api/groups/{gid}/members          → ajouter un membre {username}
DELETE /admin/api/groups/{gid}/members/{u}      → retirer un membre (204)

GET    /admin/api/genres                        → tous les genres depuis DB (ou fallback distinct)
POST   /admin/api/genres/sync                   → synchronise les genres depuis anime-sama.to
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from models.group import GroupCreate, GroupUpdate
import db.groups_repository as groups_repo
import db.genres_repository as genres_repo
import db.user_repository as user_repo
from api.dependencies import require_admin

router = APIRouter(prefix="/admin", tags=["Groupes"])


# ---------------------------------------------------------------------------
# Genres
# ---------------------------------------------------------------------------

@router.get("/api/genres", summary="Genres disponibles (DB + fallback)")
async def list_genres(_: dict = Depends(require_admin)):
    """
    Retourne les genres scrappés depuis anime-sama.to/catalogue/ (stockés en DB).
    Si la DB est vide, renvoie les genres distincts des catalogues déjà en base.
    """
    genres = await genres_repo.get_all()
    if not genres:
        genres = await groups_repo.list_unique_genres()
    return genres


@router.post("/api/genres/sync", summary="Synchronise les genres depuis anime-sama.to")
async def sync_genres(_: dict = Depends(require_admin)):
    """
    Scrape anime-sama.to/catalogue/ pour récupérer tous les genres disponibles
    et les sauvegarde en DB. Lance la tâche en arrière-plan et répond immédiatement.
    """
    import asyncio
    from services.scraper import get_genres_from_site

    async def _do_sync():
        genres = await get_genres_from_site()
        # Sauvegarder uniquement si on a trouvé au moins 5 genres valides
        if len(genres) >= 5:
            await genres_repo.save_all(genres)
        else:
            from utils.logger import logger
            logger.warning(f"Sync genres : seulement {len(genres)} genres trouvés, pas de sauvegarde")

    asyncio.create_task(_do_sync())
    return {"status": "started", "message": "Synchronisation des genres lancée en arrière-plan"}


# ---------------------------------------------------------------------------
# Groupes CRUD
# ---------------------------------------------------------------------------

@router.get("/api/groups", summary="Liste des groupes (admin)")
async def list_groups(_: dict = Depends(require_admin)):
    groups = await groups_repo.list_all()
    for g in groups:
        g["member_count"] = await groups_repo.count_members(g["id"])
    return groups


@router.post("/api/groups", status_code=201, summary="Créer un groupe (admin)")
async def create_group(body: GroupCreate, _: dict = Depends(require_admin)):
    now = datetime.now(timezone.utc).isoformat()
    doc = {**body.model_dump(), "created_at": now, "updated_at": now}
    gid = await groups_repo.create(doc)
    return {**doc, "id": gid, "member_count": 0}


@router.get("/api/groups/{gid}", summary="Détail d'un groupe (admin)")
async def get_group(gid: str, _: dict = Depends(require_admin)):
    g = await groups_repo.find_by_id(gid)
    if not g:
        raise HTTPException(404, f"Groupe '{gid}' introuvable")
    g["member_count"] = await groups_repo.count_members(gid)
    return g


@router.put("/api/groups/{gid}", summary="Modifier un groupe (admin)")
async def update_group(gid: str, body: GroupUpdate, _: dict = Depends(require_admin)):
    if not await groups_repo.find_by_id(gid):
        raise HTTPException(404, f"Groupe '{gid}' introuvable")
    fields = body.model_dump(exclude_none=True)
    if "permissions" in fields and hasattr(fields["permissions"], "model_dump"):
        fields["permissions"] = fields["permissions"].model_dump()
    await groups_repo.update(gid, fields)
    g = await groups_repo.find_by_id(gid)
    g["member_count"] = await groups_repo.count_members(gid)
    return g


@router.delete("/api/groups/{gid}", status_code=204, summary="Supprimer un groupe (admin)")
async def delete_group(gid: str, _: dict = Depends(require_admin)):
    if not await groups_repo.delete(gid):
        raise HTTPException(404, f"Groupe '{gid}' introuvable")


# ---------------------------------------------------------------------------
# Membres
# ---------------------------------------------------------------------------

@router.get("/api/groups/{gid}/members", summary="Membres du groupe (admin)")
async def get_members(gid: str, _: dict = Depends(require_admin)):
    if not await groups_repo.find_by_id(gid):
        raise HTTPException(404, f"Groupe '{gid}' introuvable")
    return await groups_repo.list_members(gid)


@router.post("/api/groups/{gid}/members", summary="Ajouter un membre au groupe (admin)")
async def add_member(gid: str, body: dict, _: dict = Depends(require_admin)):
    username = body.get("username", "").strip()
    if not username:
        raise HTTPException(400, "username requis")
    if not await groups_repo.find_by_id(gid):
        raise HTTPException(404, f"Groupe '{gid}' introuvable")
    user = await user_repo.find_by_username(username)
    if not user:
        raise HTTPException(404, f"Utilisateur '{username}' introuvable")
    grps = list(user.get("groups", []))
    if gid not in grps:
        grps.append(gid)
        await user_repo.update_user(username, {"groups": grps})
    return {"ok": True, "username": username, "group_id": gid}


@router.delete("/api/groups/{gid}/members/{username}", status_code=204,
               summary="Retirer un membre du groupe (admin)")
async def remove_member(gid: str, username: str, _: dict = Depends(require_admin)):
    user = await user_repo.find_by_username(username)
    if not user:
        raise HTTPException(404, f"Utilisateur '{username}' introuvable")
    grps = [g for g in user.get("groups", []) if g != gid]
    await user_repo.update_user(username, {"groups": grps})
