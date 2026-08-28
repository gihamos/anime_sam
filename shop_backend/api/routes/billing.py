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

from datetime import datetime, timedelta, timezone
from typing import Optional

import httpx
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
import db.promotions_repository as promotions_repo
import db.webhook_events_repository as webhook_events_repo
from services.payments.registry import get_provider
from services.payments.base import WebhookSignatureError
from services.payments.events import NormalizedSubscriptionEvent, SubscriptionEventType
from services.billing_service import handle_subscription_event
from services.plan_pricing import apply_discount, discounted_price_or_none, effective_price
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
        "duration_days":          p.get("duration_days", 30),
        "jellyfin_library_names": p.get("jellyfin_library_names", []),
        "max_devices":            p.get("max_devices", 1),
        "allow_downloads":        p.get("allow_downloads", False),
        "sort_order":             p.get("sort_order", 0),
        "discount_type":          p.get("discount_type"),
        "discount_value":         p.get("discount_value"),
        "discount_expires_at":    p.get("discount_expires_at"),
        "discounted_price":       discounted_price_or_none(p),
        "max_parental_rating":    p.get("max_parental_rating"),
    }


def _sub_to_detail(sub: dict, plan: dict | None, reveal_password: bool) -> dict:
    return {
        "id":                                 sub["id"],
        "plan_id":                             sub["plan_id"],
        "plan_name":                           plan.get("name") if plan else None,
        "status":                              sub["status"],
        "auto_renew":                          sub.get("auto_renew", True),
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

_STALE_PENDING_AFTER = timedelta(hours=1)


async def _clear_stale_pending(username: str) -> dict | None:
    """Si le client a une tentative 'pending' abandonnée (paiement PayPal jamais finalisé —
    approbation annulée, onglet fermé, carte refusée...), elle traîne indéfiniment en base
    et bloque toute nouvelle tentative via le 409 ci-dessous (constaté en conditions
    réelles). Passé un délai raisonnable, on la considère abandonnée et on l'efface
    automatiquement plutôt que de figer le client. Retourne l'abonnement en cours restant
    (toujours actif/légitime), ou None."""
    existing = await subscriptions_repo.find_current_for_user(username)
    if not existing:
        return None
    if existing["status"] != "pending":
        return existing
    created_at = existing.get("created_at")
    if created_at:
        try:
            age = datetime.now(timezone.utc) - datetime.fromisoformat(created_at)
            if age > _STALE_PENDING_AFTER:
                await subscriptions_repo.delete(existing["id"])
                return None
        except ValueError:
            pass
    return existing


async def _validate_promo(code: str, plan: dict) -> dict:
    """Vérifie qu'un code promo est utilisable pour ce palier — lève 400 sinon."""
    promo = await promotions_repo.find_by_code(code)
    if not promo or not promo.get("is_active", True):
        raise HTTPException(400, "Code promo invalide")
    if promo.get("expires_at") and promo["expires_at"] < datetime.now(timezone.utc).isoformat():
        raise HTTPException(400, "Ce code promo a expiré")
    if promo.get("max_uses") is not None and promo.get("used_count", 0) >= promo["max_uses"]:
        raise HTTPException(400, "Ce code promo a atteint son nombre maximal d'utilisations")
    applicable = promo.get("applicable_plan_ids") or []
    if applicable and plan["id"] not in applicable:
        raise HTTPException(400, "Ce code promo ne s'applique pas à ce palier")
    return promo


@router.get("/promo/{code}", summary="Aperçu d'un code promo pour un palier donné")
async def preview_promo(code: str, plan_id: str, customer: dict = Depends(get_current_customer)):
    plan = await plans_repo.find_by_id(plan_id)
    if not plan:
        raise HTTPException(404, "Palier introuvable")
    promo = await _validate_promo(code, plan)
    # Le code promo s'applique sur le prix déjà réduit si le palier a lui-même une
    # réduction active — les deux remises se cumulent.
    base_price = effective_price(plan)
    discounted = apply_discount(base_price, promo["discount_type"], promo["discount_value"])
    return {
        "code":             promo["code"],
        "original_price":   plan["price"],
        "discounted_price": discounted,
        "currency":         plan.get("currency", "EUR"),
    }


@router.post("/subscribe", response_model=SubscribeResponse, summary="Initier une souscription")
async def subscribe(body: SubscribeRequest, customer: dict = Depends(get_current_customer)):
    if await _clear_stale_pending(customer["username"]):
        raise HTTPException(409, "Un abonnement est déjà en cours pour ce compte")

    plan = await plans_repo.find_by_id(body.plan_id)
    if not plan or not plan.get("is_active", True):
        raise HTTPException(404, "Palier introuvable")

    provider_plan_id = plan.get("provider_refs", {}).get("paypal", {}).get("plan_id")
    if body.auto_renew and not provider_plan_id:
        raise HTTPException(400, "Ce palier n'est pas encore configuré côté paiement")

    # Réduction automatique du palier (si active) puis code promo éventuel par-dessus —
    # les deux se cumulent.
    price = effective_price(plan)
    promo = None
    if body.promo_code:
        promo = await _validate_promo(body.promo_code, plan)
        price = apply_discount(price, promo["discount_type"], promo["discount_value"])

    sub_id = await subscriptions_repo.create({
        "username":                 customer["username"],
        "plan_id":                  plan["id"],
        "provider":                 "paypal",
        "provider_subscription_id": None,
        "status":                   "pending",
        "auto_renew":               body.auto_renew,
        "promotion_code":            promo["code"] if promo else None,
        # Un paiement unique n'a rien à annuler plus tard — il expire naturellement à la
        # fin de sa période via le job planifié, comme un abonnement déjà annulé.
        "cancel_at_period_end":     not body.auto_renew,
        "current_period_end":       None,
        "jellyfin_user_id":         None,
        "jellyfin_username":        None,
    })

    provider = get_provider("paypal")
    try:
        if body.auto_renew:
            effective_plan_id = provider_plan_id
            if price != plan["price"]:
                # Un abonnement récurrent facture le prix encodé dans le plan PayPal — pas
                # de remise ponctuelle possible dessus, il faut un plan dédié au tarif remisé
                # (réduction du palier et/ou code promo — même mécanisme que le changement
                # de prix normal d'un palier). Ce tarif reste celui facturé pour toute la
                # durée de vie de cet abonnement récurrent, même après l'expiration de la
                # réduction — simplification déjà actée pour les codes promo, reprise ici.
                product_id = plan.get("provider_refs", {}).get("paypal", {}).get("product_id")
                suffix = promo["code"] if promo else "promo"
                effective_plan_id = await provider.create_billing_plan(
                    product_id=product_id,
                    plan_name=f"{plan['name']} ({suffix})",
                    description=f"{plan.get('description') or plan['name']} — tarif réduit",
                    price=price,
                    currency=plan.get("currency", "EUR"),
                    duration_days=plan.get("duration_days", 30),
                )
            checkout = await provider.create_subscription_checkout(
                provider_plan_id=effective_plan_id,
                # PayPal ajoute lui-même ?subscription_id=I-XXX&... à la redirection de retour.
                return_url=PAYPAL_RETURN_URL,
                cancel_url=PAYPAL_CANCEL_URL,
                custom_id=sub_id,
            )
        else:
            checkout = await provider.create_one_time_checkout(
                price=price,
                currency=plan.get("currency", "EUR"),
                return_url=PAYPAL_RETURN_URL,
                cancel_url=PAYPAL_CANCEL_URL,
                custom_id=sub_id,
            )
    except Exception as exc:
        # Rollback : sans ça, ce brouillon "pending" sans provider_subscription_id bloque
        # indéfiniment toute nouvelle tentative via le 409 ci-dessus (constaté en conditions
        # réelles avec un mauvais paramètre PayPal — le client ne pouvait plus jamais
        # réessayer de s'abonner tant que ce document traînait en base).
        await subscriptions_repo.delete(sub_id)
        logger.error(f"billing.subscribe : échec de création côté PayPal — {exc}")
        raise HTTPException(502, "Échec de l'initialisation du paiement — réessayez dans un instant")

    await subscriptions_repo.update(sub_id, {"provider_subscription_id": checkout.provider_subscription_id})

    return {"subscription_id": sub_id, "approval_url": checkout.approval_url}


@router.post("/subscribe/confirm", response_model=SubscriptionDetail, summary="Confirmer après retour PayPal")
async def confirm_subscription(subscription_id: str, customer: dict = Depends(get_current_customer)):
    sub = await subscriptions_repo.find_by_provider_subscription_id("paypal", subscription_id)
    if not sub or sub["username"] != customer["username"]:
        raise HTTPException(404, "Abonnement introuvable")

    provider = get_provider("paypal")

    if sub.get("auto_renew", True):
        if sub["status"] != "active":
            status_data = await provider.get_subscription_status(subscription_id)
            if status_data.get("status") == "ACTIVE":
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
    else:
        # Paiement unique — le buyer doit avoir approuvé côté PayPal avant que la capture
        # puisse réussir ; ORDER_NOT_APPROVED (422) sinon (ex. retour prématuré/rechargement
        # de page) — on redemande alors une approbation plutôt que de planter.
        if sub["status"] != "active":
            try:
                capture = await provider.capture_one_time_payment(subscription_id)
            except httpx.HTTPStatusError:
                raise HTTPException(409, "Paiement non finalisé côté PayPal — veuillez réessayer l'approbation")

            if capture["status"] == "COMPLETED":
                plan = await plans_repo.find_by_id(sub["plan_id"])
                duration = (plan or {}).get("duration_days", 30)
                period_end = datetime.now(timezone.utc) + timedelta(days=duration)

                await handle_subscription_event(NormalizedSubscriptionEvent(
                    provider="paypal", event_id=f"onetime-activate-{sub['id']}",
                    event_type=SubscriptionEventType.ACTIVATED,
                    provider_subscription_id=subscription_id,
                    occurred_at=datetime.now(timezone.utc),
                    current_period_end=period_end,
                ))

                existing_payment = await payments_repo.find_by_provider_payment_id(capture["payment_id"])
                if not existing_payment:
                    await payments_repo.create({
                        "username":              sub["username"],
                        "subscription_id":       sub["id"],
                        "plan_id":                sub["plan_id"],
                        "amount":                 capture["amount"],
                        "currency":               capture["currency"],
                        "provider":               "paypal",
                        "provider_payment_id":    capture["payment_id"],
                        "provider_event_id":      f"onetime-{capture['payment_id']}",
                        "status":                 "completed",
                        "paid_at":                datetime.now(timezone.utc).isoformat(),
                    })

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

    if sub["status"] == "pending":
        # Rien n'a encore été facturé côté PayPal (paiement jamais finalisé) — pas
        # d'annulation fournisseur à faire, on efface juste la tentative pour libérer le
        # compte et permettre de réessayer immédiatement.
        await subscriptions_repo.delete(sub["id"])
        return {"message": "Tentative d'abonnement annulée — vous pouvez réessayer"}

    if sub["provider"] != "manual" and sub.get("provider_subscription_id"):
        provider = get_provider(sub["provider"])
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

    if sub["provider"] != "manual":
        new_provider_plan_id = new_plan.get("provider_refs", {}).get("paypal", {}).get("plan_id")
        if not new_provider_plan_id:
            raise HTTPException(400, "Ce palier n'est pas encore configuré côté paiement")
        provider = get_provider(sub["provider"])
        await provider.change_plan(sub["provider_subscription_id"], new_provider_plan_id)

    await subscriptions_repo.update(sub["id"], {"plan_id": new_plan["id"]})

    if sub.get("jellyfin_user_id"):
        import services.jellyfin_provisioning as jellyfin
        from services.parental_rating import effective_max_rating
        await jellyfin.enable_user(
            sub["jellyfin_user_id"],
            new_plan.get("jellyfin_library_folder_ids", []),
            new_plan.get("max_devices", 1),
            new_plan.get("allow_downloads", False),
            max_parental_rating=effective_max_rating(customer.get("date_of_birth"), new_plan.get("max_parental_rating")),
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
