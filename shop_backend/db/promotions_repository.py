from datetime import datetime, timezone
from bson import ObjectId
from db.connection import get_db

COLLECTION = "promotions"


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(pid: str) -> ObjectId | None:
    try:
        return ObjectId(pid)
    except Exception:
        return None


async def list_all() -> list[dict]:
    db = get_db()
    docs = await db[COLLECTION].find({}).sort("created_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def find_by_id(pid: str) -> dict | None:
    oid = _oid(pid)
    if not oid:
        return None
    db = get_db()
    doc = await db[COLLECTION].find_one({"_id": oid})
    return _clean(doc) if doc else None


async def find_by_code(code: str) -> dict | None:
    db = get_db()
    doc = await db[COLLECTION].find_one({"code": code.upper()})
    return _clean(doc) if doc else None


async def create(doc: dict) -> str:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    payload = dict(doc)
    payload["code"] = payload["code"].upper()
    payload["used_count"] = 0
    payload["created_at"] = now
    payload["updated_at"] = now
    result = await db[COLLECTION].insert_one(payload)
    return str(result.inserted_id)


async def update(pid: str, fields: dict) -> bool:
    oid = _oid(pid)
    if not oid:
        return False
    db = get_db()
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await db[COLLECTION].update_one({"_id": oid}, {"$set": fields})
    return r.matched_count > 0


async def delete(pid: str) -> bool:
    oid = _oid(pid)
    if not oid:
        return False
    db = get_db()
    r = await db[COLLECTION].delete_one({"_id": oid})
    return r.deleted_count > 0


async def increment_usage(code: str) -> None:
    db = get_db()
    await db[COLLECTION].update_one({"code": code.upper()}, {"$inc": {"used_count": 1}})
