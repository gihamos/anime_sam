"""
Repository MongoDB pour les clients API tiers.

Collection : api_clients
"""

from typing import Optional
from datetime import datetime, timezone
from db.connection import get_db

COLLECTION = "api_clients"


def _col():
    try:
        return get_db()[COLLECTION]
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(e))


def _clean(doc: dict) -> dict:
    doc = dict(doc)
    doc["_id"] = str(doc.get("_id", ""))
    doc.pop("client_secret_hash", None)
    return doc


async def find_by_client_id(client_id: str) -> Optional[dict]:
    """Retourne le document brut avec le hash (pour vérification)."""
    return await _col().find_one({"client_id": client_id})


async def list_clients() -> list[dict]:
    cursor = _col().find({})
    return [_clean(doc) async for doc in cursor]


async def create_client(doc: dict) -> str:
    result = await _col().insert_one(doc)
    return str(result.inserted_id)


async def update_client(client_id: str, fields: dict) -> bool:
    fields["updated_at"] = datetime.now(timezone.utc).isoformat()
    result = await _col().update_one({"client_id": client_id}, {"$set": fields})
    return result.matched_count > 0


async def delete_client(client_id: str) -> bool:
    result = await _col().delete_one({"client_id": client_id})
    return result.deleted_count > 0
