"""
Administration de la boutique (paliers, abonnements, tickets, clients) — réservé au rôle
admin de shop_backend (compte totalement distinct de l'admin anime_sam).

GET/POST/PUT/DELETE /admin/api/plans[/{id}]
GET    /admin/api/jellyfin/library-folders
GET    /admin/api/subscriptions
GET    /admin/api/subscriptions/{id}
POST   /admin/api/subscriptions/{id}/extend
POST   /admin/api/subscriptions/{id}/cancel
GET    /admin/api/customers
PUT    /admin/api/customers/{username}/status
GET    /admin/api/tickets
GET    /admin/api/tickets/{id}
POST   /admin/api/tickets/{id}/messages
PUT    /admin/api/tickets/{id}/status
"""

from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from uuid import uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from models.plan import PlanCreate, PlanUpdate
from models.subscription import SubscriptionExtendRequest, SubscriptionAdminCancelRequest, ManualSubscriptionCreate
from models.customer import CustomerPublic, CustomerStatusUpdate, CustomerAdminUpdate, CustomerAdminCreate, Role as CustomerRole
from models.ticket import TicketMessageCreate, TicketStatusUpdate
from models.promotion import PromotionCreate, PromotionUpdate
from models.responses import TicketPublic, CustomerCreatedResponse
from api.dependencies import require_admin, hash_password

import db.plans_repository as plans_repo
import db.subscriptions_repository as subscriptions_repo
import db.payments_repository as payments_repo
import db.customers_repository as customers_repo
import db.tickets_repository as tickets_repo
import db.promotions_repository as promotions_repo
import services.jellyfin_provisioning as jellyfin
import services.anime_sam_client as anime_sam_client
import services.jellyfin_auto_sync as jellyfin_auto_sync
from services.payments.registry import get_provider
from services.payments.events import NormalizedSubscriptionEvent, SubscriptionEventType
from services.billing_service import handle_subscription_event, reapply_access_policy
from services.parental_rating import effective_max_rating
from services.stats_service import get_dashboard_stats
from params import ANIME_SAM_ADMIN_USERNAME, ANIME_SAM_ADMIN_PASSWORD

router = APIRouter(prefix="/admin/api", tags=["Administration"])


# ---------------------------------------------------------------------------
# Paliers
# ---------------------------------------------------------------------------

_PRODUCT_NAME = "Anime Sama — Accès serveur Jellyfin"


def _paypal_error_detail(exc: httpx.HTTPStatusError) -> str:
    """PayPal renvoie le champ fautif dans le corps JSON (ex. INVALID_STRING_MIN_LENGTH sur
    /description) — str(exc) seul ne montre que le code HTTP, inutile pour diagnostiquer."""
    try:
        body = exc.response.json()
        details = body.get("details") or []
        if details:
            d = details[0]
            return f"{body.get('message', '')} ({d.get('field', '?')} : {d.get('description', d.get('issue', ''))})"
        return body.get("message", str(exc))
    except Exception:
        return str(exc)


@router.get("/plans", summary="Liste des paliers (admin, inclut les inactifs)")
async def list_plans_admin(_: dict = Depends(require_admin)):
    return await plans_repo.list_all(include_inactive=True)


def _validate_discount_fields(discount_type, discount_value) -> None:
    if (discount_type is None) != (discount_value is None):
        raise HTTPException(400, "La réduction doit avoir un type ET une valeur, ou aucun des deux")
    if discount_type is None:
        return
    if discount_type == "percent" and not (0 < discount_value <= 100):
        raise HTTPException(400, "Une réduction en pourcentage doit être comprise entre 0 et 100")
    if discount_value <= 0:
        raise HTTPException(400, "La valeur de la réduction doit être strictement positive")


@router.post("/plans", status_code=201, summary="Créer un palier")
async def create_plan(body: PlanCreate, _: dict = Depends(require_admin)):
    if await plans_repo.find_by_slug(body.slug):
        raise HTTPException(409, f"Le palier '{body.slug}' existe déjà")
    if body.price <= 0:
        raise HTTPException(400, "Le prix doit être strictement positif")
    if body.duration_days <= 0:
        raise HTTPException(400, "La durée de validité doit être strictement positive")
    if body.max_parental_rating is not None and body.max_parental_rating < 0:
        raise HTTPException(400, "La restriction d'âge doit être un nombre positif")
    _validate_discount_fields(body.discount_type, body.discount_value)

    provider = get_provider("paypal")
    provider_refs: dict = {}
    try:
        product_id = await provider.ensure_product(_PRODUCT_NAME, "Abonnements d'accès au serveur Jellyfin")
        plan_id_paypal = await provider.create_billing_plan(
            product_id=product_id, plan_name=body.name, description=body.description,
            price=body.price, currency=body.currency, duration_days=body.duration_days,
        )
        provider_refs["paypal"] = {"product_id": product_id, "plan_id": plan_id_paypal}
    except httpx.HTTPStatusError as exc:
        raise HTTPException(502, f"Échec de la création du plan PayPal : {_paypal_error_detail(exc)}")
    except Exception as exc:
        raise HTTPException(502, f"Échec de la création du plan PayPal : {exc}")

    doc = body.model_dump()
    if doc.get("discount_type") is not None:
        doc["discount_type"] = doc["discount_type"].value if hasattr(doc["discount_type"], "value") else doc["discount_type"]
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

    raw = body.model_dump(exclude_unset=True)
    fields = {k: v for k, v in raw.items() if v is not None}
    # Un champ de réduction explicitement mis à null (ex. "retirer la réduction") doit être
    # appliqué comme tel plutôt que d'être filtré comme un champ non fourni — sinon aucun
    # moyen de mettre fin à une réduction avant son expiration.
    # Idem pour max_parental_rating : un null explicite ("retirer la restriction du palier")
    # doit être appliqué comme tel, pas filtré comme un champ non fourni.
    for nullable_field in ("discount_type", "discount_value", "discount_expires_at", "max_parental_rating"):
        if nullable_field in raw:
            fields[nullable_field] = raw[nullable_field]
    warning = None

    if "price" in fields and fields["price"] <= 0:
        raise HTTPException(400, "Le prix doit être strictement positif")
    if "duration_days" in fields and fields["duration_days"] <= 0:
        raise HTTPException(400, "La durée de validité doit être strictement positive")
    if fields.get("max_parental_rating") is not None and fields["max_parental_rating"] < 0:
        raise HTTPException(400, "La restriction d'âge doit être un nombre positif")

    resulting_discount_type = fields["discount_type"] if "discount_type" in fields else existing.get("discount_type")
    resulting_discount_value = fields["discount_value"] if "discount_value" in fields else existing.get("discount_value")
    _validate_discount_fields(resulting_discount_type, resulting_discount_value)
    if "discount_type" in fields and fields["discount_type"] is not None:
        fields["discount_type"] = fields["discount_type"].value if hasattr(fields["discount_type"], "value") else fields["discount_type"]

    price_changed = "price" in fields and fields["price"] != existing.get("price")
    duration_changed = "duration_days" in fields and fields["duration_days"] != existing.get("duration_days")

    if price_changed or duration_changed:
        provider = get_provider("paypal")
        product_id = existing.get("provider_refs", {}).get("paypal", {}).get("product_id")
        if product_id:
            try:
                new_paypal_plan_id = await provider.create_billing_plan(
                    product_id=product_id,
                    plan_name=fields.get("name", existing["name"]),
                    description=fields.get("description", existing.get("description", "")),
                    price=fields.get("price", existing["price"]),
                    currency=fields.get("currency", existing.get("currency", "EUR")),
                    duration_days=fields.get("duration_days", existing.get("duration_days", 30)),
                )
                provider_refs = dict(existing.get("provider_refs", {}))
                provider_refs["paypal"] = {"product_id": product_id, "plan_id": new_paypal_plan_id}
                fields["provider_refs"] = provider_refs
                warning = (
                    "Un nouveau plan PayPal a été créé pour ce prix — les abonnés déjà "
                    "engagés restent facturés sur l'ancien tarif jusqu'à leur prochaine "
                    "souscription."
                )
            except httpx.HTTPStatusError as exc:
                raise HTTPException(502, f"Échec de la mise à jour PayPal : {_paypal_error_detail(exc)}")
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

@router.post("/subscriptions", status_code=201, summary="Ajouter un abonnement manuellement (geste commercial, sans PayPal)")
async def create_manual_subscription(body: ManualSubscriptionCreate, _: dict = Depends(require_admin)):
    customer = await customers_repo.find_by_username(body.username)
    if not customer:
        raise HTTPException(404, "Client introuvable")
    if await subscriptions_repo.find_current_for_user(body.username):
        raise HTTPException(409, "Ce client a déjà un abonnement en cours")

    plan = await plans_repo.find_by_id(body.plan_id)
    if not plan:
        raise HTTPException(404, "Palier introuvable")

    duration = body.duration_days or plan.get("duration_days", 30)
    period_end = datetime.now(timezone.utc) + timedelta(days=duration)
    manual_ref = f"manual-{uuid4().hex}"

    sub_id = await subscriptions_repo.create({
        "username":                 body.username,
        "plan_id":                  plan["id"],
        "provider":                 "manual",
        "provider_subscription_id": manual_ref,
        "status":                   "pending",
        "cancel_at_period_end":     True,  # geste ponctuel — ne se renouvelle jamais tout seul
        "current_period_end":       None,
        "jellyfin_user_id":         None,
        "jellyfin_username":        None,
    })

    await handle_subscription_event(NormalizedSubscriptionEvent(
        provider="manual",
        event_id=f"manual-activate-{sub_id}",
        event_type=SubscriptionEventType.ACTIVATED,
        provider_subscription_id=manual_ref,
        occurred_at=datetime.now(timezone.utc),
        current_period_end=period_end,
    ))

    return await subscriptions_repo.find_by_id(sub_id)


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

    if sub["provider"] != "manual" and sub.get("provider_subscription_id"):
        try:
            provider = get_provider(sub["provider"])
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
# Clients
# ---------------------------------------------------------------------------

@router.get("/customers", response_model=list[CustomerPublic], summary="Liste des clients")
async def list_customers(_: dict = Depends(require_admin)):
    return await customers_repo.list_customers()


def _validate_dob(date_of_birth: str) -> None:
    try:
        dob = date.fromisoformat(date_of_birth[:10])
    except (ValueError, TypeError):
        raise HTTPException(400, "Date de naissance invalide")
    if dob > date.today():
        raise HTTPException(400, "La date de naissance ne peut pas être dans le futur")


@router.post("/customers", status_code=201, response_model=CustomerCreatedResponse, summary="Créer un compte client")
async def create_customer_admin(body: CustomerAdminCreate, _: dict = Depends(require_admin)):
    if await customers_repo.find_by_username(body.username):
        raise HTTPException(409, f"Le compte '{body.username}' existe déjà")
    _validate_dob(body.date_of_birth)

    generated_password = None if body.password else secrets.token_urlsafe(9)
    password = body.password or generated_password

    await customers_repo.create_customer({
        "username":        body.username,
        "email":            body.email,
        "role":             CustomerRole.CUSTOMER,
        "hashed_password":  hash_password(password),
        "is_active":        True,
        "date_of_birth":     body.date_of_birth,
        "created_at":       datetime.now(timezone.utc).isoformat(),
    })

    return {"username": body.username, "email": body.email, "generated_password": generated_password}


@router.put("/customers/{username}", response_model=CustomerPublic, summary="Modifier un client (e-mail, mot de passe, date de naissance)")
async def update_customer_admin(username: str, body: CustomerAdminUpdate, _: dict = Depends(require_admin)):
    customer = await customers_repo.find_by_username(username)
    if not customer:
        raise HTTPException(404, "Client introuvable")

    fields: dict = {}
    if body.email is not None:
        fields["email"] = body.email
    if body.date_of_birth is not None:
        _validate_dob(body.date_of_birth)
        fields["date_of_birth"] = body.date_of_birth
    if body.new_password:
        if len(body.new_password) < 8:
            raise HTTPException(400, "Le mot de passe doit contenir au moins 8 caractères")
        fields["hashed_password"] = hash_password(body.new_password)

    if fields:
        await customers_repo.update_customer(username, fields)

    if body.new_password:
        sub = await subscriptions_repo.find_current_for_user(username)
        if sub and sub.get("jellyfin_user_id"):
            await jellyfin.set_password(sub["jellyfin_user_id"], body.new_password)

    if body.date_of_birth is not None:
        await reapply_access_policy(username)

    return await customers_repo.find_by_username(username)


@router.put("/customers/{username}/status", response_model=CustomerPublic, summary="Activer/désactiver un client")
async def update_customer_status(username: str, body: CustomerStatusUpdate, admin: dict = Depends(require_admin)):
    if username == admin["username"]:
        raise HTTPException(400, "Impossible de modifier son propre statut")

    customer = await customers_repo.find_by_username(username)
    if not customer:
        raise HTTPException(404, "Client introuvable")

    await customers_repo.update_customer(username, {"is_active": body.is_active})

    # Un compte désactivé perd aussi son accès Jellyfin (sinon la désactivation du compte
    # boutique n'empêche pas réellement de continuer à regarder) ; à la réactivation, on
    # restaure l'accès Jellyfin si un abonnement non terminal existe encore.
    sub = await subscriptions_repo.find_current_for_user(username)
    if sub and sub.get("jellyfin_user_id"):
        if not body.is_active:
            await jellyfin.disable_user(sub["jellyfin_user_id"])
        elif sub["status"] in ("active", "past_due", "suspended"):
            plan = await plans_repo.find_by_id(sub["plan_id"])
            if plan:
                await jellyfin.enable_user(
                    sub["jellyfin_user_id"],
                    plan.get("jellyfin_library_folder_ids", []),
                    plan.get("max_devices", 1),
                    plan.get("allow_downloads", False),
                    max_parental_rating=effective_max_rating(customer.get("date_of_birth"), plan.get("max_parental_rating")),
                )

    return await customers_repo.find_by_username(username)


@router.delete("/customers/{username}", status_code=204, summary="Supprimer un client")
async def delete_customer(username: str, admin: dict = Depends(require_admin)):
    if username == admin["username"]:
        raise HTTPException(400, "Impossible de supprimer son propre compte")

    customer = await customers_repo.find_by_username(username)
    if not customer:
        raise HTTPException(404, "Client introuvable")
    if customer.get("role") == "admin":
        raise HTTPException(400, "Impossible de supprimer un compte administrateur")

    # Contrairement à la désactivation (qui ne fait que couper l'accès et préserve
    # l'historique — cf. update_customer_status), une suppression de compte boutique
    # supprime aussi le compte Jellyfin : c'est définitif des deux côtés. On cherche sur
    # TOUS les abonnements (pas seulement le courant, via find_current_for_user) car le
    # compte Jellyfin reste rattaché à un abonnement même une fois celui-ci passé en statut
    # terminal (expiré, annulé) — sinon un client dont l'abonnement est déjà terminé
    # garderait un compte Jellyfin fantôme après suppression de son compte boutique.
    subs = await subscriptions_repo.list_for_user(username)
    jellyfin_user_id = next((s["jellyfin_user_id"] for s in subs if s.get("jellyfin_user_id")), None)
    if jellyfin_user_id:
        await jellyfin.delete_user(jellyfin_user_id)

    await customers_repo.delete_customer(username)


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


# ---------------------------------------------------------------------------
# Statistiques
# ---------------------------------------------------------------------------

@router.get("/stats", summary="Statistiques de vente et d'utilisation")
async def dashboard_stats(_: dict = Depends(require_admin)):
    return await get_dashboard_stats()


# ---------------------------------------------------------------------------
# Promotions
# ---------------------------------------------------------------------------

@router.get("/promotions", summary="Liste des codes promo")
async def list_promotions(_: dict = Depends(require_admin)):
    return await promotions_repo.list_all()


@router.post("/promotions", status_code=201, summary="Créer un code promo")
async def create_promotion(body: PromotionCreate, _: dict = Depends(require_admin)):
    if await promotions_repo.find_by_code(body.code):
        raise HTTPException(409, f"Le code '{body.code.upper()}' existe déjà")
    if body.discount_type == "percent" and not (0 < body.discount_value <= 100):
        raise HTTPException(400, "Une remise en pourcentage doit être comprise entre 0 et 100")
    if body.discount_value <= 0:
        raise HTTPException(400, "La valeur de la remise doit être strictement positive")

    doc = body.model_dump()
    doc["discount_type"] = doc["discount_type"].value if hasattr(doc["discount_type"], "value") else doc["discount_type"]
    pid = await promotions_repo.create(doc)
    return await promotions_repo.find_by_id(pid)


@router.put("/promotions/{promo_id}", summary="Modifier un code promo")
async def update_promotion(promo_id: str, body: PromotionUpdate, _: dict = Depends(require_admin)):
    if not await promotions_repo.find_by_id(promo_id):
        raise HTTPException(404, "Code promo introuvable")

    fields = {k: v for k, v in body.model_dump(exclude_unset=True).items() if v is not None}
    if "discount_type" in fields and hasattr(fields["discount_type"], "value"):
        fields["discount_type"] = fields["discount_type"].value
    if fields:
        await promotions_repo.update(promo_id, fields)
    return await promotions_repo.find_by_id(promo_id)


@router.delete("/promotions/{promo_id}", status_code=204, summary="Supprimer un code promo")
async def delete_promotion(promo_id: str, _: dict = Depends(require_admin)):
    if not await promotions_repo.find_by_id(promo_id):
        raise HTTPException(404, "Code promo introuvable")
    await promotions_repo.delete(promo_id)


# ---------------------------------------------------------------------------
# Synchronisation Jellyfin — raccourci vers anime_sam
# ---------------------------------------------------------------------------
# La synchronisation (extension anime_sama) existe déjà côté anime_sam, manuelle et
# automatique toutes les heures. Ces deux routes ne font que relayer un déclenchement/statut
# vers l'API anime_sam — seule dépendance volontaire de shop_backend vers l'autre système,
# ajoutée à la demande explicite de l'utilisateur pour éviter d'avoir à changer d'admin.

@router.post("/jellyfin/sync", summary="Synchroniser Jellyfin (raccourci vers anime_sam)")
async def trigger_jellyfin_sync_admin(_: dict = Depends(require_admin)):
    if not ANIME_SAM_ADMIN_USERNAME or not ANIME_SAM_ADMIN_PASSWORD:
        raise HTTPException(503, "Identifiants anime_sam non configurés (ANIME_SAM_ADMIN_USERNAME/PASSWORD dans .env)")
    ok = await anime_sam_client.trigger_jellyfin_sync()
    if not ok:
        raise HTTPException(502, "Échec du déclenchement — anime_sam injoignable ou identifiants invalides")
    return {"ok": True}


@router.get("/jellyfin/sync-status", summary="Dernière synchronisation Jellyfin (anime_sam)")
async def jellyfin_sync_status_admin(_: dict = Depends(require_admin)):
    status = await anime_sam_client.get_sync_status()
    if status is None:
        return {"last_sync": None, "reachable": False}
    return {"last_sync": status.get("last_sync"), "reachable": True}


class JellyfinAutoSyncUpdate(BaseModel):
    enabled:        bool
    interval_hours: int


@router.get("/jellyfin/auto-sync", summary="Configuration de la synchronisation Jellyfin automatique")
async def get_jellyfin_auto_sync(_: dict = Depends(require_admin)):
    return await jellyfin_auto_sync.get_config()


@router.put("/jellyfin/auto-sync", summary="Configurer la synchronisation Jellyfin automatique")
async def update_jellyfin_auto_sync(body: JellyfinAutoSyncUpdate, _: dict = Depends(require_admin)):
    if body.interval_hours < 1:
        raise HTTPException(400, "L'intervalle doit être d'au moins 1 heure")
    return await jellyfin_auto_sync.set_config(body.enabled, body.interval_hours)
