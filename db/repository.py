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
from datetime import datetime, timezone
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
    if type_contenu:
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
        # Projection : retourner un résumé sans les listes d'épisodes (potentiellement volumineuses)
        {
            "slug": 1, "nom": 1, "titre_alternatif": 1, "image": 1,
            "genres": 1, "langues": 1, "etat": 1, "type_contenu": 1,
            "synopsis": 1, "episodes_synced": 1, "updated_at": 1,
            "saisons": {"$slice": 0},   # exclure les épisodes du résumé
            "films":   {"$slice": 0},
            "scans":   {"$slice": 0},
        }
    ).skip(skip).limit(limit)

    return [_clean(d) async for d in cursor]


async def get_all_en_cours() -> list[dict]:
    cursor = _col().find(
        {"etat": "en_cours"},
        {"slug": 1, "nom": 1, "etat": 1}
    )
    return [_clean(d) async for d in cursor]


async def get_all_summary() -> list[dict]:
    """Résumé léger — admin uniquement (pas de filtrage visibilité)."""
    cursor = _col().find(
        {},
        {"slug": 1, "nom": 1, "etat": 1, "type_contenu": 1,
         "genres": 1, "langues": 1, "updated_at": 1, "episodes_synced": 1}
    )
    return [_clean(d) async for d in cursor]


async def get_reco_candidates() -> list[dict]:
    """Champs pour le moteur de recommandations (inclut image, annee, note, visibility)."""
    cursor = _col().find(
        {},
        {
            "slug": 1, "nom": 1, "image": 1, "genres": 1,
            "type_contenu": 1, "etat": 1, "annee": 1,
            "langue": 1, "note": 1, "updated_at": 1,
            "visibility": 1,
        }
    )
    return [_clean(d) async for d in cursor]


async def get_visible_summary() -> list[dict]:
    """
    Résumé complet avec visibilité, structure saisons/films/scans,
    mais sans épisodes/chapitres/vidéos (données lourdes exclues).
    Utilisé par la route publique pour filtrer selon les droits d'accès.
    """
    cursor = _col().find(
        {},
        {"saisons.episodes": 0, "films.videos": 0, "scans.chapitres": 0},
    )
    return [_clean(d) async for d in cursor]


# ---------------------------------------------------------------------------
# Écriture
# ---------------------------------------------------------------------------

async def save_catalogue(catalogue: Catalogue) -> str:
    """Insère ou met à jour un catalogue (upsert par slug)."""
    now  = datetime.now(timezone.utc).isoformat()
    data = catalogue.model_dump(mode="json")
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
# Suppression
# ---------------------------------------------------------------------------

async def delete_by_slug(slug: str) -> bool:
    result = await _col().delete_one({"slug": slug})
    return result.deleted_count > 0
