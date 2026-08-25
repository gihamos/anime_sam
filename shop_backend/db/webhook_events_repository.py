from datetime import datetime, timezone
from pymongo.errors import DuplicateKeyError
from db.connection import get_db

COLLECTION = "webhook_events"


async def try_record(provider: str, event_id: str, event_type: str, raw: dict) -> bool:
    """Tente d'enregistrer un événement webhook. Retourne False s'il a déjà été traité
    (PayPal redélivre ses événements — c'est le mécanisme d'idempotence)."""
    db = get_db()
    try:
        await db[COLLECTION].insert_one({
            "provider":     provider,
            "event_id":     event_id,
            "event_type":   event_type,
            "received_at":  datetime.now(timezone.utc).isoformat(),
            "raw":          raw,
        })
        return True
    except DuplicateKeyError:
        return False
