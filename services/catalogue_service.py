"""
Couche service : logique métier catalogue.

Flux principal pour GET /{slug} :
  1. Cherche en DB → retourne si présent
  2. Scrape la structure (métadonnées + liste saisons/films/scans)  ~5-10 s
  3. Sauvegarde en DB
  4. Retourne la structure (épisodes vides, episodes_synced=False)

Flux sync-episodes (tâche de fond) :
  Pour chaque saison/film du catalogue :
    → scrape les épisodes via Playwright
    → met à jour la DB au fur et à mesure
  Marque episodes_synced=True à la fin.
"""

from typing import Optional
from models.catalogue import Episode
from services import scraper
import db.repository as repo
from utils.logger import logger
from params import BASE_SAMA_URL


# Ordre de priorité des langues : VF > VOSTFR > VO > autres
_LANG_PRIORITY: dict[str, int] = {"vf": 0, "vostfr": 1, "vo": 2}

def _lang_key(item: dict) -> int:
    """Clé de tri : priorité VF (0) → VOSTFR (1) → VO (2) → autres (99)."""
    return _LANG_PRIORITY.get((item.get("lang") or "").lower(), 99)


def _ensure_absolute_url(url: str, cat_slug: str) -> str:
    """
    Corrige les URLs relatives stockées en DB avant le fix des parsers.
    Ex: "saison1hs/vostfr" → "https://anime-sama.to/catalogue/naruto/saison1hs/vostfr/"
    """
    if not url:
        return url
    if url.startswith("http"):
        return url
    if url.startswith("/"):
        return BASE_SAMA_URL.rstrip("/") + url
    return f"{BASE_SAMA_URL}catalogue/{cat_slug}/{url.strip('/')}/"


# ---------------------------------------------------------------------------
# Recherche
# ---------------------------------------------------------------------------

async def rechercher(
    q:            Optional[str]       = None,
    type_contenu: Optional[str]       = None,
    lang:         Optional[str]       = None,
    etat:         Optional[str]       = None,
    genres:       Optional[list[str]] = None,
    page:         int                 = 1,
) -> list[dict]:
    """
    Cherche en DB avec les filtres fournis.
    Si aucun résultat et q est fourni, scrape la barre de recherche du site.
    """
    db_results = await repo.search_with_filters(
        q=q, type_contenu=type_contenu, lang=lang,
        etat=etat, genres=genres, page=page,
    )
    if db_results:
        return db_results

    # Fallback : recherche sur le site via la barre de recherche
    if q:
        site_results = await scraper.search_anime(q)
        return site_results

    return []


async def rechercher_sur_site(
    search:        Optional[str]       = None,
    types:         Optional[list[str]] = None,
    langues:       Optional[list[str]] = None,
    statuts:       Optional[list[str]] = None,
    genres:        Optional[list[str]] = None,
    annee_min:     Optional[int]       = None,
    annee_max:     Optional[int]       = None,
    episodes_min:  Optional[int]       = None,
    episodes_max:  Optional[int]       = None,
    chapitres_min: Optional[int]       = None,
    chapitres_max: Optional[int]       = None,
    page:          int                 = 1,
) -> list[dict]:
    """Scrape directement /catalogue/ avec les filtres réels du site."""
    return await scraper.search_catalogue_site(
        search=search, types=types, langues=langues, statuts=statuts,
        genres=genres, annee_min=annee_min, annee_max=annee_max,
        episodes_min=episodes_min, episodes_max=episodes_max,
        chapitres_min=chapitres_min, chapitres_max=chapitres_max,
        page_num=page,
    )


# ---------------------------------------------------------------------------
# Récupération d'un catalogue complet
# ---------------------------------------------------------------------------

async def get_catalogue(slug: str) -> Optional[dict]:
    """
    Retourne le catalogue depuis la DB s'il existe.
    Sinon : scrape la structure, sauvegarde, retourne.
    Les épisodes ne sont PAS chargés ici → utiliser sync_episodes_bg.
    """
    doc = await repo.find_by_slug(slug)
    if doc:
        return doc

    catalogue = await scraper.getcatalogue(slug)
    if catalogue is None:
        return None

    await repo.save_catalogue(catalogue)
    return catalogue.model_dump(mode="json")


async def rafraichir_catalogue(slug: str) -> Optional[dict]:
    """Force le re-scraping de la structure (sans épisodes)."""
    catalogue = await scraper.getcatalogue(slug)
    if catalogue is None:
        return None

    # Conserver les épisodes déjà en DB si présents
    existing = await repo.find_by_slug(slug)
    if existing and existing.get("episodes_synced"):
        catalogue.episodes_synced = True
        for i, saison in enumerate(catalogue.saisons):
            ex_saisons = existing.get("saisons", [])
            if i < len(ex_saisons):
                old = ex_saisons[i]
                if old.get("episodes"):
                    saison.episodes       = [Episode(**e) for e in old["episodes"]]
                    saison.total_episodes = old.get("total_episodes", len(saison.episodes))

    await repo.save_catalogue(catalogue)
    return catalogue.model_dump(mode="json")


# ---------------------------------------------------------------------------
# Synchronisation des épisodes (tâche de fond)
# ---------------------------------------------------------------------------

async def sync_content_bg(
    slug:            str,
    broadcast        = None,   # Optional[Callable[[dict], Awaitable[None]]]
    wait_if_paused   = None,   # Optional[async Callable[[], bool]] → False = annulée
) -> int:
    """
    Charge tous les épisodes de toutes les saisons et films d'un catalogue.
    Met à jour la DB au fur et à mesure.
    `broadcast` : callback async optionnel pour streamer la progression (WebSocket).
    Retourne le nombre total d'épisodes chargés.
    """

    async def _emit(event: dict) -> None:
        if broadcast:
            await broadcast(event)

    async def _check() -> bool:
        """Retourne False si la sync doit s'arrêter (annulation)."""
        if wait_if_paused:
            return await wait_if_paused()
        return True

    doc = await repo.find_by_slug(slug)
    if not doc:
        logger.warning(f"sync_episodes_bg : slug {slug!r} absent de la DB")
        return 0

    # Trier par priorité de langue (vf → vostfr → vo) tout en gardant l'index DB
    saisons = sorted(enumerate(doc.get("saisons", [])), key=lambda x: _lang_key(x[1]))
    films   = sorted(enumerate(doc.get("films",   [])), key=lambda x: _lang_key(x[1]))
    scans   = sorted(enumerate(doc.get("scans",   [])), key=lambda x: _lang_key(x[1]))
    total_steps  = len(saisons) + len(films) + len(scans)
    steps_done   = 0
    total_loaded = 0

    await _emit({"type": "progress_init", "slug": slug,
                 "nb_saisons": len(saisons), "nb_films": len(films),
                 "nb_scans": len(scans)})

    # --- Saisons ---
    for i, saison in saisons:
        if not await _check():
            return total_loaded
        nom = saison.get("nom", f"Saison {i}")
        url = _ensure_absolute_url(saison.get("url", ""), slug)

        if saison.get("episodes"):
            logger.info(f"sync [{slug}] saison {i} déjà présente, ignorée")
            await _emit({"type": "saison_skip", "index": i, "nom": nom,
                         "reason": "already_synced"})
            steps_done += 1
            continue

        if not url:
            await _emit({"type": "saison_skip", "index": i, "nom": nom,
                         "reason": "no_url"})
            steps_done += 1
            continue

        await _emit({"type": "saison_start", "index": i, "nom": nom, "url": url})
        logger.info(f"sync [{slug}] chargement saison {i} : {url}")

        raw = await scraper.get_episodes(url)
        if not raw:
            await _emit({"type": "saison_error", "index": i, "nom": nom})
            steps_done += 1
            continue

        episodes = [
            {
                "numero": ep_num,
                "titre":  None,
                "videos": [{"lecteur": v["lecteur"], "player_url": v["player_url"]}
                           for v in lecteurs],
            }
            for ep_num, lecteurs in raw.items()
        ]
        await repo.update_saison_episodes(slug, i, episodes)
        total_loaded += len(episodes)
        steps_done   += 1

        await _emit({
            "type":           "saison_done",
            "index":          i,
            "nom":            nom,
            "episodes_count": len(episodes),
            "progress":       round(steps_done / total_steps * 100) if total_steps else 100,
        })
        logger.info(f"sync [{slug}] saison {i} : {len(episodes)} épisodes sauvegardés")

    # --- Films ---
    for j, film in films:
        if not await _check():
            return total_loaded
        nom = film.get("nom", f"Film {j}")
        url = _ensure_absolute_url(film.get("url", ""), slug)

        if film.get("videos"):
            await _emit({"type": "film_skip", "index": j, "nom": nom,
                         "reason": "already_synced"})
            steps_done += 1
            continue

        if not url:
            await _emit({"type": "film_skip", "index": j, "nom": nom,
                         "reason": "no_url"})
            steps_done += 1
            continue

        await _emit({"type": "film_start", "index": j, "nom": nom, "url": url})
        logger.info(f"sync [{slug}] film {j} : {url}")

        raw = await scraper.get_episodes(url)
        if raw and 1 in raw:
            videos = [{"lecteur": v["lecteur"], "player_url": v["player_url"]}
                      for v in raw[1]]
            await repo.update_film_videos(slug, j, videos)
            total_loaded += 1
            await _emit({
                "type":     "film_done",
                "index":    j,
                "nom":      nom,
                "progress": round(steps_done / total_steps * 100) if total_steps else 100,
            })
        else:
            await _emit({"type": "film_error", "index": j, "nom": nom})

        steps_done += 1

    # --- Scans / Mangas ---
    for k, scan in scans:
        if not await _check():
            return total_loaded
        nom = scan.get("nom", f"Scan {k}")
        url = _ensure_absolute_url(scan.get("url", ""), slug)

        if scan.get("chapitres"):
            await _emit({"type": "scan_skip", "index": k, "nom": nom,
                         "reason": "already_synced"})
            steps_done += 1
            continue

        if not url:
            await _emit({"type": "scan_skip", "index": k, "nom": nom,
                         "reason": "no_url"})
            steps_done += 1
            continue

        await _emit({"type": "scan_start", "index": k, "nom": nom, "url": url})
        logger.info(f"sync [{slug}] scan {k} : {url}")

        chapitres = await scraper.get_scan_chapitres(url)
        if chapitres:
            await repo.update_scan_chapitres(slug, k, chapitres)
            total_loaded += len(chapitres)
            steps_done   += 1
            total_images  = sum(len(c.get("images", [])) for c in chapitres)
            await _emit({
                "type":            "scan_done",
                "index":           k,
                "nom":             nom,
                "chapitres_count": len(chapitres),
                "images_count":    total_images,
                "progress":        round(steps_done / total_steps * 100) if total_steps else 100,
            })
            logger.info(
                f"sync [{slug}] scan {k} : {len(chapitres)} chapitres, "
                f"{total_images} images sauvegardées"
            )
        else:
            await _emit({"type": "scan_error", "index": k, "nom": nom})
            steps_done += 1

    await repo.mark_content_synced(slug)
    logger.info(f"sync [{slug}] terminé : {total_loaded} éléments au total")
    return total_loaded


# ---------------------------------------------------------------------------
# Auto-update (scheduler 24h)
# ---------------------------------------------------------------------------

async def mettre_a_jour_tous() -> int:
    """Re-scrape tous les catalogues EN_COURS (structure seulement)."""
    catalogues = await repo.get_all_en_cours()
    updated = 0
    for cat in catalogues:
        slug = cat.get("slug")
        if not slug:
            continue
        try:
            result = await rafraichir_catalogue(slug)
            if result:
                updated += 1
        except Exception:
            logger.exception(f"Échec mise à jour {slug!r}")
    logger.info(f"Auto-update : {updated}/{len(catalogues)} mis à jour")
    return updated
