from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field
from typing import Optional

from models.promotion import DiscountType


# ══════════════════════════════════════════════════════════════════════════
#  AUTHENTIFICATION
# ══════════════════════════════════════════════════════════════════════════

class TokenResponse(BaseModel):
    """Jeton d'accès shop_backend — indépendant des tokens anime_sam."""
    model_config = ConfigDict(json_schema_extra={"example": {
        "access_token":  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        "token_type":    "bearer",
    }})

    access_token:  str           = Field(description="JWT Bearer shop_backend — Authorization: Bearer <token>")
    refresh_token: Optional[str] = Field(default=None, description="Refresh token (30 jours) — POST /auth/refresh")
    token_type:    str           = Field(default="bearer", description="Toujours 'bearer'")


class MessageResponse(BaseModel):
    message: str


class CustomerCreatedResponse(BaseModel):
    username:          str
    email:              Optional[str] = None
    generated_password: Optional[str] = Field(
        default=None,
        description="Révélé une seule fois — null si l'admin a fourni son propre mot de passe à la création.",
    )


# ══════════════════════════════════════════════════════════════════════════
#  PLANS
# ══════════════════════════════════════════════════════════════════════════

class PlanPublic(BaseModel):
    """Palier tel que visible sur la vitrine — jamais provider_refs, jamais les GUIDs
    Jellyfin bruts (détail d'implémentation serveur, pas une info client)."""
    id:                     str
    slug:                   str
    name:                   str
    description:            str
    price:                  float
    currency:               str
    duration_days:          int
    jellyfin_library_names: list[str] = Field(default_factory=list)
    max_devices:            int
    allow_downloads:        bool
    sort_order:              int = 0
    discount_type:            Optional[DiscountType] = None
    discount_value:             Optional[float]        = None
    discount_expires_at:          Optional[str]         = None
    discounted_price:               Optional[float]     = Field(
        default=None, description="Prix après réduction active du palier, ou null si aucune réduction en cours."
    )
    max_parental_rating:               Optional[int]     = None


# ══════════════════════════════════════════════════════════════════════════
#  ABONNEMENTS
# ══════════════════════════════════════════════════════════════════════════

class SubscribeResponse(BaseModel):
    subscription_id: str
    approval_url:     str


class SubscriptionDetail(BaseModel):
    id:                                str
    plan_id:                            str
    plan_name:                          Optional[str] = None
    status:                              str
    auto_renew:                           bool = True
    cancel_at_period_end:                 bool = False
    current_period_end:                    Optional[str] = None
    jellyfin_username:                      Optional[str] = None
    jellyfin_initial_password_pending:       Optional[str] = None
    created_at:                              Optional[str] = None
    activated_at:                            Optional[str] = None


# ══════════════════════════════════════════════════════════════════════════
#  TICKETS
# ══════════════════════════════════════════════════════════════════════════

class TicketMessagePublic(BaseModel):
    author_role:     str
    author_username: str
    body:            str
    created_at:      str


class TicketPublic(BaseModel):
    id:          str
    username:    str
    subject:     str
    status:      str
    messages:    list[TicketMessagePublic] = Field(default_factory=list)
    created_at:  str
    updated_at:  str
