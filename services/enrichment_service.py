"""
Pipeline d'enrichissement des métadonnées via AniList.

Flux pour un catalogue ANIME/MANGA (enrichissement au niveau catalogue) :
  1. Si un anilist_id est déjà confirmé (enrichment.anilist_id) → refetch direct par ID
     (services.anilist_client.get_by_id). Jamais de nouvelle recherche texte dans ce cas.
  2. Sinon → recherche par titre (search_by_title), puis appariement par similarité
     (rapidfuzz) sur (nom, titre_alternatif) contre (romaji, english) de chaque candidat.
     Le meilleur candidat est retenu même à faible confiance (< 0.7), mais marqué
     needs_review=True plutôt que rejeté — un admin doit avoir quelque chose à corriger.
  3. Traduction FR du synopsis : le synopsis anime-sama.to (déjà en français) est
     prioritaire ; DeepL n'est appelé qu'en son absence, pour traduire la description
     AniList (anglaise). L'anglais brut est toujours conservé en repli.
  4. Écriture partielle en DB (db.repository.set_enrichment) — ne touche jamais aux
     champs de scraping existants.

Films : un catalogue peut contenir PLUSIEURS films (franchise) — chacun est recherché
et apparié individuellement à AniList (pas le catalogue dans son ensemble), et son
enrichissement est stocké sur le film lui-même (Film.enrichment).

Épisodes : dérivé du champ AniList `streamingEpisodes` (titre + vignette), disponible
seulement pour les séries ayant un partenariat streaming listé sur AniList — c'est le
seul champ AniList pertinent au niveau épisode. Appliqué par POSITION (streamingEpisodes[i]
↔ épisode numéro i+1) sur chaque saison du catalogue une fois l'anilist_id du catalogue
résolu : dans ce projet, les différentes `saisons` d'un catalogue sont des variantes de
langue (VOSTFR/VF) du même contenu, pas des arcs différents, donc un seul appariement
AniList au niveau catalogue suffit à couvrir toutes les saisons. Best-effort : l'ordre de
streamingEpisodes n'est pas garanti coïncider exactement avec la numérotation locale.

Limite connue : un re-scrape complet (bouton "Rafraîchir") reconstruit les objets
Saison/Episode/Film depuis zéro et réinitialise leur `enrichment` imbriqué (contrairement
au `enrichment` de niveau catalogue, qui lui est protégé — voir save_catalogue). Le job
planifié ré-enrichit automatiquement ce qui redevient "manquant" au run suivant.

Le job planifié (enrichir_tous) et les routes admin appellent ce module ; aucun des deux
ne doit jamais planter à cause d'une source externe indisponible (AniList/DeepL).
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from bs4 import BeautifulSoup
from rapidfuzz import fuzz

import db.repository as repo
from constants.genres_fr import to_fr
from services.anilist_client import search_by_title, get_by_id
from services.deepl_client import translate_to_fr
from utils.logger import logger

# Mapping type_contenu (ce projet) -> MediaType (AniList). AUTRE volontairement absent
# (pas d'équivalent AniList sensé). "film" est traité à part (enrichissement par film
# individuel, cf. enrichir_films) mais mappé ici sur ANIME pour le matching : AniList
# classe les films d'animation sous MediaType.ANIME avec format=MOVIE.
TYPE_MAP = {"anime": "ANIME", "film": "ANIME", "scan": "MANGA"}

_CONFIDENCE_THRESHOLD = 0.7
_FRESHNESS_DAYS = 30


def _is_stale(enrichment: Optional[dict]) -> bool:
    if not enrichment or not enrichment.get("enriched_at"):
        return True
    try:
        enriched_at = datetime.fromisoformat(enrichment["enriched_at"])
    except ValueError:
        return True
    return datetime.now(timezone.utc) - enriched_at > timedelta(days=_FRESHNESS_DAYS)


def _strip_html(text: str) -> str:
    """AniList peut renvoyer des balises même avec asHtml:false selon les entrées."""
    return BeautifulSoup(text, "html.parser").get_text(" ", strip=True)


def _best_match(nom: str, titre_alt: Optional[str], candidates: list[dict]) -> tuple[Optional[dict], float]:
    """Score chaque candidat par similarité max sur (nom, titre_alt) x (romaji, english)."""
    queries = [t for t in (nom, titre_alt) if t]
    best, best_score = None, 0.0
    for cand in candidates:
        title = cand.get("title") or {}
        titles = [t for t in (title.get("romaji"), title.get("english")) if t]
        if not queries or not titles:
            continue
        score = max(fuzz.WRatio(q, t) for q in queries for t in titles) / 100.0
        if score > best_score:
            best, best_score = cand, score
    return best, best_score


async def build_enrichment(
    media: dict,
    media_type: str,
    confidence: float,
    needs_review: bool,
    existing_synopsis_fr: Optional[str],
) -> dict:
    """Construit le sous-document `enrichment` à partir d'une réponse AniList `Media`."""
    genres = media.get("genres") or []
    raw_description = media.get("description") or ""
    description = _strip_html(raw_description) or None

    # Le synopsis anime-sama.to (déjà FR) prime toujours sur la traduction DeepL.
    synopsis_fr = existing_synopsis_fr or None
    if not synopsis_fr and description:
        synopsis_fr = await translate_to_fr(description)

    if media_type == "ANIME":
        studios_ou_staff = [n["name"] for n in (media.get("studios") or {}).get("nodes", [])]
        annee = media.get("seasonYear")
    else:
        studios_ou_staff = [
            (n.get("name") or {}).get("full") for n in (media.get("staff") or {}).get("nodes", [])
        ]
        studios_ou_staff = [s for s in studios_ou_staff if s]
        annee = (media.get("startDate") or {}).get("year")

    cover = media.get("coverImage") or {}

    return {
        "anilist_id":       media.get("id"),
        "type":             media_type,
        "genres":           genres,
        "genres_fr":        to_fr(genres),
        "tags":             media.get("tags") or [],
        "score":            media.get("averageScore"),
        "popularity":       media.get("popularity"),
        "studios_ou_staff": studios_ou_staff,
        "cover_url":        cover.get("extraLarge"),
        "banner_url":       media.get("bannerImage"),
        "dominant_color":   cover.get("color"),
        "synopsis":         description,
        "synopsis_fr":      synopsis_fr,
        "annee":            annee,
        "format":           media.get("format"),
        "match_confidence": round(confidence, 4),
        "needs_review":     needs_review,
        "enriched_at":      datetime.now(timezone.utc).isoformat(),
    }


async def _distribute_episode_enrichment(slug: str, streaming_episodes: list[dict]) -> None:
    """
    Applique streamingEpisodes[i] à l'épisode numéro i+1 de CHAQUE saison du catalogue
    (les saisons d'un même catalogue sont des variantes de langue du même contenu dans
    ce projet, donc un seul jeu de streamingEpisodes s'applique à toutes). Best-effort,
    silencieux en cas d'échec — ne doit jamais faire échouer l'enrichissement catalogue.
    """
    if not streaming_episodes:
        return
    try:
        cat_full = await repo.find_by_slug(slug)
        if not cat_full:
            return
        now = datetime.now(timezone.utc).isoformat()
        for saison in cat_full.get("saisons", []):
            for ep in saison.get("episodes", []):
                idx = ep.get("numero", 0) - 1
                if idx < 0 or idx >= len(streaming_episodes):
                    continue
                se = streaming_episodes[idx]
                await repo.set_episode_enrichment(slug, saison["slug"], ep["numero"], {
                    "title":       se.get("title"),
                    "thumbnail":   se.get("thumbnail"),
                    "enriched_at": now,
                })
    except Exception:
        logger.exception(f"Enrichissement : échec distribution épisodes pour '{slug}'")


async def _enrich_one(cat: dict) -> tuple[bool, Optional[str]]:
    """Traite un catalogue (niveau catalogue — anime/manga). Retourne (succès, raison)."""
    slug         = cat["slug"]
    type_contenu = cat.get("type_contenu")
    media_type   = TYPE_MAP.get(type_contenu)
    if not media_type:
        return False, f"type_contenu non enrichissable : {type_contenu}"

    existing_id = (cat.get("enrichment") or {}).get("anilist_id")

    if existing_id:
        media = await get_by_id(existing_id, media_type)
        if not media:
            return False, "Rafraîchissement AniList impossible (ID introuvable ou API indisponible)"
        confidence, needs_review = 1.0, False
    else:
        candidates = await search_by_title(cat.get("nom", ""), media_type)
        if not candidates:
            return False, "Aucun résultat AniList"
        media, confidence = _best_match(cat.get("nom", ""), cat.get("titre_alternatif"), candidates)
        if not media:
            return False, "Aucun candidat exploitable"
        needs_review = confidence < _CONFIDENCE_THRESHOLD

    enrichment = await build_enrichment(
        media, media_type, confidence, needs_review, cat.get("synopsis")
    )
    ok = await repo.set_enrichment(slug, enrichment)
    if not ok:
        return False, "Catalogue introuvable en DB au moment de l'écriture"

    if needs_review:
        logger.info(f"Enrichissement : '{slug}' à faible confiance ({confidence:.2f}) — needs_review")

    if type_contenu == "anime":
        await _distribute_episode_enrichment(slug, media.get("streamingEpisodes") or [])

    return True, None


async def _enrich_film_one(slug: str, film: dict) -> tuple[bool, Optional[str]]:
    """Traite UN film au sein d'un catalogue. Retourne (succès, raison_échec_si_échec)."""
    film_slug = film["slug"]
    existing_id = (film.get("enrichment") or {}).get("anilist_id")

    if existing_id:
        media = await get_by_id(existing_id, "ANIME")
        if not media:
            return False, "Rafraîchissement AniList impossible (ID introuvable ou API indisponible)"
        confidence, needs_review = 1.0, False
    else:
        candidates = await search_by_title(film.get("nom", ""), "ANIME")
        if not candidates:
            return False, "Aucun résultat AniList"
        media, confidence = _best_match(film.get("nom", ""), None, candidates)
        if not media:
            return False, "Aucun candidat exploitable"
        needs_review = confidence < _CONFIDENCE_THRESHOLD

    enrichment = await build_enrichment(media, "ANIME", confidence, needs_review, None)
    ok = await repo.set_film_enrichment(slug, film_slug, enrichment)
    if not ok:
        return False, "Film introuvable en DB au moment de l'écriture"
    return True, None


async def enrichir_films(batch_size: int = 50) -> dict:
    """
    Enrichit individuellement jusqu'à `batch_size` films (toutes catalogues confondus —
    un catalogue "anime" a souvent aussi des films, cf. get_catalogues_with_films_needing_enrichment).
    Retourne {"ok": ["slug/film_slug", ...], "errors": {...}}.
    """
    catalogues = await repo.get_catalogues_with_films_needing_enrichment(batch_size)
    ok: list[str] = []
    errors: dict[str, str] = {}
    processed = 0

    for cat in catalogues:
        slug = cat["slug"]
        for film in cat.get("films", []):
            if processed >= batch_size:
                break
            if not _is_stale(film.get("enrichment")) and (film.get("enrichment") or {}).get("anilist_id"):
                continue
            key = f"{slug}/{film['slug']}"
            processed += 1
            try:
                success, reason = await _enrich_film_one(slug, film)
                if success:
                    ok.append(key)
                else:
                    errors[key] = reason or "Échec inconnu"
                    logger.info(f"Enrichissement film : échec pour '{key}' — {reason}")
            except Exception as exc:
                logger.exception(f"Enrichissement film : erreur inattendue pour '{key}'")
                errors[key] = str(exc)

    logger.info(f"Enrichissement films : {len(ok)}/{processed} réussis")
    return {"ok": ok, "errors": errors}


async def enrichir_catalogue(type_contenu: str, batch_size: int = 50) -> dict:
    """
    Enrichit jusqu'à `batch_size` entrées du type donné dont l'enrichment est absent
    ou périmé (> 30 jours). Idempotent — sûr à ré-exécuter.
    Retourne {"ok": [...], "errors": {...}}.

    type_contenu="film" est un cas particulier : délègue à enrichir_films() car les films
    sont enrichis individuellement (un catalogue peut en contenir plusieurs), pas au
    niveau catalogue comme anime/scan.
    """
    if type_contenu == "film":
        return await enrichir_films(batch_size)

    if type_contenu not in TYPE_MAP:
        return {"ok": [], "errors": {"_global": f"type_contenu non enrichissable : {type_contenu}"}}

    candidates = await repo.get_needing_enrichment(type_contenu, batch_size)
    ok: list[str] = []
    errors: dict[str, str] = {}

    for cat in candidates:
        slug = cat["slug"]
        try:
            success, reason = await _enrich_one(cat)
            if success:
                ok.append(slug)
            else:
                errors[slug] = reason or "Échec inconnu"
                logger.info(f"Enrichissement : échec pour '{slug}' — {reason}")
        except Exception as exc:
            logger.exception(f"Enrichissement : erreur inattendue pour '{slug}'")
            errors[slug] = str(exc)

    logger.info(f"Enrichissement {type_contenu} : {len(ok)}/{len(candidates)} réussis")
    return {"ok": ok, "errors": errors}


async def enrichir_tous() -> None:
    """Appelé par APScheduler : enrichit anime, film puis scan. Ne lève jamais."""
    for type_contenu in TYPE_MAP:
        try:
            result = await enrichir_catalogue(type_contenu, batch_size=50)
            logger.info(
                f"Enrichissement planifié '{type_contenu}' : "
                f"{len(result['ok'])} ok, {len(result['errors'])} erreurs"
            )
        except Exception:
            logger.exception(f"Enrichissement planifié : échec global pour '{type_contenu}'")
