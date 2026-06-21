"""Paramètres globaux de l'application (collection `settings`)."""

from datetime import datetime, timezone
from db.connection import get_db


async def get_setting(key: str, default=None):
    db = get_db()
    doc = await db.settings.find_one({"key": key}, {"_id": 0})
    return doc["value"] if doc else default


async def set_setting(key: str, value) -> None:
    db = get_db()
    await db.settings.update_one(
        {"key": key},
        {"$set": {"key": key, "value": value, "updated_at": datetime.now(timezone.utc).isoformat()}},
        upsert=True,
    )
