from datetime import datetime, timezone
from bson import ObjectId
from db.connection import get_db

COLLECTION = "payments"


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


async def create(doc: dict) -> str:
    db = get_db()
    payload = dict(doc)
    payload.setdefault("created_at", datetime.now(timezone.utc).isoformat())
    result = await db[COLLECTION].insert_one(payload)
    return str(result.inserted_id)


async def list_for_user(username: str) -> list[dict]:
    db = get_db()
    docs = await db[COLLECTION].find({"username": username}).sort("paid_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def list_for_subscription(subscription_id: str) -> list[dict]:
    db = get_db()
    docs = await db[COLLECTION].find({"subscription_id": subscription_id}).sort("paid_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def find_by_provider_payment_id(provider_payment_id: str) -> dict | None:
    db = get_db()
    doc = await db[COLLECTION].find_one({"provider_payment_id": provider_payment_id})
    return _clean(doc) if doc else None
