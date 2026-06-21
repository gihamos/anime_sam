"""
Suivi des téléchargements et gestion des quotas de téléchargement.

Collection `downloads`  → historique
Collection `dl_quotas`  → quotas par utilisateur (__default__ = valeur globale)
"""

from datetime import datetime, timezone, timedelta
from db.connection import get_db


def _hist():
    return get_db()["downloads"]


def _quotas():
    return get_db()["dl_quotas"]


# ── Quota par défaut ──────────────────────────────────────────────────────────

_DEFAULT_QUOTA = {
    "max_files_per_day": 20,
    "max_gb_per_day":    10.0,
    "can_download":      True,
}


# ── Lecture historique ────────────────────────────────────────────────────────

async def list_recent(limit: int = 200) -> list[dict]:
    cursor = _hist().find({}, {"_id": 0}).sort("date", -1).limit(limit)
    return await cursor.to_list(None)


async def usage_today(username: str) -> dict:
    """Retourne {count, bytes} pour les dernières 24 h."""
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    pipeline = [
        {"$match": {"username": username, "date": {"$gte": since}}},
        {"$group": {
            "_id":   None,
            "count": {"$sum": "$nb_files"},
            "bytes": {"$sum": "$size_bytes"},
        }},
    ]
    rows = await _hist().aggregate(pipeline).to_list(1)
    return {"count": rows[0]["count"], "bytes": rows[0]["bytes"]} if rows else {"count": 0, "bytes": 0}


# ── Enregistrement ────────────────────────────────────────────────────────────

async def record(
    username:     str,
    slug:         str,
    dl_type:      str,  # "episode" | "film" | "season"
    nb_files:     int   = 1,
    size_bytes:   int   = 0,
    details:      str   = "",
) -> None:
    await _hist().insert_one({
        "username":   username,
        "slug":       slug,
        "type":       dl_type,
        "nb_files":   nb_files,
        "size_bytes": size_bytes,
        "details":    details,
        "date":       datetime.now(timezone.utc).isoformat(),
    })


# ── Quotas ────────────────────────────────────────────────────────────────────

async def get_quota(username: str) -> dict:
    """Retourne le quota de l'utilisateur (ou le quota global, ou le défaut)."""
    q = await _quotas().find_one({"username": username}, {"_id": 0})
    if not q:
        q = await _quotas().find_one({"username": "__default__"}, {"_id": 0})
    return q or dict(_DEFAULT_QUOTA)


async def set_quota(
    username:          str,
    max_files_per_day: int,
    max_gb_per_day:    float,
    can_download:      bool = True,
) -> None:
    await _quotas().update_one(
        {"username": username},
        {"$set": {
            "username":          username,
            "max_files_per_day": max_files_per_day,
            "max_gb_per_day":    max_gb_per_day,
            "can_download":      can_download,
        }},
        upsert=True,
    )


async def delete_quota(username: str) -> bool:
    r = await _quotas().delete_one({"username": username})
    return r.deleted_count > 0


async def list_quotas() -> list[dict]:
    cursor = _quotas().find({}, {"_id": 0}).sort("username", 1)
    return await cursor.to_list(None)


# ── Suppression historique ───────────────────────────────────────────────────

async def delete_all() -> int:
    r = await _hist().delete_many({})
    return r.deleted_count


async def delete_by_username(username: str) -> int:
    r = await _hist().delete_many({"username": username})
    return r.deleted_count


async def delete_by_slug(slug: str) -> int:
    r = await _hist().delete_many({"slug": slug})
    return r.deleted_count


# ── Vérification ──────────────────────────────────────────────────────────────

async def check(username: str, nb_files: int = 1) -> tuple[bool, str]:
    """
    Vérifie si l'utilisateur peut télécharger `nb_files` fichiers.
    Retourne (True, "") ou (False, raison).
    """
    quota = await get_quota(username)

    if not quota.get("can_download", True):
        return False, "Téléchargement désactivé pour ce compte"

    usage = await usage_today(username)

    max_files = quota.get("max_files_per_day", _DEFAULT_QUOTA["max_files_per_day"])
    if usage["count"] + nb_files > max_files:
        return False, (
            f"Quota dépassé : {usage['count']}/{max_files} fichiers/24 h — "
            f"réessayez demain"
        )

    max_bytes = quota.get("max_gb_per_day", _DEFAULT_QUOTA["max_gb_per_day"]) * 1024 ** 3
    if usage["bytes"] > max_bytes:
        gb_used = usage["bytes"] / 1024 ** 3
        gb_max  = quota["max_gb_per_day"]
        return False, f"Quota volumétrique dépassé : {gb_used:.1f}/{gb_max} Go/24 h"

    return True, ""
