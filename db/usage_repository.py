"""Suivi du quota de synchronisation par utilisateur / client API."""

from datetime import datetime, timezone
from typing import Optional
from db.connection import get_db
from pymongo import ReturnDocument

COLLECTION = "sync_usage"


def _col():
    return get_db()[COLLECTION]


def _period_key(period: str) -> str:
    now = datetime.now(timezone.utc)
    if period == "day":  return now.strftime("%Y-%m-%d")
    if period == "year": return now.strftime("%Y")
    return now.strftime("%Y-%m")  # month (défaut)


async def increment(entity_id: str, period: str) -> int:
    """Incrémente le compteur et retourne la nouvelle valeur."""
    pk = _period_key(period)
    doc = await _col().find_one_and_update(
        {"entity_id": entity_id, "period_key": pk},
        {"$inc": {"count": 1}, "$set": {"period": period}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return doc["count"]


async def get_count(entity_id: str, period: str) -> int:
    pk = _period_key(period)
    doc = await _col().find_one({"entity_id": entity_id, "period_key": pk})
    return doc["count"] if doc else 0


async def get_usage_info(entity_id: str) -> Optional[dict]:
    """Retourne tous les compteurs actifs pour une entité."""
    cursor = _col().find({"entity_id": entity_id}, {"_id": 0})
    return await cursor.to_list(length=None)
