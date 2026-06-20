from datetime import datetime, timezone
from bson import ObjectId
from db.connection import get_db


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(gid: str) -> ObjectId | None:
    try:
        return ObjectId(gid)
    except Exception:
        return None


async def list_all() -> list[dict]:
    db = get_db()
    docs = await db.groups.find({}).sort("name", 1).to_list(None)
    return [_clean(d) for d in docs]


async def find_by_id(gid: str) -> dict | None:
    oid = _oid(gid)
    if not oid:
        return None
    db = get_db()
    doc = await db.groups.find_one({"_id": oid})
    return _clean(doc) if doc else None


async def find_by_ids(gids: list[str]) -> list[dict]:
    oids = [o for g in gids if (o := _oid(g))]
    if not oids:
        return []
    db = get_db()
    docs = await db.groups.find({"_id": {"$in": oids}}).to_list(None)
    return [_clean(d) for d in docs]


async def create(doc: dict) -> str:
    db = get_db()
    result = await db.groups.insert_one(doc)
    return str(result.inserted_id)


async def update(gid: str, fields: dict) -> bool:
    oid = _oid(gid)
    if not oid:
        return False
    db = get_db()
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await db.groups.update_one({"_id": oid}, {"$set": fields})
    return r.matched_count > 0


async def delete(gid: str) -> bool:
    oid = _oid(gid)
    if not oid:
        return False
    db = get_db()
    r = await db.groups.delete_one({"_id": oid})
    return r.deleted_count > 0


async def count_members(gid: str) -> int:
    db = get_db()
    return await db.users.count_documents({"groups": ObjectId(gid)})


async def list_members(gid: str) -> list[dict]:
    db = get_db()
    cursor = db.users.find({"groups": gid}, {"_id": 0, "hashed_password": 0})
    return await cursor.to_list(None)


async def list_unique_genres() -> list[str]:
    """Retourne tous les genres distincts de la collection catalogues."""
    db = get_db()
    result = await db.catalogues.distinct("genres")
    return sorted(result)
