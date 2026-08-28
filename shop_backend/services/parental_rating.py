"""
Restriction de contenu liée à l'âge — calcule le seuil Jellyfin (UserPolicy.MaxParentalRating)
à appliquer à un client.

Vérifié en conditions réelles contre l'instance Jellyfin de production (10.11.11) :
MaxParentalRating est un entier comparé au score numérique de la classification de chaque
titre (Jellyfin résout lui-même "TV-MA", "FR-16", etc. vers un score — pas besoin de le faire
nous-mêmes). L'échelle officielle française exposée par Jellyfin correspond directement à des
paliers d'âge (0, 6, 9, 10, 12, 13, 14, 16, 18) mais n'importe quel entier fonctionne comme
seuil, y compris l'âge brut du client.

Deux sources de restriction, cumulables (la plus stricte des deux s'applique) :
  - l'âge du client (date_of_birth du compte) — aucune restriction dès 18 ans révolus ;
  - le palier souscrit (max_parental_rating, optionnel, défini par l'admin).
"""

from __future__ import annotations

from datetime import date
from typing import Optional


def age_from_dob(date_of_birth: str) -> Optional[int]:
    try:
        dob = date.fromisoformat(date_of_birth[:10])
    except (ValueError, TypeError):
        return None
    today = date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return max(age, 0)


def age_based_max_rating(date_of_birth: Optional[str]) -> Optional[int]:
    """None si pas de date de naissance connue, ou si le client est majeur (18 ans+) —
    dans ces deux cas, aucune restriction liée à l'âge n'est appliquée."""
    if not date_of_birth:
        return None
    age = age_from_dob(date_of_birth)
    if age is None or age >= 18:
        return None
    return age


def effective_max_rating(date_of_birth: Optional[str], plan_max_rating: Optional[int]) -> Optional[int]:
    """Seuil MaxParentalRating à appliquer — le plus restrictif entre la restriction d'âge
    du client et celle, éventuelle, du palier. None si aucune des deux n'est active."""
    candidates = [v for v in (age_based_max_rating(date_of_birth), plan_max_rating) if v is not None]
    return min(candidates) if candidates else None
