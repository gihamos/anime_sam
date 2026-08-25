from datetime import datetime, timezone
from bson import ObjectId
from db.connection import get_db

COLLECTION = "tickets"


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(tid: str) -> ObjectId | None:
    try:
        return ObjectId(tid)
    except Exception:
        return None


async def create(username: str, subject: str, message: str) -> str:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    doc = {
        "username":   username,
        "subject":    subject,
        "status":     "open",
        "messages": [{
            "author_role":     "customer",
            "author_username": username,
            "body":            message,
            "created_at":      now,
        }],
        "created_at": now,
        "updated_at": now,
    }
    result = await db[COLLECTION].insert_one(doc)
    return str(result.inserted_id)


async def find_by_id(tid: str) -> dict | None:
    oid = _oid(tid)
    if not oid:
        return None
    db = get_db()
    doc = await db[COLLECTION].find_one({"_id": oid})
    return _clean(doc) if doc else None


async def list_for_user(username: str) -> list[dict]:
    db = get_db()
    docs = await db[COLLECTION].find({"username": username}).sort("updated_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def list_all(status: str | None = None) -> list[dict]:
    db = get_db()
    query = {"status": status} if status else {}
    docs = await db[COLLECTION].find(query).sort("updated_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def add_message(tid: str, author_role: str, author_username: str, body: str) -> bool:
    oid = _oid(tid)
    if not oid:
        return False
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    message = {
        "author_role":     author_role,
        "author_username": author_username,
        "body":             body,
        "created_at":       now,
    }
    fields: dict = {"updated_at": now}
    # Rouvre un ticket clos/en attente si le client répond ; passe "pending" si l'admin répond
    if author_role == "admin":
        fields["status"] = "pending"
    else:
        fields["status"] = "open"
    r = await db[COLLECTION].update_one(
        {"_id": oid},
        {"$push": {"messages": message}, "$set": fields},
    )
    return r.matched_count > 0


async def set_status(tid: str, status: str) -> bool:
    oid = _oid(tid)
    if not oid:
        return False
    db = get_db()
    r = await db[COLLECTION].update_one(
        {"_id": oid},
        {"$set": {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()}},
    )
    return r.matched_count > 0
