"""Repository pour les programmations de sync automatique."""

from datetime import datetime, timezone
from typing import Optional
from bson import ObjectId
from db.connection import get_db

COLLECTION = "sync_schedules"


def _col():
    return get_db()[COLLECTION]


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


async def create(doc: dict) -> str:
    result = await _col().insert_one(doc)
    return str(result.inserted_id)


async def list_all() -> list[dict]:
    cursor = _col().find({}).sort("created_at", -1)
    return [_clean(d) async for d in cursor]


async def find_by_id(sid: str) -> Optional[dict]:
    try:
        doc = await _col().find_one({"_id": ObjectId(sid)})
        return _clean(doc) if doc else None
    except Exception:
        return None


async def find_active() -> list[dict]:
    cursor = _col().find({"active": True})
    return [_clean(d) async for d in cursor]


async def update(sid: str, fields: dict) -> bool:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    try:
        r = await _col().update_one({"_id": ObjectId(sid)}, {"$set": fields})
        return r.matched_count > 0
    except Exception:
        return False


async def delete(sid: str) -> bool:
    try:
        r = await _col().delete_one({"_id": ObjectId(sid)})
        return r.deleted_count > 0
    except Exception:
        return False
