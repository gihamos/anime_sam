"""
Client GraphQL pour l'API publique AniList (https://graphql.anilist.co, aucune clé requise).

Pourquoi un throttling manuel ?
  AniList impose une limite de requêtes/minute (429 Too Many Requests au-delà). On espace
  nous-mêmes les appels (ANILIST_RATE_LIMIT_PER_MIN) plutôt que de compter sur AniList pour
  nous le rappeler à chaque fois, et on retente avec backoff exponentiel sur les 429 restants.

Contrat : ce module ne lève JAMAIS d'exception. Toute erreur (réseau, GraphQL, 429 persistant)
est loguée et donne lieu à un retour vide (None / []) — l'appelant (scheduler ou route admin)
ne doit jamais planter à cause d'AniList.
"""

import asyncio
import time
from typing import Optional

import httpx

from params import ANILIST_API_URL, ANILIST_RATE_LIMIT_PER_MIN
from utils.logger import logger

_MIN_INTERVAL = 60.0 / ANILIST_RATE_LIMIT_PER_MIN
_last_call_ts = 0.0
_throttle_lock = asyncio.Lock()

_MAX_RETRIES = 3

# Un seul jeu de champs partagé pour ANIME et MANGA : AniList renvoie simplement `null`
# pour les champs non pertinents selon le type (ex. `chapters` sur un ANIME).
_MEDIA_FIELDS = """
  id
  title { romaji english native }
  genres
  tags { name rank }
  averageScore
  popularity
  studios(isMain: true) { nodes { name } }
  staff(perPage: 5) { nodes { name { full } } }
  coverImage { extraLarge color }
  bannerImage
  description(asHtml: false)
  seasonYear
  startDate { year }
  episodes
  chapters
  volumes
  format
  status
  streamingEpisodes { title thumbnail }
"""


async def _throttle() -> None:
    global _last_call_ts
    async with _throttle_lock:
        wait = _MIN_INTERVAL - (time.monotonic() - _last_call_ts)
        if wait > 0:
            await asyncio.sleep(wait)
        _last_call_ts = time.monotonic()


async def _post(query: str, variables: dict) -> Optional[dict]:
    """POST GraphQL avec throttling + retry sur 429. Ne lève jamais — None si échec définitif."""
    for attempt in range(_MAX_RETRIES + 1):
        await _throttle()
        try:
            async with httpx.AsyncClient() as c:
                r = await c.post(
                    ANILIST_API_URL,
                    json={"query": query, "variables": variables},
                    timeout=15,
                )
        except Exception as exc:
            logger.warning(f"AniList : erreur réseau — {exc}")
            return None

        if r.status_code == 429:
            if attempt >= _MAX_RETRIES:
                logger.warning("AniList : 429 persistant, abandon")
                return None
            retry_after = r.headers.get("Retry-After")
            delay = float(retry_after) if retry_after else 2 ** attempt
            logger.info(f"AniList : 429, nouvelle tentative dans {delay:.0f}s")
            await asyncio.sleep(delay)
            continue

        if r.status_code != 200:
            logger.warning(f"AniList : HTTP {r.status_code} — {r.text[:200]}")
            return None

        payload = r.json()
        if payload.get("errors"):
            logger.warning(f"AniList : erreur GraphQL — {payload['errors']}")
            return None
        return payload.get("data")

    return None


async def search_by_title(title: str, media_type: str, limit: int = 5) -> list[dict]:
    """
    Recherche par titre. `media_type` : "ANIME" | "MANGA".
    Retourne jusqu'à `limit` candidats (liste vide si échec ou aucun résultat).
    """
    query = f"""
    query ($search: String, $type: MediaType, $perPage: Int) {{
      Page(page: 1, perPage: $perPage) {{
        media(search: $search, type: $type) {{ {_MEDIA_FIELDS} }}
      }}
    }}"""
    data = await _post(query, {"search": title, "type": media_type, "perPage": limit})
    if not data:
        return []
    return data.get("Page", {}).get("media", []) or []


async def get_by_id(anilist_id: int, media_type: str) -> Optional[dict]:
    """
    Récupération directe par ID — pour les rafraîchissements uniquement.
    Une fois un anilist_id confirmé pour une entrée, on ne refait plus jamais de
    recherche texte : on appelle systématiquement cette fonction.
    """
    query = f"""
    query ($id: Int, $type: MediaType) {{
      Media(id: $id, type: $type) {{ {_MEDIA_FIELDS} }}
    }}"""
    data = await _post(query, {"id": anilist_id, "type": media_type})
    if not data:
        return None
    return data.get("Media")
