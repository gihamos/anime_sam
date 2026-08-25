"""
Administration de la boutique (paliers, abonnements, tickets) — réservé au rôle admin de
shop_backend (compte totalement distinct de l'admin anime_sam).

GET/POST/PUT/DELETE /admin/api/plans[/{id}]
GET    /admin/api/jellyfin/library-folders
GET    /admin/api/subscriptions
GET    /admin/api/subscriptions/{id}
POST   /admin/api/subscriptions/{id}/extend
POST   /admin/api/subscriptions/{id}/cancel
GET    /admin/api/tickets
GET    /admin/api/tickets/{id}
POST   /admin/api/tickets/{id}/messages
PUT    /admin/api/tickets/{id}/status
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.plan import PlanCreate, PlanUpdate
from models.subscription import SubscriptionExtendRequest, SubscriptionAdminCancelRequest
from models.ticket import TicketMessageCreate, TicketStatusUpdate
from models.responses import TicketPublic
from api.dependencies import require_admin

import db.plans_repository as plans_repo
import db.subscriptions_repository as subscriptions_repo
import db.payments_repository as payments_repo
import db.tickets_repository as tickets_repo
import services.jellyfin_provisioning as jellyfin
from services.payments.registry import get_provider

router = APIRouter(prefix="/admin/api", tags=["Administration"])


# ---------------------------------------------------------------------------
# Paliers
# ---------------------------------------------------------------------------

_PRODUCT_NAME = "Anime Sama — Accès serveur Jellyfin"


@router.get("/plans", summary="Liste des paliers (admin, inclut les inactifs)")
async def list_plans_admin(_: dict = Depends(require_admin)):
    return await plans_repo.list_all(include_inactive=True)


@router.post("/plans", status_code=201, summary="Créer un palier")
async def create_plan(body: PlanCreate, _: dict = Depends(require_admin)):
    if await plans_repo.find_by_slug(body.slug):
        raise HTTPException(409, f"Le palier '{body.slug}' existe déjà")

    provider = get_provider("paypal")
    provider_refs: dict = {}
    try:
        product_id = await provider.ensure_product(_PRODUCT_NAME, "Abonnements d'accès au serveur Jellyfin")
        plan_id_paypal = await provider.create_billing_plan(
            product_id=product_id, plan_name=body.name, description=body.description,
            price=body.price, currency=body.currency, billing_period=body.billing_period,
        )
        provider_refs["paypal"] = {"product_id": product_id, "plan_id": plan_id_paypal}
    except Exception as exc:
        raise HTTPException(502, f"Échec de la création du plan PayPal : {exc}")

    doc = body.model_dump()
    doc["provider_refs"] = provider_refs
    pid = await plans_repo.create(doc)
    return await plans_repo.find_by_id(pid)


@router.get("/plans/{plan_id}", summary="Détail d'un palier")
async def get_plan_admin(plan_id: str, _: dict = Depends(require_admin)):
    plan = await plans_repo.find_by_id(plan_id)
    if not plan:
        raise HTTPException(404, "Palier introuvable")
    return plan


@router.put("/plans/{plan_id}", summary="Modifier un palier")
async def update_plan(plan_id: str, body: PlanUpdate, _: dict = Depends(require_admin)):
    existing = await plans_repo.find_by_id(plan_id)
    if not existing:
        raise HTTPException(404, "Palier introuvable")

    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    warning = None

    if "price" in fields and fields["price"] != existing.get("price"):
        provider = get_provider("paypal")
        product_id = existing.get("provider_refs", {}).get("paypal", {}).get("product_id")
        if product_id:
            try:
                new_paypal_plan_id = await provider.create_billing_plan(
                    product_id=product_id,
                    plan_name=fields.get("name", existing["name"]),
                    description=fields.get("description", existing.get("description", "")),
                    price=fields["price"],
                    currency=fields.get("currency", existing.get("currency", "EUR")),
                    billing_period=existing.get("billing_period", "month"),
                )
                provider_refs = dict(existing.get("provider_refs", {}))
                provider_refs["paypal"] = {"product_id": product_id, "plan_id": new_paypal_plan_id}
                fields["provider_refs"] = provider_refs
                warning = (
                    "Un nouveau plan PayPal a été créé pour ce prix — les abonnés déjà "
                    "engagés restent facturés sur l'ancien tarif jusqu'à leur prochaine "
                    "souscription."
                )
            except Exception as exc:
                raise HTTPException(502, f"Échec de la mise à jour PayPal : {exc}")

    if fields:
        await plans_repo.update(plan_id, fields)

    updated = await plans_repo.find_by_id(plan_id)
    return {"plan": updated, "warning": warning}


@router.delete("/plans/{plan_id}", status_code=204, summary="Supprimer un palier")
async def delete_plan(plan_id: str, _: dict = Depends(require_admin)):
    if not await plans_repo.find_by_id(plan_id):
        raise HTTPException(404, "Palier introuvable")
    if await subscriptions_repo.count_by_plan(plan_id) > 0:
        raise HTTPException(409, "Des abonnements actifs référencent encore ce palier")
    await plans_repo.delete(plan_id)


@router.get("/jellyfin/library-folders", summary="Bibliothèques Jellyfin disponibles")
async def jellyfin_library_folders(_: dict = Depends(require_admin)):
    return await jellyfin.list_library_folders()


# ---------------------------------------------------------------------------
# Abonnements
# ---------------------------------------------------------------------------

@router.get("/subscriptions", summary="Liste des abonnements (filtres)")
async def list_subscriptions(
    status:  Optional[str] = None,
    plan_id: Optional[str] = None,
    search:  Optional[str] = None,
    _: dict = Depends(require_admin),
):
    return await subscriptions_repo.list_all(status=status, plan_id=plan_id, search=search)


@router.get("/subscriptions/{subscription_id}", summary="Détail d'un abonnement + historique de paiement")
async def get_subscription(subscription_id: str, _: dict = Depends(require_admin)):
    sub = await subscriptions_repo.find_by_id(subscription_id)
    if not sub:
        raise HTTPException(404, "Abonnement introuvable")
    payments = await payments_repo.list_for_subscription(subscription_id)
    return {"subscription": sub, "payments": payments}


@router.post("/subscriptions/{subscription_id}/extend", summary="Prolonger un abonnement (geste commercial local)")
async def extend_subscription(subscription_id: str, body: SubscriptionExtendRequest, _: dict = Depends(require_admin)):
    sub = await subscriptions_repo.find_by_id(subscription_id)
    if not sub:
        raise HTTPException(404, "Abonnement introuvable")

    base = datetime.now(timezone.utc)
    if sub.get("current_period_end"):
        try:
            existing_end = datetime.fromisoformat(sub["current_period_end"])
            if existing_end > base:
                base = existing_end
        except ValueError:
            pass
    new_end = base + timedelta(days=body.days)

    await subscriptions_repo.update(subscription_id, {"current_period_end": new_end.isoformat()})
    return await subscriptions_repo.find_by_id(subscription_id)


@router.post("/subscriptions/{subscription_id}/cancel", summary="Annulation forcée (désactivation immédiate)")
async def force_cancel_subscription(subscription_id: str, body: SubscriptionAdminCancelRequest, _: dict = Depends(require_admin)):
    sub = await subscriptions_repo.find_by_id(subscription_id)
    if not sub:
        raise HTTPException(404, "Abonnement introuvable")

    provider = get_provider(sub["provider"])
    if sub.get("provider_subscription_id"):
        try:
            await provider.cancel_subscription(sub["provider_subscription_id"], body.reason or "Annulation admin")
        except Exception:
            pass  # déjà annulé côté fournisseur — on force quand même l'état local

    if sub.get("jellyfin_user_id"):
        await jellyfin.disable_user(sub["jellyfin_user_id"])

    await subscriptions_repo.update(subscription_id, {
        "status": "cancelled", "cancel_at_period_end": False,
        "cancelled_at": datetime.now(timezone.utc).isoformat(),
    })
    return await subscriptions_repo.find_by_id(subscription_id)


# ---------------------------------------------------------------------------
# Tickets
# ---------------------------------------------------------------------------

@router.get("/tickets", response_model=list[TicketPublic], summary="Boîte de réception des tickets")
async def list_tickets_admin(status: Optional[str] = None, _: dict = Depends(require_admin)):
    return await tickets_repo.list_all(status=status)


@router.get("/tickets/{ticket_id}", response_model=TicketPublic, summary="Détail d'un ticket")
async def get_ticket_admin(ticket_id: str, _: dict = Depends(require_admin)):
    ticket = await tickets_repo.find_by_id(ticket_id)
    if not ticket:
        raise HTTPException(404, "Ticket introuvable")
    return ticket


@router.post("/tickets/{ticket_id}/messages", response_model=TicketPublic, summary="Répondre à un ticket")
async def reply_to_ticket_admin(ticket_id: str, body: TicketMessageCreate, admin: dict = Depends(require_admin)):
    if not await tickets_repo.find_by_id(ticket_id):
        raise HTTPException(404, "Ticket introuvable")
    await tickets_repo.add_message(ticket_id, "admin", admin["username"], body.body)
    return await tickets_repo.find_by_id(ticket_id)


@router.put("/tickets/{ticket_id}/status", response_model=TicketPublic, summary="Changer le statut d'un ticket")
async def update_ticket_status(ticket_id: str, body: TicketStatusUpdate, _: dict = Depends(require_admin)):
    if not await tickets_repo.find_by_id(ticket_id):
        raise HTTPException(404, "Ticket introuvable")
    await tickets_repo.set_status(ticket_id, body.status.value)
    return await tickets_repo.find_by_id(ticket_id)
