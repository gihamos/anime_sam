"""
Statistiques de vente/utilisation pour le tableau de bord admin — agrégations en lecture
seule sur customers/subscriptions/payments, aucune écriture.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.connection import get_db


async def get_dashboard_stats() -> dict:
    db = get_db()
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0).isoformat()
    thirty_days_ago = (now - timedelta(days=30)).isoformat()

    total_customers = await db.customers.count_documents({"role": "customer"})
    new_customers_this_month = await db.customers.count_documents({
        "role": "customer", "created_at": {"$gte": month_start},
    })

    active_subscriptions = await db.subscriptions.count_documents({"status": "active"})

    subs_by_status: dict[str, int] = {}
    async for doc in db.subscriptions.aggregate([
        {"$group": {"_id": "$status", "count": {"$sum": 1}}},
    ]):
        subs_by_status[doc["_id"]] = doc["count"]

    async def _sum_revenue(match: dict) -> float:
        result = await db.payments.aggregate([
            {"$match": match},
            {"$group": {"_id": None, "total": {"$sum": "$amount"}}},
        ]).to_list(1)
        return round(result[0]["total"], 2) if result else 0.0

    total_revenue = await _sum_revenue({"status": "completed"})
    month_revenue = await _sum_revenue({"status": "completed", "paid_at": {"$gte": month_start}})

    daily: dict[str, dict] = {}
    async for doc in db.payments.aggregate([
        {"$match": {"status": "completed", "paid_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {"$substrBytes": ["$paid_at", 0, 10]},
            "amount": {"$sum": "$amount"},
            "count":  {"$sum": 1},
        }},
        {"$sort": {"_id": 1}},
    ]):
        daily[doc["_id"]] = {"amount": round(doc["amount"], 2), "count": doc["count"]}

    # Complète les jours sans paiement à 0 — un graphique en ligne avec des trous entre
    # points non consécutifs induit en erreur sur la pente.
    daily_revenue = []
    for i in range(30, -1, -1):
        day = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        entry = daily.get(day, {"amount": 0, "count": 0})
        daily_revenue.append({"date": day, **entry})

    plan_counts: dict[str, int] = {}
    async for doc in db.subscriptions.aggregate([
        {"$match": {"status": {"$in": ["active", "past_due", "suspended"]}}},
        {"$group": {"_id": "$plan_id", "count": {"$sum": 1}}},
        {"$sort": {"count": -1}},
    ]):
        plan_counts[doc["_id"]] = doc["count"]

    plans_by_id = {}
    async for p in db.plans.find({}, {"name": 1}):
        plans_by_id[str(p["_id"])] = p.get("name", "?")
    plan_popularity = [
        {"plan_id": pid, "plan_name": plans_by_id.get(pid, "Palier supprimé"), "count": count}
        for pid, count in plan_counts.items()
    ]

    return {
        "total_customers":           total_customers,
        "new_customers_this_month":  new_customers_this_month,
        "active_subscriptions":      active_subscriptions,
        "subscriptions_by_status":   subs_by_status,
        "total_revenue":             total_revenue,
        "month_revenue":             month_revenue,
        "daily_revenue":             daily_revenue,
        "plan_popularity":           plan_popularity,
    }
