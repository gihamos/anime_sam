from typing import Optional
from db.connection import get_db

COLLECTION = "users"


def _col():
    return get_db()[COLLECTION]


async def find_by_username(username: str) -> Optional[dict]:
    return await _col().find_one({"username": username}, {"_id": 0})


async def create_user(user_doc: dict) -> None:
    await _col().insert_one(user_doc)


async def update_user(username: str, fields: dict) -> bool:
    result = await _col().update_one({"username": username}, {"$set": fields})
    return result.modified_count > 0


async def delete_user(username: str) -> bool:
    result = await _col().delete_one({"username": username})
    return result.deleted_count > 0


async def list_users() -> list[dict]:
    cursor = _col().find({}, {"_id": 0, "hashed_password": 0})
    return await cursor.to_list(length=None)


async def count_users() -> int:
    return await _col().count_documents({})
