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

# Langue originale typique par pays — utilisée uniquement pour filtrer les résultats de
# `/search` (mode "avec titre"), qui ne porte l'origine que pour les séries (`origin_country`),
# pas pour les films (seulement `original_language`). En mode `/discover` (sans titre),
# `with_origin_country` est nativement supporté pour films ET séries, donc cette table n'entre
# pas en jeu — approximation utile seulement pour la recherche texte, pas une vérité absolue.
_COUNTRY_LANGUAGE = {
    "KR": "ko", "JP": "ja", "CN": "zh", "TW": "zh", "HK": "zh", "TH": "th",
    "IN": "hi", "TR": "tr", "FR": "fr", "US": "en", "GB": "en", "ES": "es",
    "DE": "de", "IT": "it", "BR": "pt", "MX": "es", "CA": "en",
}


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


async def tmdb_genres() -> dict[str, list[dict]]:
    """Genres TMDB en français pour movie et tv — alimente le sélecteur de genres de la
    recherche (TMDB ne filtre pas les genres en texte libre, ils sont recensés séparément)."""
    return {
        "movie": await tmdb_client.genres_fr("movie"),
        "tv":    await tmdb_client.genres_fr("tv"),
    }


async def rechercher_tmdb(
    query:          Optional[str]       = None,
    media_type:     Optional[str]       = None,
    genre_ids:      Optional[list[int]] = None,
    annee_min:      Optional[int]       = None,
    annee_max:      Optional[int]       = None,
    origin_country: Optional[str]       = None,
    page:           int                 = 1,
) -> list[dict]:
    """
    Recherche TMDB par titre et/ou filtres (genres, plage d'années, pays d'origine — ex: "KR"
    pour ne voir que les séries/films coréens). `media_type` : "movie" | "tv" | None (les deux).

    - Avec `query` : recherche texte TMDB, puis filtrage local par genre/année/pays (l'API de
      recherche TMDB ne supporte pas ces filtres en même temps qu'un texte libre). Le pays est
      vérifié via `origin_country` pour les séries (présent sur les résultats de recherche),
      et via `original_language` pour les films (TMDB ne renvoie pas `origin_country` sur les
      résultats de recherche film — seulement sur `/discover` — donc on approxime par la
      langue originale typique du pays).
    - Sans `query` : parcours TMDB par filtres (`/discover`), équivalent de la recherche
      anime-sama.to sans titre — `with_origin_country` y est nativement supporté pour les
      films ET les séries, donc le filtre pays est exact dans ce mode.

    Retourne des résultats légers avec `in_db` (comme la recherche combinée anime-sama.to).
    """
    types = [media_type] if media_type in ("movie", "tv") else ["movie", "tv"]
    has_query = bool(query and query.strip())

    raw: list[tuple[dict, str]] = []
    for t in types:
        if has_query:
            for r in await tmdb_client.search(query.strip(), t, page=page):
                raw.append((r, t))
        else:
            for r in await tmdb_client.discover(
                t, genre_ids=genre_ids, annee_min=annee_min, annee_max=annee_max,
                origin_country=origin_country, page=page,
            ):
                raw.append((r, t))

    slugs = [f"{t}-{r['id']}" for r, t in raw if r.get("id")]
    in_db = await repo.find_slugs(slugs)

    results = []
    for r, t in raw:
        tmdb_id = r.get("id")
        if not tmdb_id:
            continue

        annee = _annee_from_date(r.get("release_date") or r.get("first_air_date"))

        # Filtrage local — uniquement nécessaire en mode recherche texte (le mode /discover
        # applique déjà ces filtres côté TMDB).
        if has_query:
            if genre_ids and not (set(r.get("genre_ids", [])) & set(genre_ids)):
                continue
            if annee_min and (annee is None or annee < annee_min):
                continue
            if annee_max and (annee is None or annee > annee_max):
                continue
            if origin_country:
                if t == "tv":
                    if origin_country not in (r.get("origin_country") or []):
                        continue
                else:
                    if r.get("original_language") != _COUNTRY_LANGUAGE.get(origin_country):
                        continue

        slug = f"{t}-{tmdb_id}"
        results.append({
            "tmdb_id":    tmdb_id,
            "media_type": t,
            "slug":       slug,
            "nom":        r.get("title") or r.get("name") or "",
            "image":      tmdb_client.image_url(r.get("poster_path"), "w342"),
            "synopsis":   r.get("overview"),
            "annee":      annee,
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
    if not dispo or not dispo.get("available", False):
        # Vu en conditions réelles : Vidzy référence parfois un tmdb_id dans TMDB search
        # sans avoir le fichier — ajouter quand même produirait un catalogue dont la
        # lecture échoue systématiquement (404 sur le manifest résolu). Autant refuser
        # l'ajout à la source plutôt que de laisser un catalogue "fantôme" injouable.
        logger.warning(f"film_serie_service : '{slug}' indisponible sur Vidzy — ajout refusé")
        return None
    langues = dispo.get("languages") or ["vf"]

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
