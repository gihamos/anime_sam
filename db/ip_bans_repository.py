"""
Bannissement d'adresses IP.

Cache en mémoire pour les vérifications rapides (aucun accès DB par requête).
Le cache est rechargé au démarrage puis mis à jour immédiatement à chaque ban/unban.
"""

from datetime import datetime, timezone
from db.connection import get_db

# ── Cache en mémoire ──────────────────────────────────────────────────────────
_banned: set[str] = set()


async def load() -> None:
    """Charge tous les bans depuis MongoDB (appelé au démarrage)."""
    global _banned
    db = get_db()
    docs = await db.ip_bans.find({}, {"ip": 1}).to_list(None)
    _banned = {d["ip"] for d in docs}


def is_banned(ip: str) -> bool:
    """Vérifie en mémoire — O(1), aucun accès DB."""
    return ip in _banned


async def add_ban(ip: str, reason: str = "", banned_by: str = "admin") -> None:
    global _banned
    _banned.add(ip)
    db = get_db()
    await db.ip_bans.update_one(
        {"ip": ip},
        {"$set": {
            "ip":         ip,
            "reason":     reason,
            "banned_by":  banned_by,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )


async def remove_ban(ip: str) -> bool:
    global _banned
    _banned.discard(ip)
    db = get_db()
    r = await db.ip_bans.delete_one({"ip": ip})
    return r.deleted_count > 0


async def list_bans() -> list[dict]:
    db = get_db()
    return await db.ip_bans.find({}, {"_id": 0}).sort("created_at", -1).to_list(None)
