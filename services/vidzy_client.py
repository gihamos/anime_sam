"""
Client pour Vidzy (https://api.vidzy.org/) — service d'embed vidéo public, sans clé,
qui donne un lecteur à partir d'un identifiant TMDB : "donne un TMDB id, obtiens un lecteur".
2e brique de la source de contenu "tmdb-vidzy" (TMDB = structure/métadonnées, Vidzy = lecteur).

Pourquoi ce module et pas simplement yt-dlp comme pour anime-sama.to ?
  yt-dlp n'a pas d'extracteur pour vidzy.org/vidzy.cc (vérifié : "Unsupported URL"). La page
  d'embed (`vidzy.org/movie|serie/...`) contient un unique <iframe> vers
  `vidzy.cc/embed-xxxx.html`, qui charge en JS un manifest HLS signé et à durée de vie limitée
  (~48h) via des requêtes réseau — invisible dans le HTML statique. On reproduit donc ici, avec
  Playwright, exactement la résolution qu'un navigateur ferait, puis on capte l'URL du manifest
  interceptée au vol. Une fois cette URL obtenue, yt-dlp la lit nativement (HLS standard) —
  voir le branchement dans services/downloader.py, qui réutilise tout le reste du pipeline
  existant (téléchargement, proxy de streaming) sans modification.

Contrat identique aux autres clients externes du projet : ne lève jamais d'exception.
"""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Optional
from urllib.parse import urlparse

import httpx

from params import VIDZY_BASE_URL
from utils.logger import logger

# Pool dédié pour Playwright, séparé de celui de scraper.py (sources indépendantes,
# on ne veut pas qu'une résolution Vidzy lente bloque un scraping anime-sama.to ou l'inverse).
_executor = ThreadPoolExecutor(max_workers=2)

# Navigateur Chromium persistant, un par thread du pool (sync_playwright — voir
# services/scraper.py pour la justification Windows — est lié au thread qui l'a démarré,
# donc pas de partage entre threads possible). Avant, un navigateur complet était relancé à
# CHAQUE résolution (~0.5-1.5 s de démarrage Chromium en plus des 3-10 s de résolution) —
# constaté en conditions réelles comme une part significative de la lenteur perçue, en plus
# de la charge CPU/mémoire inutile qui pouvait faire échouer une résolution concurrente sous
# charge. Avec 2 threads dans l'executor, au plus 2 navigateurs vivent en permanence après
# préchauffe — même budget mémoire que prévu par le commentaire ci-dessus (~300 Mo/instance).
_thread_local = threading.local()


def _get_browser():
    """Retourne le navigateur du thread courant, le (re)lançant si besoin (première
    utilisation de ce thread, ou navigateur mort — crash/OOM)."""
    browser = getattr(_thread_local, "browser", None)
    if browser is not None:
        try:
            if browser.is_connected():
                return browser
        except Exception:
            pass
        _reset_browser()

    from playwright.sync_api import sync_playwright

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    _thread_local.pw = pw
    _thread_local.browser = browser
    return browser


def _reset_browser() -> None:
    """Ferme proprement le navigateur/playwright du thread courant (s'ils existent) et
    efface l'état — le prochain appel à _get_browser() en relance des neufs."""
    pw = getattr(_thread_local, "pw", None)
    browser = getattr(_thread_local, "browser", None)
    _thread_local.browser = None
    _thread_local.pw = None
    try:
        if browser is not None:
            browser.close()
    except Exception:
        pass
    try:
        if pw is not None:
            pw.stop()
    except Exception:
        pass

# La résolution Playwright prend 3-10 s (navigateur headless réel) — recommencer cette
# résolution à *chaque* clic sur lecture (y compris resélectionner la même vidéo quelques
# secondes après) ajoute une latence perçue par le lecteur qui peut dépasser son propre délai
# d'attente et déclencher une "erreur de lecture" côté client, alors que le serveur aurait
# fini par répondre correctement. Le manifest signé reste valide ~48h côté Vidzy (e=172800
# dans l'URL) — on peut donc réutiliser une résolution récente sans risque de rejouer un lien
# expiré. Cache mémoire simple : clé = URL embed, valeur = (expiration, résultat).
_resolve_cache: dict[str, tuple[float, Optional[dict]]] = {}
_CACHE_TTL_OK     = 1800  # 30 min — largement sous les 48h de validité du lien signé
_CACHE_TTL_FAILED = 120   # 2 min — évite de marteler Playwright sur un titre cassé,
                          # mais retente vite au cas où l'échec précédent était transitoire

# Referer/Origin exigés par le CDN vidzy.cc pour servir les segments/manifests HLS —
# constants car toujours les mêmes quel que soit le titre (vérifié en conditions réelles).
_VIDZY_HEADERS = {"Referer": "https://vidzy.cc/", "Origin": "https://vidzy.cc"}


def is_vidzy_url(url: str) -> bool:
    """True si `url` doit être résolue via ce module plutôt que directement par yt-dlp."""
    try:
        return urlparse(url).netloc.endswith("vidzy.org")
    except Exception:
        return False


def embed_url_film(tmdb_id: int) -> str:
    return f"{VIDZY_BASE_URL}/movie/{tmdb_id}"


def embed_url_episode(tmdb_id: int, saison: int, episode: int) -> str:
    return f"{VIDZY_BASE_URL}/serie/{tmdb_id}/{saison}/{episode}"


async def check_availability(tmdb_id: int) -> Optional[dict]:
    """
    GET /api/{tmdb_id} — confirme qu'un titre est bien disponible sur Vidzy avant de l'ajouter
    au catalogue, et donne les langues disponibles (vu en conditions réelles : ex. ["vf"]).
    """
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(f"{VIDZY_BASE_URL}/api/{tmdb_id}", timeout=15)
    except Exception as exc:
        logger.warning(f"Vidzy : erreur réseau sur la vérification de dispo — {exc}")
        return None
    if r.status_code != 200:
        return None
    try:
        return r.json()
    except Exception:
        return None


def _resolve_embed_sync(url: str) -> Optional[dict]:
    """
    Ouvre `url` (page vidzy.org) en Playwright headless, suit l'iframe vidzy.cc, et intercepte
    les requêtes réseau jusqu'à trouver le manifest HLS signé. Retourne le même format de dict
    que downloader._resolve_sync (url/audio_url/ext/protocol/headers/title/duration/merged) —
    pour rester un drop-in dans le pipeline de résolution existant.
    """
    try:
        browser = _get_browser()
    except Exception as exc:
        logger.warning(f"Vidzy : impossible de démarrer Chromium — {exc}")
        return None

    try:
        page = browser.new_page()
    except Exception as exc:
        # Le navigateur du thread est dans un état invalide (ex. crashé entre deux appels) —
        # on le jette pour qu'il soit relancé au prochain appel, plutôt que de rester bloqué
        # à échouer indéfiniment sur ce même navigateur mort.
        logger.warning(f"Vidzy : navigateur indisponible, relance au prochain appel — {exc}")
        _reset_browser()
        return None

    requests_seen: list[str] = []
    try:
        page.on("request", lambda req: requests_seen.append(req.url))
        try:
            page.goto(url, timeout=20000, wait_until="networkidle")
        except Exception:
            # Un flux qui continue de streamer peut empêcher "networkidle" d'être atteint —
            # sans gravité, le manifest a très probablement déjà été demandé à ce stade.
            pass
        title = page.title()
    except Exception as exc:
        logger.warning(f"Vidzy : échec résolution Playwright pour {url!r} — {exc}")
        return None
    finally:
        try:
            page.close()
        except Exception:
            pass

    master = next((u for u in requests_seen if "master.m3u8" in u), None) \
        or next((u for u in requests_seen if ".m3u8" in u), None)

    if not master:
        logger.warning(f"Vidzy : aucun manifest HLS intercepté pour {url!r}")
        return None

    return {
        "url":       master,
        "audio_url": None,
        "ext":       "m3u8",
        "protocol":  "m3u8",
        "headers":   dict(_VIDZY_HEADERS),
        "title":     title or None,
        "duration":  None,
        "merged":    False,
    }


async def resolve_embed(url: str) -> Optional[dict]:
    """
    Wrapper async (thread pool dédié) de _resolve_embed_sync, avec cache mémoire de courte
    durée pour éviter de repayer la latence Playwright (3-10 s) à chaque tentative de lecture
    du même titre — voir le commentaire sur `_resolve_cache` plus haut.
    """
    cached = _resolve_cache.get(url)
    if cached and cached[0] > time.monotonic():
        return cached[1]

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(_executor, _resolve_embed_sync, url)

    ttl = _CACHE_TTL_OK if result else _CACHE_TTL_FAILED
    _resolve_cache[url] = (time.monotonic() + ttl, result)
    return result
