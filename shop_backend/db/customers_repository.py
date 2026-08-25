from typing import Optional
from db.connection import get_db

COLLECTION = "customers"


def _col():
    return get_db()[COLLECTION]


async def find_by_username(username: str) -> Optional[dict]:
    return await _col().find_one({"username": username}, {"_id": 0})


async def create_customer(doc: dict) -> None:
    await _col().insert_one(doc)


async def update_customer(username: str, fields: dict) -> bool:
    result = await _col().update_one({"username": username}, {"$set": fields})
    return result.modified_count > 0


async def count_customers() -> int:
    return await _col().count_documents({})


async def list_customers() -> list[dict]:
    cursor = _col().find({}, {"_id": 0, "hashed_password": 0})
    return await cursor.to_list(length=None)
