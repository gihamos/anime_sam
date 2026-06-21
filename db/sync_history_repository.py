"""Historique des synchronisations."""

from db.connection import get_db

COLLECTION = "sync_history"


def _col():
    return get_db()[COLLECTION]


async def add_entry(entry: dict) -> None:
    await _col().insert_one(entry)


async def get_recent(limit: int = 60) -> list[dict]:
    cursor = _col().find({}, {"_id": 0}).sort("started_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def get_for_slug(slug: str, limit: int = 20) -> list[dict]:
    cursor = _col().find({"slug": slug}, {"_id": 0}).sort("started_at", -1).limit(limit)
    return await cursor.to_list(length=limit)


async def delete_all() -> int:
    r = await _col().delete_many({})
    return r.deleted_count


async def delete_by_slug(slug: str) -> int:
    r = await _col().delete_many({"slug": slug})
    return r.deleted_count
