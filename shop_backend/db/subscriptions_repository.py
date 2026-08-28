from datetime import datetime, timezone
from bson import ObjectId
from db.connection import get_db

COLLECTION = "subscriptions"

_NON_TERMINAL = {"pending", "active", "past_due", "suspended"}


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["id"] = str(doc.pop("_id"))
    return doc


def _oid(sid: str) -> ObjectId | None:
    try:
        return ObjectId(sid)
    except Exception:
        return None


async def create(doc: dict) -> str:
    db = get_db()
    now = datetime.now(timezone.utc).isoformat()
    payload = dict(doc)
    payload["created_at"] = now
    payload["updated_at"] = now
    result = await db[COLLECTION].insert_one(payload)
    return str(result.inserted_id)


async def find_by_id(sid: str) -> dict | None:
    oid = _oid(sid)
    if not oid:
        return None
    db = get_db()
    doc = await db[COLLECTION].find_one({"_id": oid})
    return _clean(doc) if doc else None


async def find_by_provider_subscription_id(provider: str, provider_subscription_id: str) -> dict | None:
    db = get_db()
    doc = await db[COLLECTION].find_one({
        "provider": provider,
        "provider_subscription_id": provider_subscription_id,
    })
    return _clean(doc) if doc else None


async def find_current_for_user(username: str) -> dict | None:
    db = get_db()
    doc = await db[COLLECTION].find_one({
        "username": username,
        "status": {"$in": list(_NON_TERMINAL)},
    })
    return _clean(doc) if doc else None


async def list_for_user(username: str) -> list[dict]:
    db = get_db()
    docs = await db[COLLECTION].find({"username": username}).sort("created_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def list_all(status: str | None = None, plan_id: str | None = None, search: str | None = None) -> list[dict]:
    db = get_db()
    query: dict = {}
    if status:
        query["status"] = status
    if plan_id:
        query["plan_id"] = plan_id
    if search:
        query["username"] = {"$regex": search, "$options": "i"}
    docs = await db[COLLECTION].find(query).sort("created_at", -1).to_list(None)
    return [_clean(d) for d in docs]


async def update(sid: str, fields: dict) -> bool:
    oid = _oid(sid)
    if not oid:
        return False
    db = get_db()
    fields = dict(fields)
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    r = await db[COLLECTION].update_one({"_id": oid}, {"$set": fields})
    return r.matched_count > 0


async def delete(sid: str) -> bool:
    """Réservé au rollback d'une souscription 'pending' jamais confirmée côté fournisseur
    (ex. échec de création côté PayPal juste après création du document local) — un
    abonnement qui a réellement existé côté fournisseur ne doit jamais être supprimé,
    seulement transitionné de statut (historique de facturation)."""
    oid = _oid(sid)
    if not oid:
        return False
    db = get_db()
    r = await db[COLLECTION].delete_one({"_id": oid})
    return r.deleted_count > 0


async def count_by_plan(plan_id: str) -> int:
    db = get_db()
    return await db[COLLECTION].count_documents({
        "plan_id": plan_id,
        "status": {"$in": list(_NON_TERMINAL)},
    })


async def list_expiring_cancellations(before_iso: str) -> list[dict]:
    """Abonnements annulés (accès conservé jusqu'à current_period_end) dont la période
    payée est désormais terminée — alimente le job planifié de désactivation."""
    db = get_db()
    docs = await db[COLLECTION].find({
        "cancel_at_period_end": True,
        "status": {"$in": ["active", "cancelled"]},
        "current_period_end": {"$lt": before_iso},
    }).to_list(None)
    return [_clean(d) for d in docs]


async def delete_stale_pending(before_iso: str) -> int:
    """Supprime les tentatives 'pending' jamais finalisées côté PayPal (approbation
    abandonnée, onglet fermé...) et créées avant `before_iso` — filet de sécurité pour les
    clients qui n'ont jamais cliqué sur 'annuler' eux-mêmes (cf. self-service dans
    api/routes/billing.py). Retourne le nombre supprimé."""
    db = get_db()
    r = await db[COLLECTION].delete_many({
        "status": "pending",
        "created_at": {"$lt": before_iso},
    })
    return r.deleted_count
