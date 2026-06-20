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
from api.dependencies import (
    get_current_user, get_optional_user, require_admin,
    check_can_sync, check_can_delete, check_can_refresh, check_catalogue_access,
    check_quota, increment_quota,
    decode_ws_token,
)
from fastapi import Depends

router = APIRouter(prefix="/catalogues", tags=["Catalogues"])


def _apply_content_filter(cat: dict, saisons: list, films: list, scans: list) -> dict:
    """Retire du catalogue les contenus absents des listes (liste vide = tout garder)."""
    cat = dict(cat)
    if saisons:
        allowed = set(saisons)
        cat["saisons"] = [s for s in cat.get("saisons", []) if s.get("slug") in allowed]
    if films:
        allowed = set(films)
        cat["films"] = [f for f in cat.get("films", []) if f.get("slug") in allowed]
    if scans:
        allowed = set(scans)
        cat["scans"] = [s for s in cat.get("scans", []) if s.get("slug") in allowed]
    return cat


def filter_catalogue_for_user(cat: dict, user: Optional[dict]) -> dict:
    """
    Filtre le contenu du catalogue selon le profil de l'utilisateur :
      - Admin          → tout visible
      - Non authentifié → selon visibility.is_public + public_*
      - Utilisateur    → permissions directes + groupes (catalogue / genre)
    """
    from api.dependencies import EffectiveAccess

    slug       = cat.get("slug", "")
    visibility = cat.get("visibility", {})

    if user and user.get("role") == "admin":
        return cat

    if user is None:
        if not visibility.get("is_public", True):
            raise HTTPException(status_code=404, detail="Not found")
        return _apply_content_filter(
            cat,
            visibility.get("public_saisons", []),
            visibility.get("public_films",   []),
            visibility.get("public_scans",   []),
        )

    # Utilisateur authentifié non-admin — utiliser _eff (résolu par get_current_user)
    eff: Optional[EffectiveAccess] = user.get("_eff")

    if eff and isinstance(eff, EffectiveAccess):
        allowed_slugs = eff.allowed_slugs or set()
        genre_access  = eff.genre_access  or set()
        has_restrictions = bool(allowed_slugs or genre_access)
        if has_restrictions:
            cat_genres = {g.lower() for g in cat.get("genres", [])}
            if slug not in allowed_slugs and not (cat_genres & genre_access):
                raise HTTPException(status_code=404, detail="Not found")
        cat_content = (eff.cat_content or {}).get(slug, {})
    else:
        # Fallback sans _eff
        perms        = user.get("permissions", {})
        allowed_cats = perms.get("allowed_catalogues", [])
        if allowed_cats and slug not in allowed_cats:
            raise HTTPException(status_code=404, detail="Not found")
        cat_content = perms.get("catalogue_content", {}).get(slug, {})

    return _apply_content_filter(
        cat,
        cat_content.get("saisons", []),
        cat_content.get("films",   []),
        cat_content.get("scans",   []),
    )


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


@router.get("/site/rechercher", summary="Scrape /catalogue/ avec filtres réels anime-sama.to")
async def rechercher_sur_site_route(
    search:        Optional[str] = Query(None,  description="Texte libre"),
    type:          Optional[str] = Query(None,  description="Anime,Scans,Film,Autres (virgule)"),
    langue:        Optional[str] = Query(None,  description="VOSTFR,VF,VASTFR (virgule)"),
    statut:        Optional[str] = Query(None,  description="En cours,Terminé (virgule)"),
    genre:         Optional[str] = Query(None,  description="Genres séparés par virgule"),
    annee_min:     Optional[int] = Query(None),
    annee_max:     Optional[int] = Query(None),
    episodes_min:  Optional[int] = Query(None),
    episodes_max:  Optional[int] = Query(None),
    chapitres_min: Optional[int] = Query(None),
    chapitres_max: Optional[int] = Query(None),
    page:          int           = Query(1, ge=1),
):
    def _split(s: Optional[str]) -> Optional[list[str]]:
        return [x.strip() for x in s.split(",") if x.strip()] if s else None

    results = await rechercher_sur_site(
        search=search,
        types=_split(type),   langues=_split(langue),
        statuts=_split(statut), genres=_split(genre),
        annee_min=annee_min, annee_max=annee_max,
        episodes_min=episodes_min, episodes_max=episodes_max,
        chapitres_min=chapitres_min, chapitres_max=chapitres_max,
        page=page,
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
async def update_all(background_tasks: BackgroundTasks, user: dict = Depends(get_current_user)):
    check_can_refresh(user)
    background_tasks.add_task(mettre_a_jour_tous)
    return {"message": "Mise à jour lancée en arrière-plan"}


# ------------------------------------------------------------------
# Routes dynamiques {slug}
# ------------------------------------------------------------------

@router.get("/{slug}", summary="Catalogue complet")
async def obtenir_catalogue(
    slug: str,
    user: Optional[dict] = Depends(get_optional_user),
):
    """
    Retourne le catalogue depuis la DB.
    - Authentifié : scrape + sauvegarde si absent en DB.
    - Non authentifié : 404 si absent (pas de scraping).
    """
    catalogue = await repo.find_by_slug(slug)
    if catalogue:
        return filter_catalogue_for_user(catalogue, user)

    if not user:
        raise HTTPException(status_code=404, detail="Not found")

    # Authentifié → scrape + sauvegarde
    catalogue = await get_catalogue(slug)
    if not catalogue:
        raise HTTPException(status_code=404, detail="Not found")

    return filter_catalogue_for_user(catalogue, user)


@router.post("/{slug}/rafraichir", summary="Re-scrape la structure")
async def rafraichir(slug: str, user: dict = Depends(get_current_user)):
    check_can_refresh(user)
    await check_catalogue_access(user, slug)
    catalogue = await rafraichir_catalogue(slug)
    if not catalogue:
        raise HTTPException(status_code=404, detail=f"Impossible de rafraîchir '{slug}'")
    return catalogue


@router.post("/{slug}/sync-content/pause", summary="Met la sync en pause")
async def pause_sync(slug: str, user: dict = Depends(get_current_user)):
    check_can_sync(user)
    if not sync_manager.is_active(slug):
        raise HTTPException(status_code=404, detail=f"Aucune sync active pour '{slug}'")
    await sync_manager.pause(slug)
    return {"status": "pausing", "slug": slug}


@router.post("/{slug}/sync-content/resume", summary="Reprend une sync en pause")
async def resume_sync(slug: str, user: dict = Depends(get_current_user)):
    check_can_sync(user)
    if not sync_manager.is_active(slug):
        raise HTTPException(status_code=404, detail=f"Aucune sync active pour '{slug}'")
    await sync_manager.resume(slug)
    return {"status": "resumed", "slug": slug}


@router.delete("/{slug}/sync-content", summary="Annule la sync en cours")
async def cancel_sync(slug: str, user: dict = Depends(get_current_user)):
    check_can_sync(user)
    if not sync_manager.is_active(slug):
        raise HTTPException(status_code=404, detail=f"Aucune sync active pour '{slug}'")
    await sync_manager.cancel(slug)
    return {"status": "cancelling", "slug": slug}


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
async def start_sync_http(slug: str, user: dict = Depends(get_current_user)):
    """
    Démarre la synchronisation de tout le contenu (saisons, films, scans).

    Règles :
    - Si slug déjà en cours → 409 (Conflict)
    - Si cooldown 7h actif → 429 (Too Many Requests)
    - Si MAX concurrent atteint → 429

    Pour le suivi en temps réel, connectez-vous au WebSocket :
    `WS /catalogues/{slug}/sync-content/ws`
    """
    check_can_sync(user)
    await check_catalogue_access(user, slug)

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
async def ws_sync_episodes(
    websocket: WebSocket,
    slug:      str,
    token:     str = Query(..., description="JWT token d'authentification"),
):
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

    # Authentification WebSocket via query param ?token=
    ws_user = await decode_ws_token(token)
    if not ws_user:
        await websocket.send_json({"type": "error", "reason": "auth_failed", "slug": slug})
        await websocket.close(code=4001)
        return

    try:
        check_can_sync(ws_user)
        await check_catalogue_access(ws_user, slug)
        await check_quota(ws_user)
    except HTTPException as e:
        await websocket.send_json({"type": "error", "reason": e.detail, "slug": slug})
        await websocket.close(code=4003)
        return

    # Abonnement AVANT de vérifier can_start pour ne rater aucun événement
    conn_id, q = sync_manager.subscribe(slug)

    try:
        already_active = sync_manager.is_active(slug)
        can, reason    = sync_manager.can_start(slug)

        if not already_active:
            if not can:
                await websocket.send_json({"type": "error", "reason": reason, "slug": slug})
                return

            # Incrémenter le quota avant de démarrer
            await increment_quota(ws_user)
            triggered_by = ws_user.get("username") or ws_user.get("client_id", "manual")
            task = asyncio.create_task(sync_manager.run_sync(slug, triggered_by=triggered_by))
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
async def supprimer_catalogue(slug: str, user: dict = Depends(get_current_user)):
    check_can_delete(user)
    deleted = await repo.delete_by_slug(slug)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Catalogue '{slug}' introuvable")
    return {"message": f"Catalogue '{slug}' supprimé"}
