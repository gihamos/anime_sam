from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class SubscriptionEventType(str, Enum):
    ACTIVATED     = "activated"
    RENEWED       = "renewed"
    PAYMENT_FAILED = "payment_failed"
    SUSPENDED     = "suspended"
    CANCELLED     = "cancelled"
    EXPIRED       = "expired"


@dataclass
class NormalizedSubscriptionEvent:
    """Représentation provider-agnostique d'un événement de cycle de vie d'abonnement —
    le seul type que consomme services/billing_service.py. Aucun code de billing_service
    ou des routes ne doit jamais dépendre d'un type spécifique à PayPal/Stripe/etc."""
    provider:                  str
    event_id:                  str
    event_type:                SubscriptionEventType
    provider_subscription_id:  str
    occurred_at:                datetime
    current_period_end:         Optional[datetime] = None
    amount:                     Optional[float]     = None
    currency:                   Optional[str]        = None
    provider_payment_id:        Optional[str]         = None
    raw:                         Optional[dict]         = None
