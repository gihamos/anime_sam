"""
Facturation côté client — paliers publics, souscription, retour PayPal, historique,
annulation/changement de palier, et le webhook PayPal (public, auto-vérifié).

GET  /billing/plans                          → paliers actifs (public)
GET  /billing/plans/{slug}                    → détail d'un palier (public)
POST /billing/webhooks/paypal                  → webhook PayPal (public, signature vérifiée)

POST /billing/subscribe                        → initier une souscription
POST /billing/subscribe/confirm                 → confirmer après retour PayPal
GET  /billing/me/subscription                   → mon abonnement courant
GET  /billing/me/payments                       → mon historique de facturation
POST /billing/me/subscription/cancel             → annuler (accès conservé jusqu'à la fin de période)
POST /billing/me/subscription/change-plan        → changer de palier
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request

from models.subscription import (
    SubscribeRequest, ChangePlanRequest, CancelRequest,
)
from models.responses import PlanPublic, SubscribeResponse, SubscriptionDetail
from models.payment import PaymentPublic
from api.dependencies import get_current_customer
from params import PAYPAL_RETURN_URL, PAYPAL_CANCEL_URL

import db.plans_repository as plans_repo
import db.subscriptions_repository as subscriptions_repo
import db.payments_repository as payments_repo
import db.webhook_events_repository as webhook_events_repo
from services.payments.registry import get_provider
from services.payments.base import WebhookSignatureError
from services.billing_service import handle_subscription_event
from utils.logger import logger

router = APIRouter(prefix="/billing", tags=["Facturation"])


def _plan_to_public(p: dict) -> dict:
    return {
        "id":                     p["id"],
        "slug":                   p["slug"],
        "name":                   p["name"],
        "description":            p.get("description", ""),
        "price":                  p["price"],
        "currency":               p.get("currency", "EUR"),
        "billing_period":         p.get("billing_period", "month"),
        "jellyfin_library_names": p.get("jellyfin_library_names", []),
        "max_devices":            p.get("max_devices", 1),
        "allow_downloads":        p.get("allow_downloads", False),
        "sort_order":             p.get("sort_order", 0),
    }


def _sub_to_detail(sub: dict, plan: dict | None, reveal_password: bool) -> dict:
    return {
        "id":                                 sub["id"],
        "plan_id":                             sub["plan_id"],
        "plan_name":                           plan.get("name") if plan else None,
        "status":                              sub["status"],
        "cancel_at_period_end":                sub.get("cancel_at_period_end", False),
        "current_period_end":                  sub.get("current_period_end"),
        "jellyfin_username":                   sub.get("jellyfin_username"),
        "jellyfin_initial_password_pending":   sub.get("jellyfin_initial_password_pending") if reveal_password else None,
        "created_at":                          sub.get("created_at"),
        "activated_at":                        sub.get("activated_at"),
    }


# ---------------------------------------------------------------------------
# Paliers publics
# ---------------------------------------------------------------------------

@router.get("/plans", response_model=list[PlanPublic], summary="Paliers d'abonnement disponibles")
async def list_plans():
    plans = await plans_repo.list_all(include_inactive=False)
    return [_plan_to_public(p) for p in plans]


@router.get("/plans/{slug}", response_model=PlanPublic, summary="Détail d'un palier")
async def get_plan(slug: str):
    plan = await plans_repo.find_by_slug(slug)
    if not plan or not plan.get("is_active", True):
        raise HTTPException(404, f"Palier '{slug}' introuvable")
    return _plan_to_public(plan)


# ---------------------------------------------------------------------------
# Souscription
# ---------------------------------------------------------------------------

@router.post("/subscribe", response_model=SubscribeResponse, summary="Initier une souscription")
async def subscribe(body: SubscribeRequest, customer: dict = Depends(get_current_customer)):
    if await subscriptions_repo.find_current_for_user(customer["username"]):
        raise HTTPException(409, "Un abonnement est déjà en cours pour ce compte")

    plan = await plans_repo.find_by_id(body.plan_id)
    if not plan or not plan.get("is_active", True):
        raise HTTPException(404, "Palier introuvable")

    provider_plan_id = plan.get("provider_refs", {}).get("paypal", {}).get("plan_id")
    if not provider_plan_id:
        raise HTTPException(400, "Ce palier n'est pas encore configuré côté paiement")

    sub_id = await subscriptions_repo.create({
        "username":                 customer["username"],
        "plan_id":                  plan["id"],
        "provider":                 "paypal",
        "provider_subscription_id": None,
        "status":                   "pending",
        "cancel_at_period_end":     False,
        "current_period_end":       None,
        "jellyfin_user_id":         None,
        "jellyfin_username":        None,
    })

    provider = get_provider("paypal")
    checkout = await provider.create_subscription_checkout(
        provider_plan_id=provider_plan_id,
        # PayPal ajoute lui-même ?subscription_id=I-XXX&... à la redirection de retour.
        return_url=PAYPAL_RETURN_URL,
        cancel_url=PAYPAL_CANCEL_URL,
        custom_id=sub_id,
    )
    await subscriptions_repo.update(sub_id, {"provider_subscription_id": checkout.provider_subscription_id})

    return {"subscription_id": sub_id, "approval_url": checkout.approval_url}


@router.post("/subscribe/confirm", response_model=SubscriptionDetail, summary="Confirmer après retour PayPal")
async def confirm_subscription(subscription_id: str, customer: dict = Depends(get_current_customer)):
    sub = await subscriptions_repo.find_by_provider_subscription_id("paypal", subscription_id)
    if not sub or sub["username"] != customer["username"]:
        raise HTTPException(404, "Abonnement introuvable")

    provider = get_provider("paypal")
    status_data = await provider.get_subscription_status(subscription_id)

    if status_data.get("status") == "ACTIVE" and sub["status"] != "active":
        from services.payments.events import NormalizedSubscriptionEvent, SubscriptionEventType
        from datetime import datetime, timezone
        billing_info = status_data.get("billing_info", {}) or {}
        next_billing = billing_info.get("next_billing_time")
        period_end = datetime.fromisoformat(next_billing.replace("Z", "+00:00")) if next_billing else None
        await handle_subscription_event(NormalizedSubscriptionEvent(
            provider="paypal", event_id=f"sync-confirm-{subscription_id}",
            event_type=SubscriptionEventType.ACTIVATED,
            provider_subscription_id=subscription_id,
            occurred_at=datetime.now(timezone.utc),
            current_period_end=period_end,
        ))
        sub = await subscriptions_repo.find_by_id(sub["id"])

    plan = await plans_repo.find_by_id(sub["plan_id"])
    detail = _sub_to_detail(sub, plan, reveal_password=True)
    if sub.get("jellyfin_initial_password_pending"):
        await subscriptions_repo.update(sub["id"], {"jellyfin_initial_password_pending": None})
    return detail


# ---------------------------------------------------------------------------
# Mon abonnement
# ---------------------------------------------------------------------------

@router.get("/me/subscription", response_model=Optional[SubscriptionDetail], summary="Mon abonnement courant")
async def my_subscription(customer: dict = Depends(get_current_customer)):
    sub = await subscriptions_repo.find_current_for_user(customer["username"])
    if not sub:
        return None
    plan = await plans_repo.find_by_id(sub["plan_id"])
    detail = _sub_to_detail(sub, plan, reveal_password=True)
    if sub.get("jellyfin_initial_password_pending"):
        await subscriptions_repo.update(sub["id"], {"jellyfin_initial_password_pending": None})
    return detail


@router.get("/me/payments", response_model=list[PaymentPublic], summary="Mon historique de facturation")
async def my_payments(customer: dict = Depends(get_current_customer)):
    payments = await payments_repo.list_for_user(customer["username"])
    return payments


@router.post("/me/subscription/cancel", summary="Annuler mon abonnement")
async def cancel_my_subscription(body: CancelRequest, customer: dict = Depends(get_current_customer)):
    sub = await subscriptions_repo.find_current_for_user(customer["username"])
    if not sub:
        raise HTTPException(404, "Aucun abonnement en cours")

    provider = get_provider(sub["provider"])
    if sub.get("provider_subscription_id"):
        await provider.cancel_subscription(sub["provider_subscription_id"], body.reason or "")

    await subscriptions_repo.update(sub["id"], {
        "status": "cancelled", "cancel_at_period_end": True,
    })
    return {"message": "Abonnement annulé — l'accès reste actif jusqu'à la fin de la période déjà payée"}


@router.post("/me/subscription/change-plan", summary="Changer de palier")
async def change_my_plan(body: ChangePlanRequest, customer: dict = Depends(get_current_customer)):
    sub = await subscriptions_repo.find_current_for_user(customer["username"])
    if not sub or sub["status"] != "active":
        raise HTTPException(409, "Aucun abonnement actif à modifier")

    new_plan = await plans_repo.find_by_id(body.new_plan_id)
    if not new_plan or not new_plan.get("is_active", True):
        raise HTTPException(404, "Nouveau palier introuvable")

    new_provider_plan_id = new_plan.get("provider_refs", {}).get("paypal", {}).get("plan_id")
    if not new_provider_plan_id:
        raise HTTPException(400, "Ce palier n'est pas encore configuré côté paiement")

    provider = get_provider(sub["provider"])
    await provider.change_plan(sub["provider_subscription_id"], new_provider_plan_id)
    await subscriptions_repo.update(sub["id"], {"plan_id": new_plan["id"]})

    if sub.get("jellyfin_user_id"):
        import services.jellyfin_provisioning as jellyfin
        await jellyfin.enable_user(
            sub["jellyfin_user_id"],
            new_plan.get("jellyfin_library_folder_ids", []),
            new_plan.get("max_devices", 1),
            new_plan.get("allow_downloads", False),
        )
    return {"message": "Palier mis à jour"}


# ---------------------------------------------------------------------------
# Webhook PayPal (public, auto-vérifié)
# ---------------------------------------------------------------------------

@router.post("/webhooks/paypal", summary="Webhook PayPal (public — signature vérifiée en interne)")
async def paypal_webhook(request: Request):
    raw_body = await request.body()
    provider = get_provider("paypal")

    try:
        event = await provider.parse_webhook_event(dict(request.headers), raw_body)
    except WebhookSignatureError as e:
        raise HTTPException(400, str(e))

    if event is None:
        return {"status": "ignored"}

    is_new = await webhook_events_repo.try_record(
        event.provider, event.event_id, event.event_type.value, event.raw or {},
    )
    if not is_new:
        return {"status": "already_processed"}

    try:
        await handle_subscription_event(event)
    except Exception as exc:
        logger.error(f"billing webhook : échec de traitement — {exc}")
        raise HTTPException(500, "Échec du traitement de l'événement")

    return {"status": "processed"}
