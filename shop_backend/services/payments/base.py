from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional

from services.payments.events import NormalizedSubscriptionEvent


class WebhookSignatureError(Exception):
    """Levée par parse_webhook_event quand la signature du webhook est invalide — distinct
    d'un événement simplement non pertinent (qui retourne None sans lever d'exception).
    L'appelant doit répondre 400 sur cette exception, jamais traiter la requête."""


@dataclass
class CheckoutSession:
    provider_subscription_id: str
    approval_url:              str


class PaymentProvider(ABC):
    """Interface commune à tous les fournisseurs de paiement. PayPal est la seule
    implémentation aujourd'hui (services/payments/paypal.py) ; un fournisseur
    supplémentaire (Stripe...) s'ajoute en implémentant cette interface + une entrée dans
    registry.py — aucun autre fichier n'a besoin d'être modifié."""

    name: str

    @abstractmethod
    async def ensure_product(self, name: str, description: str) -> str:
        """Crée (ou retourne l'existant) le produit partagé par tous les paliers."""

    @abstractmethod
    async def create_billing_plan(
        self, *, product_id: str, plan_name: str, description: str,
        price: float, currency: str, billing_period: str,
    ) -> str:
        """Crée un plan de facturation récurrent pour un palier. Retourne l'id fournisseur."""

    @abstractmethod
    async def create_subscription_checkout(
        self, *, provider_plan_id: str, return_url: str, cancel_url: str, custom_id: str,
    ) -> CheckoutSession:
        """Initie un abonnement pour un client. Retourne l'URL d'approbation à laquelle
        rediriger le client (hébergée par le fournisseur, pas de formulaire à construire)."""

    @abstractmethod
    async def get_subscription_status(self, provider_subscription_id: str) -> dict:
        """État brut de l'abonnement côté fournisseur — utilisé pour la confirmation
        synchrone après redirection, en complément du webhook."""

    @abstractmethod
    async def cancel_subscription(self, provider_subscription_id: str, reason: str = "") -> None:
        ...

    @abstractmethod
    async def change_plan(self, provider_subscription_id: str, new_provider_plan_id: str) -> None:
        ...

    @abstractmethod
    async def parse_webhook_event(
        self, headers: dict, raw_body: bytes,
    ) -> Optional[NormalizedSubscriptionEvent]:
        """Vérifie la signature du webhook PUIS normalise l'événement. Lève
        WebhookSignatureError si la signature est invalide (l'appelant doit répondre 400).
        Retourne None si la signature est valide mais que le type d'événement n'est pas
        pertinent pour ce service (à ignorer silencieusement, réponse 200)."""
