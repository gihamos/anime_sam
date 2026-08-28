"""
Calcul du prix effectif d'un palier.

Deux mécanismes de réduction distincts et cumulables :
  - la réduction du palier lui-même (discount_type/discount_value/discount_expires_at sur
    le document plan) — automatique, affichée à tous les visiteurs sans code à saisir ;
  - le code promo (db/promotions_repository.py) — saisi par le client à la souscription.

Les deux utilisent la même formule de remise (apply_discount), appliquée en cascade :
palier → réduction du palier → code promo éventuel.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional


def apply_discount(price: float, discount_type: str, discount_value: float) -> float:
    if discount_type == "percent":
        discounted = price * (1 - discount_value / 100)
    else:
        discounted = price - discount_value
    return round(max(discounted, 0.5), 2)  # PayPal exige un montant strictement positif


def discount_is_active(plan: dict) -> bool:
    if not plan.get("discount_type") or plan.get("discount_value") is None:
        return False
    expires_at = plan.get("discount_expires_at")
    if expires_at and expires_at < datetime.now(timezone.utc).isoformat():
        return False
    return True


def effective_price(plan: dict) -> float:
    """Prix après réduction automatique du palier si elle est active, sinon le prix normal."""
    if not discount_is_active(plan):
        return plan["price"]
    return apply_discount(plan["price"], plan["discount_type"], plan["discount_value"])


def discounted_price_or_none(plan: dict) -> Optional[float]:
    """Pour l'affichage public — None si aucune réduction active (évite au front d'avoir
    à revalider lui-même l'expiration)."""
    return effective_price(plan) if discount_is_active(plan) else None
