"""
Repository MongoDB pour les catalogues anime-sama.

Collection : catalogues
Index :
  - slug          (unique)
  - nom           (text search)
  - etat
  - type_contenu
  - genres
  - langues
"""

from typing import Optional
from datetime import datetime, timedelta, timezone
from db.connection import get_db
from models.catalogue import Catalogue

COLLECTION = "catalogues"


def _col():
    try:
        return get_db()[COLLECTION]
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


def _clean(doc: dict) -> dict:
    doc["_id"] = str(doc["_id"])
    return doc


# ---------------------------------------------------------------------------
# Lecture
# ---------------------------------------------------------------------------

async def find_by_slug(slug: str) -> Optional[dict]:
    doc = await _col().find_one({"slug": slug})
    return _clean(doc) if doc else None


async def find_slugs(slugs: list[str]) -> set[str]:
    """Sous-ensemble de `slugs` déjà présents en base — évite un aller-retour DB par résultat
    pour marquer `in_db` sur une liste (ex. résultats de recherche TMDB)."""
    if not slugs:
        return set()
    cursor = _col().find({"slug": {"$in": slugs}}, {"slug": 1})
    return {d["slug"] async for d in cursor}


async def search_with_filters(
    q:             Optional[str]       = None,
    type_contenu:  Optional[str]       = None,
    lang:          Optional[str]       = None,
    etat:          Optional[str]       = None,
    genres:        Optional[list[str]] = None,
    page:          int                 = 1,
    limit:         int                 = 20,
) -> list[dict]:
    """
    Recherche dans la DB avec filtres combinables.
    q         → regex insensible à la casse sur nom + titre_alternatif
    type_contenu → "anime" | "scan" | "film" | "autre"
    lang      → code langue présent dans le champ langues
    etat      → "en_cours" | "termine" | "abandonne"
    genres    → liste de genres (ET logique)
    """
    query: dict = {}

    if q:
        query["$or"] = [
            {"nom":              {"$regex": q, "$options": "i"}},
            {"titre_alternatif": {"$regex": q, "$options": "i"}},
        ]
    if type_contenu == "scan":
        # Un catalogue "anime" peut aussi avoir des scans attachés (contenu mixte) —
        # on filtre sur la présence réelle de scans plutôt que sur le type_contenu
        # principal, sinon ces catalogues sont invisibles depuis la recherche "scan".
        query["scans.0"] = {"$exists": True}
    elif type_contenu == "film":
        query["films.0"] = {"$exists": True}
    elif type_contenu:
        query["type_contenu"] = type_contenu
    if lang:
        query["langues"] = lang
    if etat:
        query["etat"] = etat
    if genres:
        query["genres"] = {"$all": genres}

    skip   = (page - 1) * limit
    cursor = _col().find(
        query,
        # Projection en exclusion pure (comme get_visible_summary) : tout est
        # inclus par défaut sauf les listes lourdes imbriquées. Mélanger une
        # inclusion de champ ("saisons": 1) avec l'exclusion d'un sous-champ
        # ("saisons.episodes": 0) fait planter MongoDB ("Path collision").
        {
            "saisons.episodes": 0,
            "films.videos":     0,
            "scans.chapitres":  0,
        }
    ).skip(skip).limit(limit)

    return [_clean(d) async for d in cursor]


async def get_all_en_cours() -> list[dict]:
    cursor = _col().find(
        {"etat": "en_cours"},
        {"slug": 1, "nom": 1, "etat": 1}
    )
    return [_clean(d) async for d in cursor]


async def count_all() -> int:
    return await _col().count_documents({})


async def get_all_summary(skip: int = 0, limit: int = 100) -> list[dict]:
    """Résumé léger — admin uniquement (pas de filtrage visibilité).
    `limit=0` retourne tout (utilisé par la vue de gestion complète, qui filtre
    côté client — sans ça, les catalogues ajoutés après les 100 premiers en base
    devenaient invisibles dans l'interface admin)."""
    cursor = _col().find(
        {},
        {"slug": 1, "nom": 1, "etat": 1, "type_contenu": 1,
         "genres": 1, "langues": 1, "updated_at": 1, "episodes_synced": 1,
         "enrichment": 1}
    ).skip(skip)
    if limit:
        cursor = cursor.limit(limit)
    return [_clean(d) async for d in cursor]


async def get_reco_candidates() -> list[dict]:
    """Champs pour le moteur de recommandations (inclut image, annee, note, visibility,
    enrichment — nécessaire au calcul de similarité par vecteurs pondérés)."""
    cursor = _col().find(
        {},
        {
            "slug": 1, "nom": 1, "image": 1, "genres": 1,
            "type_contenu": 1, "etat": 1, "annee": 1,
            "langue": 1, "note": 1, "updated_at": 1,
            "visibility": 1, "enrichment": 1,
        }
    )
    return [_clean(d) async for d in cursor]


async def count_visible() -> int:
    return await _col().count_documents({})


async def get_visible_summary(skip: int = 0, limit: int = 100) -> list[dict]:
    """
    Résumé complet avec visibilité, structure saisons/films/scans,
    mais sans épisodes/chapitres/vidéos (données lourdes exclues).
    Utilisé par la route publique pour filtrer selon les droits d'accès.
    """
    # `enrichment` inclus (n'est pas exclu ici, contrairement aux listes lourdes ci-dessus) :
    # nécessaire à l'app mobile pour afficher score/bannière/genres_fr sans requête détail.
    cursor = _col().find(
        {},
        {"saisons.episodes": 0, "films.videos": 0, "scans.chapitres": 0},
    ).skip(skip).limit(limit)
    return [_clean(d) async for d in cursor]


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

async def save_catalogue(catalogue: Catalogue) -> str:
    """Insère ou met à jour un catalogue (upsert par slug)."""
    now  = datetime.now(timezone.utc).isoformat()
    # `enrichment` exclu volontairement : un Catalogue fraîchement scrapé n'a jamais ce
    # champ renseigné (default_factory=dict), donc l'inclure ici effacerait à chaque
    # re-scrape (ex. bouton "Rafraîchir") tout l'enrichissement AniList déjà en place.
    # Seul le pipeline d'enrichissement (repo.set_enrichment) écrit ce champ.
    data = catalogue.model_dump(mode="json", exclude={"enrichment"})
    data["updated_at"] = now

    existing = await _col().find_one({"slug": catalogue.slug}, {"created_at": 1})
    if not existing:
        data["created_at"] = now

    result = await _col().update_one(
        {"slug": catalogue.slug},
        {"$set": data},
        upsert=True,
    )
    return str(result.upserted_id) if result.upserted_id else catalogue.slug


async def update_saison_episodes(
    slug:         str,
    saison_index: int,
    episodes:     list[dict],
) -> None:
    """Met à jour les épisodes d'une saison précise (par index dans le tableau)."""
    await _col().update_one(
        {"slug": slug},
        {
            "$set": {
                f"saisons.{saison_index}.episodes":       episodes,
                f"saisons.{saison_index}.total_episodes": len(episodes),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    )


async def update_film_videos(
    slug:       str,
    film_index: int,
    videos:     list[dict],
) -> None:
    """Met à jour les vidéos d'un film précis (par index dans le tableau)."""
    await _col().update_one(
        {"slug": slug},
        {
            "$set": {
                f"films.{film_index}.videos": videos,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    )


async def update_scan_chapitres(
    slug:       str,
    scan_index: int,
    chapitres:  list[dict],
) -> None:
    """Met à jour les chapitres d'un scan précis (par index dans le tableau)."""
    await _col().update_one(
        {"slug": slug},
        {
            "$set": {
                f"scans.{scan_index}.chapitres": chapitres,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        }
    )


async def mark_content_synced(slug: str) -> None:
    await _col().update_one(
        {"slug": slug},
        {"$set": {"episodes_synced": True,
                  "updated_at": datetime.now(timezone.utc).isoformat()}}
    )


_META_FIELDS = {"nom", "titre_alternatif", "synopsis", "genres", "langues", "etat", "type_contenu"}

async def update_catalogue_metadata(slug: str, fields: dict) -> bool:
    """Met à jour les champs de métadonnées éditables d'un catalogue."""
    clean = {k: v for k, v in fields.items() if k in _META_FIELDS and v is not None}
    if not clean:
        return True
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await _col().update_one({"slug": slug}, {"$set": clean})
    return result.matched_count > 0


async def update_catalogue_visibility(slug: str, visibility: dict) -> bool:
    """Met à jour les paramètres de visibilité/accès public d'un catalogue."""
    result = await _col().update_one(
        {"slug": slug},
        {"$set": {
            "visibility":  visibility,
            "updated_at":  datetime.now(timezone.utc).isoformat(),
        }}
    )
    return result.matched_count > 0


# ---------------------------------------------------------------------------
# Enrichissement AniList
# ---------------------------------------------------------------------------

async def get_needing_enrichment(type_contenu: str, limit: int = 50) -> list[dict]:
    """
    Catalogues d'un type donné dont l'enrichissement est absent/vide, ou périmé
    (> 30 jours) — base de la sélection idempotente du job d'enrichissement.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    query = {
        "type_contenu": type_contenu,
        "$or": [
            {"enrichment": {"$exists": False}},
            {"enrichment": {}},
            {"enrichment.enriched_at": {"$exists": False}},
            {"enrichment.enriched_at": {"$lt": cutoff}},
        ],
    }
    cursor = _col().find(
        query,
        {"slug": 1, "nom": 1, "titre_alternatif": 1, "synopsis": 1,
         "type_contenu": 1, "enrichment.anilist_id": 1},
    ).limit(limit)
    return [_clean(d) async for d in cursor]


async def get_needs_review(skip: int = 0, limit: int = 100) -> list[dict]:
    """Catalogues dont l'appariement AniList est incertain (enrichment.needs_review)."""
    cursor = _col().find(
        {"enrichment.needs_review": True},
        {"slug": 1, "nom": 1, "type_contenu": 1, "enrichment": 1},
    ).skip(skip).limit(limit)
    return [_clean(d) async for d in cursor]


async def set_enrichment(slug: str, enrichment: dict) -> bool:
    """
    Écrit le sous-document enrichment en $set dot-path (une clé = un champ), pour ne
    jamais toucher saisons/films/scans/metadata/autres champs top-level. Écriture
    partielle, idempotente — sûre à ré-exécuter.
    """
    clean = {f"enrichment.{k}": v for k, v in enrichment.items() if v is not None}
    if not clean:
        return True
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await _col().update_one({"slug": slug}, {"$set": clean})
    return result.matched_count > 0


async def get_catalogues_with_films_needing_enrichment(limit: int = 50) -> list[dict]:
    """
    Catalogues ayant AU MOINS un film dont l'enrichissement est absent/vide ou périmé
    (> 30 jours). Un catalogue peut contenir plusieurs films (franchise) — chacun est
    apparié individuellement à AniList, pas le catalogue dans son ensemble. `films` peut
    exister sur n'importe quel type_contenu (un catalogue "anime" a souvent aussi des
    films), donc pas de filtre sur type_contenu ici.
    """
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    query = {
        "films.0": {"$exists": True},
        "films": {"$elemMatch": {"$or": [
            {"enrichment": {"$exists": False}},
            {"enrichment": {}},
            {"enrichment.enriched_at": {"$exists": False}},
            {"enrichment.enriched_at": {"$lt": cutoff}},
        ]}},
    }
    cursor = _col().find(query, {"slug": 1, "films": 1}).limit(limit)
    return [_clean(d) async for d in cursor]


async def set_film_enrichment(slug: str, film_slug: str, enrichment: dict) -> bool:
    """$set dot-path sur le film identifié par son slug (arrayFilters) — n'affecte que lui."""
    clean = {f"films.$[f].enrichment.{k}": v for k, v in enrichment.items() if v is not None}
    if not clean:
        return True
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await _col().update_one(
        {"slug": slug},
        {"$set": clean},
        array_filters=[{"f.slug": film_slug}],
    )
    return result.matched_count > 0


async def set_episode_enrichment(slug: str, saison_slug: str, numero: int, enrichment: dict) -> bool:
    """
    $set dot-path sur l'épisode identifié par (saison_slug, numero) via arrayFilters —
    n'affecte que cet épisode précis, dans cette saison précise.
    """
    clean = {f"saisons.$[s].episodes.$[e].enrichment.{k}": v for k, v in enrichment.items() if v is not None}
    if not clean:
        return True
    clean["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await _col().update_one(
        {"slug": slug},
        {"$set": clean},
        array_filters=[{"s.slug": saison_slug}, {"e.numero": numero}],
    )
    return result.matched_count > 0


# ---------------------------------------------------------------------------
# Suppression
# ---------------------------------------------------------------------------

async def delete_by_slug(slug: str) -> bool:
    result = await _col().delete_one({"slug": slug})
    return result.deleted_count > 0
