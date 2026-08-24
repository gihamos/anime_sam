"""
Orchestration de la source de contenu "tmdb-vidzy" (films & séries — 2e source du projet,
indépendante du scraping anime-sama.to). TMDB fournit la structure et les métadonnées
(recherche, détails, saisons/épisodes) ; Vidzy fournit le lecteur (voir services/tmdb_client.py
et services/vidzy_client.py pour le détail de chaque brique).

Contrairement à anime-sama.to, TMDB donne saisons/épisodes/titres en un ou deux appels JSON —
pas de scraping, donc pas de phase 2 "sync-content" séparée : un catalogue créé ici a
`episodes_synced=True` dès sa création.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

import db.repository as repo
import services.tmdb_client as tmdb_client
import services.vidzy_client as vidzy_client
from models.catalogue import Catalogue, Saison, Film, Episode, Video, Etat, TypeContenu
from utils.logger import logger

_STATUTS_EN_COURS = {"Returning Series", "In Production", "Planned"}


def _annee_from_date(date_str: Optional[str]) -> Optional[int]:
    if not date_str or len(date_str) < 4:
        return None
    try:
        return int(date_str[:4])
    except ValueError:
        return None


def _build_enrichment(details: dict, media_type: str) -> dict:
    """Construit le sous-document `enrichment` depuis une réponse TMDB — même forme que
    l'enrichissement AniList (score /100, genres_fr, cover/banner…), pour que l'app mobile et
    le moteur de recommandation fonctionnent sans aucune modification sur cette 2e source."""
    vote = details.get("vote_average")
    if media_type == "movie":
        studios = [c["name"] for c in (details.get("production_companies") or [])]
        annee = _annee_from_date(details.get("release_date"))
    else:
        studios = [c.get("name") for c in (details.get("created_by") or []) if c.get("name")]
        annee = _annee_from_date(details.get("first_air_date"))

    return {
        "tmdb_id":           details.get("id"),
        "media_type":        media_type,
        "genres":            details.get("_genres_en") or [],
        "genres_fr":         [g["name"] for g in (details.get("genres") or [])],
        "tags":              [],
        "score":             round(vote * 10, 1) if vote is not None else None,
        "popularity":        details.get("popularity"),
        "studios_ou_staff":  studios,
        "cover_url":         tmdb_client.image_url(details.get("poster_path"), "w500"),
        "banner_url":        tmdb_client.image_url(details.get("backdrop_path"), "original"),
        "dominant_color":    None,
        "synopsis":          details.get("overview"),
        "synopsis_fr":       details.get("overview"),  # déjà en FR (language=fr-FR)
        "annee":             annee,
        "format":            "MOVIE" if media_type == "movie" else "TV",
        "match_confidence":  1.0,  # ID TMDB exact, pas de matching flou nécessaire
        "needs_review":      False,
        "enriched_at":       datetime.now(timezone.utc).isoformat(),
    }


async def rechercher_tmdb(query: str, media_type: Optional[str] = None) -> list[dict]:
    """
    Recherche TMDB par titre. `media_type` : "movie" | "tv" | None (recherche les deux).
    Retourne des résultats légers avec `in_db` (comme la recherche combinée anime-sama.to).
    """
    types = [media_type] if media_type in ("movie", "tv") else ["movie", "tv"]

    raw: list[tuple[dict, str]] = []
    for t in types:
        for r in await tmdb_client.search(query, t):
            raw.append((r, t))

    slugs = [f"{t}-{r['id']}" for r, t in raw if r.get("id")]
    in_db = await repo.find_slugs(slugs)

    results = []
    for r, t in raw:
        tmdb_id = r.get("id")
        if not tmdb_id:
            continue
        slug = f"{t}-{tmdb_id}"
        results.append({
            "tmdb_id":    tmdb_id,
            "media_type": t,
            "slug":       slug,
            "nom":        r.get("title") or r.get("name") or "",
            "image":      tmdb_client.image_url(r.get("poster_path"), "w342"),
            "synopsis":   r.get("overview"),
            "annee":      _annee_from_date(r.get("release_date") or r.get("first_air_date")),
            "note":       round(r["vote_average"], 1) if r.get("vote_average") else None,
            "in_db":      slug in in_db,
        })
    return results


async def ajouter_depuis_tmdb(media_type: str, tmdb_id: int) -> Optional[dict]:
    """
    Ajoute un film/série au catalogue depuis TMDB (structure + métadonnées) avec un lecteur
    Vidzy. Idempotent : si déjà en base (slug déterministe), retourne l'existant tel quel.
    """
    if media_type not in ("movie", "tv"):
        raise ValueError("media_type doit être 'movie' ou 'tv'")

    slug = f"{media_type}-{tmdb_id}"
    existing = await repo.find_by_slug(slug)
    if existing:
        return existing

    details = await tmdb_client.get_details(tmdb_id, media_type)
    if not details:
        return None

    enrichment = _build_enrichment(details, media_type)
    nom = details.get("title") or details.get("name") or f"{media_type}-{tmdb_id}"
    titre_original = details.get("original_title") or details.get("original_name")
    tmdb_url = f"https://www.themoviedb.org/{media_type}/{tmdb_id}"

    dispo = await vidzy_client.check_availability(tmdb_id)
    langues = (dispo or {}).get("languages") or ["vf"]

    catalogue = Catalogue(
        slug=slug,
        url=tmdb_url,
        source="tmdb-vidzy",
        nom=nom,
        titre_alternatif=titre_original if titre_original != nom else None,
        synopsis=details.get("overview"),
        image=enrichment["cover_url"],
        genres=enrichment["genres_fr"],
        langues=langues,
        episodes_synced=True,
    )

    if media_type == "movie":
        catalogue.type_contenu = TypeContenu.FILM
        catalogue.etat = Etat.TERMINE
        catalogue.films = [Film(
            nom=nom,
            slug="film1",
            lang=langues[0] if langues else "vf",
            url=tmdb_url,
            image=enrichment["cover_url"],
            videos=[Video(lecteur="Vidzy", player_url=vidzy_client.embed_url_film(tmdb_id))],
        )]
    else:
        catalogue.type_contenu = TypeContenu.SERIE
        catalogue.etat = Etat.EN_COURS if details.get("status") in _STATUTS_EN_COURS else Etat.TERMINE
        saisons: list[Saison] = []
        for s in details.get("seasons", []):
            numero = s.get("season_number")
            if numero is None:
                continue
            season_detail = await tmdb_client.get_season(tmdb_id, numero)
            if not season_detail:
                continue
            episodes = [
                Episode(
                    numero=ep["episode_number"],
                    titre=ep.get("name"),
                    videos=[Video(
                        lecteur="Vidzy",
                        player_url=vidzy_client.embed_url_episode(tmdb_id, numero, ep["episode_number"]),
                    )],
                    enrichment={
                        "title":     ep.get("name"),
                        "thumbnail": tmdb_client.image_url(ep.get("still_path")),
                    },
                )
                for ep in season_detail.get("episodes", [])
                if ep.get("episode_number") is not None
            ]
            if not episodes:
                continue
            saisons.append(Saison(
                nom=season_detail.get("name") or f"Saison {numero}",
                slug=f"saison{numero}",
                lang=langues[0] if langues else "vf",
                url=f"{tmdb_url}/season/{numero}",
                image=tmdb_client.image_url(season_detail.get("poster_path"), "w342"),
                total_episodes=len(episodes),
                episodes=episodes,
            ))
        catalogue.saisons = saisons

    await repo.save_catalogue(catalogue)
    await repo.set_enrichment(slug, enrichment)
    logger.info(f"film_serie_service : '{slug}' ajouté depuis TMDB ({nom})")

    return await repo.find_by_slug(slug)
