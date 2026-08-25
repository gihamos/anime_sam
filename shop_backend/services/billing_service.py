"""
Orchestrateur du cycle de vie des abonnements — point d'entrée unique consommé par le
webhook PayPal (api/routes/billing.py) et par la confirmation synchrone post-redirection.
Ne connaît que NormalizedSubscriptionEvent (services/payments/events.py), jamais de code
spécifique à un fournisseur de paiement.

Idempotent par construction : réactiver un compte Jellyfin déjà actif ou désactiver un
compte déjà désactivé sont des opérations sans effet de bord supplémentaire — combiné à
`webhook_events` (idempotence au niveau événement), c'est ce qui rend le traitement sûr en
cas de redélivraison PayPal.
"""

from __future__ import annotations

from datetime import datetime, timezone

import db.subscriptions_repository as subscriptions_repo
import db.plans_repository as plans_repo
import db.payments_repository as payments_repo
import services.jellyfin_provisioning as jellyfin
from services.payments.events import NormalizedSubscriptionEvent, SubscriptionEventType
from utils.logger import logger


async def handle_subscription_event(event: NormalizedSubscriptionEvent) -> None:
    sub = await subscriptions_repo.find_by_provider_subscription_id(
        event.provider, event.provider_subscription_id,
    )
    if not sub:
        logger.warning(
            f"billing_service : événement {event.event_type} pour un abonnement "
            f"inconnu ({event.provider}/{event.provider_subscription_id}) — ignoré"
        )
        return

    plan = await plans_repo.find_by_id(sub["plan_id"])
    if not plan:
        logger.warning(f"billing_service : palier {sub['plan_id']} introuvable pour l'abonnement {sub['id']}")
        return

    period_end_iso = event.current_period_end.isoformat() if event.current_period_end else sub.get("current_period_end")

    if event.event_type == SubscriptionEventType.ACTIVATED:
        await _activate(sub, plan, period_end_iso)

    elif event.event_type == SubscriptionEventType.RENEWED:
        await _renew(sub, plan, event, period_end_iso)

    elif event.event_type == SubscriptionEventType.PAYMENT_FAILED:
        # Période de grâce — aucune action Jellyfin, PayPal relance seul.
        await subscriptions_repo.update(sub["id"], {"status": "past_due"})

    elif event.event_type in (SubscriptionEventType.SUSPENDED, SubscriptionEventType.EXPIRED):
        if sub.get("jellyfin_user_id"):
            await jellyfin.disable_user(sub["jellyfin_user_id"])
        await subscriptions_repo.update(sub["id"], {
            "status": event.event_type.value,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        })

    elif event.event_type == SubscriptionEventType.CANCELLED:
        # Décision produit actée : accès conservé jusqu'à la fin de la période déjà payée
        # (cf. disable_expired_cancellations, job planifié plus bas) — pas de coupure ici.
        await subscriptions_repo.update(sub["id"], {
            "status": "cancelled",
            "cancel_at_period_end": True,
            "cancelled_at": datetime.now(timezone.utc).isoformat(),
        })


async def _activate(sub: dict, plan: dict, period_end_iso: str | None) -> None:
    jellyfin_user_id = sub.get("jellyfin_user_id")
    fields: dict = {"status": "active", "activated_at": datetime.now(timezone.utc).isoformat()}
    if period_end_iso:
        fields["current_period_end"] = period_end_iso

    if not jellyfin_user_id:
        created = await jellyfin.create_user(sub["username"])
        if not created:
            logger.warning(f"billing_service : échec provisioning Jellyfin pour l'abonnement {sub['id']}")
            return
        jellyfin_user_id, password = created
        fields["jellyfin_user_id"] = jellyfin_user_id
        fields["jellyfin_username"] = sub["username"]
        fields["jellyfin_initial_password_pending"] = password

    await jellyfin.enable_user(
        jellyfin_user_id,
        plan.get("jellyfin_library_folder_ids", []),
        plan.get("max_devices", 1),
        plan.get("allow_downloads", False),
    )
    await subscriptions_repo.update(sub["id"], fields)
    logger.info(f"billing_service : abonnement {sub['id']} activé pour '{sub['username']}'")


async def _renew(sub: dict, plan: dict, event: NormalizedSubscriptionEvent, period_end_iso: str | None) -> None:
    if event.provider_payment_id:
        existing = await payments_repo.find_by_provider_payment_id(event.provider_payment_id)
        if not existing:
            await payments_repo.create({
                "username":              sub["username"],
                "subscription_id":       sub["id"],
                "plan_id":                sub["plan_id"],
                "amount":                 event.amount or plan.get("price", 0),
                "currency":               event.currency or plan.get("currency", "EUR"),
                "provider":               event.provider,
                "provider_payment_id":    event.provider_payment_id,
                "provider_event_id":      event.event_id,
                "status":                 "completed",
                "paid_at":                event.occurred_at.isoformat(),
            })

    fields: dict = {}
    if period_end_iso:
        fields["current_period_end"] = period_end_iso

    if sub.get("status") in ("past_due", "suspended") and sub.get("jellyfin_user_id"):
        await jellyfin.enable_user(
            sub["jellyfin_user_id"],
            plan.get("jellyfin_library_folder_ids", []),
            plan.get("max_devices", 1),
            plan.get("allow_downloads", False),
        )
        fields["status"] = "active"

    if fields:
        await subscriptions_repo.update(sub["id"], fields)


async def disable_expired_cancellations() -> int:
    """Job planifié quotidien — désactive les comptes Jellyfin des abonnements annulés dont
    la période déjà payée est désormais terminée (cf. décision produit : pas de coupure
    immédiate à l'annulation). Retourne le nombre de comptes désactivés."""
    now_iso = datetime.now(timezone.utc).isoformat()
    expired = await subscriptions_repo.list_expiring_cancellations(now_iso)

    count = 0
    for sub in expired:
        if sub.get("jellyfin_user_id"):
            await jellyfin.disable_user(sub["jellyfin_user_id"])
        await subscriptions_repo.update(sub["id"], {"status": "expired"})
        count += 1

    if count:
        logger.info(f"billing_service : {count} abonnement(s) désactivé(s) en fin de période (job planifié)")
    return count
