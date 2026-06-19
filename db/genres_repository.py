"""
Dépôt pour les genres disponibles sur anime-sama.to.
Stockés dans la collection `site_genres` (document unique).
"""

from datetime import datetime, timezone
from db.connection import get_db

_COLLECTION = "site_genres"
_DOC_ID     = "genres_v1"


async def get_all() -> list[str]:
    db  = get_db()
    doc = await db[_COLLECTION].find_one({"_id": _DOC_ID})
    if not doc:
        return []
    return [
        g for g in doc.get("genres", [])
        if g and len(g.strip()) >= 2 and any(c.isalpha() for c in g)
    ]


async def save_all(genres: list[str]) -> None:
    # Double validation : ignorer les entrées vides, trop courtes ou sans lettre
    clean = sorted({
        g.strip() for g in genres
        if g and g.strip() and len(g.strip()) >= 2 and any(c.isalpha() for c in g)
    })
    if not clean:
        return
    db = get_db()
    await db[_COLLECTION].replace_one(
        {"_id": _DOC_ID},
        {
            "_id":        _DOC_ID,
            "genres":     clean,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        upsert=True,
    )


async def last_sync_at() -> str | None:
    db  = get_db()
    doc = await db[_COLLECTION].find_one({"_id": _DOC_ID}, {"updated_at": 1, "_id": 0})
    return doc.get("updated_at") if doc else None
