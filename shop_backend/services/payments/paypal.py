"""
Implémentation PayPal de PaymentProvider — Subscriptions API (abonnements récurrents
automatiques). Toute la logique spécifique à PayPal (auth OAuth2, noms d'endpoints,
vérification de signature webhook) reste confinée à ce fichier ; billing_service.py et les
routes ne connaissent que PaymentProvider/NormalizedSubscriptionEvent (services/payments/
base.py, events.py).

Portée générale des endpoints/noms d'événements ci-dessous confirmée par connaissance
générale de l'API PayPal v2 — à revérifier contre la documentation PayPal actuelle et un
compte sandbox avant la mise en production (pas testé en conditions réelles à l'écriture de
ce module, faute d'identifiants PayPal disponibles dans cet environnement).
"""

from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Optional

import httpx

from params import PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET, PAYPAL_WEBHOOK_ID, PAYPAL_API_BASE
from utils.logger import logger
from services.payments.base import PaymentProvider, CheckoutSession, WebhookSignatureError
from services.payments.events import NormalizedSubscriptionEvent, SubscriptionEventType

_EVENT_TYPE_MAP = {
    "BILLING.SUBSCRIPTION.ACTIVATED":       SubscriptionEventType.ACTIVATED,
    "PAYMENT.SALE.COMPLETED":               SubscriptionEventType.RENEWED,
    "BILLING.SUBSCRIPTION.PAYMENT.FAILED":  SubscriptionEventType.PAYMENT_FAILED,
    "BILLING.SUBSCRIPTION.SUSPENDED":       SubscriptionEventType.SUSPENDED,
    "BILLING.SUBSCRIPTION.CANCELLED":       SubscriptionEventType.CANCELLED,
    "BILLING.SUBSCRIPTION.EXPIRED":         SubscriptionEventType.EXPIRED,
}


class PayPalProvider(PaymentProvider):
    name = "paypal"

    def __init__(self) -> None:
        self._token: Optional[str] = None
        self._token_expires_at: float = 0.0

    # ------------------------------------------------------------------
    # Authentification OAuth2 (client credentials, cache mémoire)
    # ------------------------------------------------------------------

    async def _get_token(self) -> str:
        if self._token and time.monotonic() < self._token_expires_at:
            return self._token

        async with httpx.AsyncClient(base_url=PAYPAL_API_BASE, timeout=15) as c:
            r = await c.post(
                "/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(PAYPAL_CLIENT_ID, PAYPAL_CLIENT_SECRET),
            )
            r.raise_for_status()
            data = r.json()

        self._token = data["access_token"]
        # Marge de sécurité de 60s avant l'expiration réelle
        self._token_expires_at = time.monotonic() + int(data.get("expires_in", 3600)) - 60
        return self._token

    async def _client(self) -> httpx.AsyncClient:
        token = await self._get_token()
        return httpx.AsyncClient(
            base_url=PAYPAL_API_BASE, timeout=20,
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        )

    # ------------------------------------------------------------------
    # Produit / plans de facturation (setup, côté admin)
    # ------------------------------------------------------------------

    async def ensure_product(self, name: str, description: str) -> str:
        async with await self._client() as c:
            r = await c.get("/v1/catalogs/products", params={"page_size": 20})
            if r.status_code == 200:
                for p in r.json().get("products", []):
                    if p.get("name") == name:
                        return p["id"]

            r2 = await c.post("/v1/catalogs/products", json={
                "name": name, "description": description, "type": "SERVICE", "category": "SOFTWARE",
            })
            r2.raise_for_status()
            return r2.json()["id"]

    async def create_billing_plan(
        self, *, product_id: str, plan_name: str, description: str,
        price: float, currency: str, duration_days: int,
    ) -> str:
        async with await self._client() as c:
            r = await c.post("/v1/billing/plans", json={
                "product_id":  product_id,
                "name":        plan_name,
                # PayPal rejette une description vide (INVALID_STRING_MIN_LENGTH) — repli sur
                # le nom du palier si l'admin n'a pas renseigné de description.
                "description": description or plan_name,
                "billing_cycles": [{
                    # Frequency en jours — vérifié en conditions réelles (DAY est un
                    # interval_unit valide) : correspond exactement à duration_days, plus
                    # précis qu'un mapping mois/année approximatif.
                    "frequency": {"interval_unit": "DAY", "interval_count": duration_days},
                    "tenure_type": "REGULAR",
                    "sequence": 1,
                    "total_cycles": 0,  # 0 = infini (récurrent tant que non annulé)
                    "pricing_scheme": {"fixed_price": {"value": f"{price:.2f}", "currency_code": currency}},
                }],
                "payment_preferences": {
                    "auto_bill_outstanding": True,
                    "payment_failure_threshold": 3,
                },
            })
            r.raise_for_status()
            return r.json()["id"]

    # ------------------------------------------------------------------
    # Abonnement par client
    # ------------------------------------------------------------------

    async def create_subscription_checkout(
        self, *, provider_plan_id: str, return_url: str, cancel_url: str, custom_id: str,
    ) -> CheckoutSession:
        async with await self._client() as c:
            r = await c.post("/v1/billing/subscriptions", json={
                "plan_id":   provider_plan_id,
                "custom_id": custom_id,
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "user_action": "SUBSCRIBE_NOW",
                },
            })
            r.raise_for_status()
            data = r.json()

        approve_url = next(
            (l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), "",
        )
        return CheckoutSession(provider_subscription_id=data["id"], approval_url=approve_url)

    # ------------------------------------------------------------------
    # Paiement unique (pas de renouvellement automatique)
    # ------------------------------------------------------------------

    async def create_one_time_checkout(
        self, *, price: float, currency: str, return_url: str, cancel_url: str, custom_id: str,
    ) -> CheckoutSession:
        async with await self._client() as c:
            r = await c.post("/v2/checkout/orders", json={
                "intent": "CAPTURE",
                "purchase_units": [{
                    "custom_id": custom_id,
                    "amount": {"currency_code": currency, "value": f"{price:.2f}"},
                }],
                "application_context": {
                    "return_url": return_url,
                    "cancel_url": cancel_url,
                    "user_action": "PAY_NOW",
                },
            })
            r.raise_for_status()
            data = r.json()

        approve_url = next(
            (l["href"] for l in data.get("links", []) if l.get("rel") == "approve"), "",
        )
        return CheckoutSession(provider_subscription_id=data["id"], approval_url=approve_url)

    async def capture_one_time_payment(self, order_id: str) -> dict:
        async with await self._client() as c:
            r = await c.post(f"/v2/checkout/orders/{order_id}/capture")
            r.raise_for_status()
            data = r.json()

        capture = data["purchase_units"][0]["payments"]["captures"][0]
        return {
            "status":      capture["status"],
            "payment_id":  capture["id"],
            "amount":      float(capture["amount"]["value"]),
            "currency":    capture["amount"]["currency_code"],
        }

    async def get_subscription_status(self, provider_subscription_id: str) -> dict:
        async with await self._client() as c:
            r = await c.get(f"/v1/billing/subscriptions/{provider_subscription_id}")
            r.raise_for_status()
            return r.json()

    async def cancel_subscription(self, provider_subscription_id: str, reason: str = "") -> None:
        async with await self._client() as c:
            r = await c.post(
                f"/v1/billing/subscriptions/{provider_subscription_id}/cancel",
                json={"reason": reason or "Annulation demandée"},
            )
            if r.status_code not in (200, 204):
                logger.warning(f"PayPal : échec annulation {provider_subscription_id} — {r.status_code} {r.text}")
                r.raise_for_status()

    async def change_plan(self, provider_subscription_id: str, new_provider_plan_id: str) -> None:
        async with await self._client() as c:
            r = await c.post(
                f"/v1/billing/subscriptions/{provider_subscription_id}/revise",
                json={"plan_id": new_provider_plan_id},
            )
            r.raise_for_status()

    # ------------------------------------------------------------------
    # Webhooks
    # ------------------------------------------------------------------

    async def parse_webhook_event(
        self, headers: dict, raw_body: bytes,
    ) -> Optional[NormalizedSubscriptionEvent]:
        h = {k.lower(): v for k, v in headers.items()}
        import json
        try:
            body = json.loads(raw_body)
        except Exception:
            raise WebhookSignatureError("Corps de webhook illisible")

        verify_payload = {
            "transmission_id":   h.get("paypal-transmission-id", ""),
            "transmission_time": h.get("paypal-transmission-time", ""),
            "cert_url":           h.get("paypal-cert-url", ""),
            "auth_algo":           h.get("paypal-auth-algo", ""),
            "transmission_sig":    h.get("paypal-transmission-sig", ""),
            "webhook_id":           PAYPAL_WEBHOOK_ID,
            "webhook_event":        body,
        }

        async with await self._client() as c:
            r = await c.post("/v1/notifications/verify-webhook-signature", json=verify_payload)

        if r.status_code != 200 or r.json().get("verification_status") != "SUCCESS":
            raise WebhookSignatureError("Signature de webhook PayPal invalide")

        event_type_raw = body.get("event_type", "")
        mapped = _EVENT_TYPE_MAP.get(event_type_raw)
        if not mapped:
            return None  # type d'événement non pertinent pour ce service — à ignorer

        resource = body.get("resource", {}) or {}
        provider_subscription_id = resource.get("id") or resource.get("billing_agreement_id") or ""
        if not provider_subscription_id:
            return None

        current_period_end = None
        billing_info = resource.get("billing_info", {}) or {}
        next_billing = billing_info.get("next_billing_time")
        if next_billing:
            current_period_end = datetime.fromisoformat(next_billing.replace("Z", "+00:00"))

        amount = None
        currency = None
        provider_payment_id = None
        if mapped == SubscriptionEventType.RENEWED:
            amt = resource.get("amount", {}) or {}
            amount = float(amt.get("total", 0) or 0)
            currency = amt.get("currency", None)
            provider_payment_id = resource.get("id")

        return NormalizedSubscriptionEvent(
            provider=self.name,
            event_id=body.get("id", ""),
            event_type=mapped,
            provider_subscription_id=provider_subscription_id,
            occurred_at=datetime.now(timezone.utc),
            current_period_end=current_period_end,
            amount=amount,
            currency=currency,
            provider_payment_id=provider_payment_id,
            raw=body,
        )
