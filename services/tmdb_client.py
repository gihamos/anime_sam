"""
Client pour l'API publique TMDB (https://api.themoviedb.org/3, clé API v3 requise).

Sert de source de structure + métadonnées pour les films et séries (2e source de contenu,
indépendante du scraping anime-sama.to) : recherche, détails, saisons/épisodes, genres déjà
localisables en français via `language=fr-FR` — pas besoin d'une table de traduction statique
comme pour les genres AniList.

Contrat identique aux autres clients externes du projet (anilist_client.py, deepl_client.py) :
ce module ne lève JAMAIS d'exception. Toute erreur (réseau, HTTP, clé absente) est loguée et
donne lieu à un retour vide (None / []).
"""

from __future__ import annotations

from typing import Optional

import httpx

from params import TMDB_API_URL, TMDB_API_KEY, TMDB_IMAGE_BASE
from utils.logger import logger

# Cache mémoire simple : la liste des genres TMDB est quasi statique, pas besoin de la
# re-télécharger à chaque appel. Clé = media_type ("movie" | "tv"), valeur = {id: name}.
_genre_cache_en: dict[str, dict[int, str]] = {}


def image_url(path: Optional[str], size: str = "original") -> Optional[str]:
    """Construit une URL d'image TMDB absolue à partir d'un chemin relatif (ex: poster_path)."""
    if not path:
        return None
    return f"{TMDB_IMAGE_BASE}/{size}{path}"


async def _get(path: str, params: dict) -> Optional[dict]:
    if not TMDB_API_KEY:
        logger.warning("TMDB : TMDB_API_KEY non configurée")
        return None
    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{TMDB_API_URL}{path}",
                params={**params, "api_key": TMDB_API_KEY},
                timeout=15,
            )
    except Exception as exc:
        logger.warning(f"TMDB : erreur réseau — {exc}")
        return None

    if r.status_code != 200:
        logger.warning(f"TMDB : HTTP {r.status_code} sur {path} — {r.text[:200]}")
        return None

    return r.json()


async def _genre_names_en(media_type: str) -> dict[int, str]:
    """Table id → nom anglais des genres — mise en cache mémoire (quasi-statique côté TMDB)."""
    if media_type in _genre_cache_en:
        return _genre_cache_en[media_type]

    data = await _get(f"/genre/{media_type}/list", {"language": "en-US"})
    table = {g["id"]: g["name"] for g in (data or {}).get("genres", [])}
    _genre_cache_en[media_type] = table
    return table


async def search(query: str, media_type: str, page: int = 1) -> list[dict]:
    """
    Recherche par titre. `media_type` : "movie" | "tv".
    Retourne les résultats bruts TMDB (liste vide si échec ou aucun résultat).
    """
    data = await _get(f"/search/{media_type}", {"query": query, "language": "fr-FR", "page": page})
    return (data or {}).get("results", []) or []


async def get_details(tmdb_id: int, media_type: str) -> Optional[dict]:
    """
    Détails complets d'un film/d'une série, avec mots-clés et équipe technique/casting.
    Ajoute aussi `_genres_en` (noms anglais) au dict retourné, pour le vecteur de similarité
    du moteur de recommandation (vocabulaire cohérent avec les genres AniList).
    """
    data = await _get(
        f"/{media_type}/{tmdb_id}",
        {"language": "fr-FR", "append_to_response": "keywords,credits"},
    )
    if not data:
        return None

    genre_table_en = await _genre_names_en(media_type)
    genre_ids = [g["id"] for g in data.get("genres", [])]
    data["_genres_en"] = [genre_table_en[i] for i in genre_ids if i in genre_table_en]
    return data


async def get_season(tmdb_id: int, season_number: int) -> Optional[dict]:
    """Détails d'une saison (épisodes avec titre/synopsis/vignette) — séries uniquement."""
    return await _get(f"/tv/{tmdb_id}/season/{season_number}", {"language": "fr-FR"})
