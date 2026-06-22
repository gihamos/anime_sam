"""
Historique des connexions à l'API.

Chaque requête entrante (hors documentation) est enregistrée avec :
  - ip            : adresse IP du client
  - username      : nom d'utilisateur si authentifié (None sinon)
  - method        : méthode HTTP
  - path          : chemin de la requête
  - status_code   : code HTTP de la réponse
  - user_agent    : User-Agent du client
  - timestamp     : date/heure UTC ISO 8601

TTL MongoDB : 90 jours (via index sur le champ `expires_at`).
"""

import asyncio
from datetime import datetime, timezone, timedelta
from db.connection import get_db

COLLECTION  = "access_logs"
TTL_DAYS    = 90
_SKIP_PATHS = {"/docs", "/openapi.json", "/", "/favicon.ico"}


# ── Écriture ──────────────────────────────────────────────────────────────────

def log_request_bg(
    ip: str,
    username: str | None,
    method: str,
    path: str,
    status_code: int,
    user_agent: str = "",
) -> None:
    """Lance l'insertion en tâche de fond (non bloquant)."""
    if path in _SKIP_PATHS or path.startswith("/openapi"):
        return
    try:
        asyncio.create_task(_insert(ip, username, method, path, status_code, user_agent))
    except RuntimeError:
        pass  # pas de boucle d'événements active (tests)


async def _insert(
    ip: str,
    username: str | None,
    method: str,
    path: str,
    status_code: int,
    user_agent: str,
) -> None:
    now = datetime.now(timezone.utc)
    doc = {
        "ip":          ip,
        "username":    username,
        "method":      method,
        "path":        path,
        "status_code": status_code,
        "user_agent":  user_agent,
        "timestamp":   now.isoformat(),
        "expires_at":  now + timedelta(days=TTL_DAYS),
    }
    try:
        await get_db()[COLLECTION].insert_one(doc)
    except Exception:
        pass  # ne jamais bloquer l'API pour un log raté


# ── Lecture ───────────────────────────────────────────────────────────────────

async def get_logs(
    ip: str | None       = None,
    username: str | None = None,
    auth_only: bool      = False,
    anon_only: bool      = False,
    date_from: str | None = None,
    date_to: str | None   = None,
    limit: int            = 200,
) -> list[dict]:
    col   = get_db()[COLLECTION]
    query: dict = {}

    if ip:       query["ip"]       = ip
    if username: query["username"] = username
    if auth_only:
        query["username"] = {"$ne": None}
    elif anon_only:
        query["username"] = None

    ts: dict = {}
    if date_from: ts["$gte"] = date_from
    if date_to:   ts["$lte"] = date_to
    if ts:        query["timestamp"] = ts

    cursor = col.find(query, {"_id": 0, "expires_at": 0}).sort("timestamp", -1).limit(limit)
    return await cursor.to_list(None)


async def get_stats() -> dict:
    col = get_db()[COLLECTION]

    total      = await col.count_documents({})
    auth_count = await col.count_documents({"username": {"$ne": None}})
    anon_count = total - auth_count

    # IPs uniques (les 10 000 derniers pour éviter full-scan sur très gros volumes)
    unique_ips = len(await col.distinct("ip"))

    # Top utilisateurs authentifiés
    top_users = await col.aggregate([
        {"$match":  {"username": {"$ne": None}}},
        {"$group":  {"_id": "$username", "count": {"$sum": 1}}},
        {"$sort":   {"count": -1}},
        {"$limit":  10},
    ]).to_list(None)

    # Top IPs
    top_ips = await col.aggregate([
        {"$group": {"_id": "$ip",       "count": {"$sum": 1}}},
        {"$sort":  {"count": -1}},
        {"$limit": 10},
    ]).to_list(None)

    # Activité par heure (dernières 24 h)
    since = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    hourly = await col.aggregate([
        {"$match": {"timestamp": {"$gte": since}}},
        {"$group": {
            "_id":   {"$substr": ["$timestamp", 0, 13]},  # "YYYY-MM-DDTHH"
            "count": {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]).to_list(None)

    return {
        "total":       total,
        "unique_ips":  unique_ips,
        "auth_count":  auth_count,
        "anon_count":  anon_count,
        "top_users":   [{"username": d["_id"], "count": d["count"]} for d in top_users],
        "top_ips":     [{"ip": d["_id"],       "count": d["count"]} for d in top_ips],
        "hourly_24h":  [{"hour": d["_id"],     "count": d["count"]} for d in hourly],
    }


async def clear_logs() -> int:
    r = await get_db()[COLLECTION].delete_many({})
    return r.deleted_count
