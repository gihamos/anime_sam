from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional

from models.promotion import DiscountType


class PlanCreate(BaseModel):
    slug:                        str
    name:                        str
    description:                 str            = ""
    price:                       float
    currency:                    str            = "EUR"
    duration_days:               int            = 30
    jellyfin_library_folder_ids: list[str]       = Field(default_factory=list)
    jellyfin_library_names:      list[str]       = Field(default_factory=list)
    max_devices:                 int             = 2
    allow_downloads:             bool            = False
    is_active:                   bool            = True
    sort_order:                  int             = 0
    # Réduction automatique, affichée directement sur le palier côté vitrine (prix barré) —
    # distincte des codes promo, qui restent un mécanisme à part (voir models/promotion.py).
    discount_type:                Optional[DiscountType] = None
    discount_value:                Optional[float]        = None
    discount_expires_at:            Optional[str]          = None
    # Seuil UserPolicy.MaxParentalRating appliqué aux abonnés de ce palier (échelle Jellyfin,
    # ex. 12 = équivalent -12 ans) — cumulable avec la restriction d'âge du client (la plus
    # stricte des deux s'applique, voir services/parental_rating.py). None = pas de plafond.
    max_parental_rating:              Optional[int]          = None


class PlanUpdate(BaseModel):
    name:                        Optional[str]        = None
    description:                 Optional[str]        = None
    price:                       Optional[float]       = None
    currency:                    Optional[str]         = None
    duration_days:               Optional[int]         = None
    jellyfin_library_folder_ids: Optional[list[str]]   = None
    jellyfin_library_names:      Optional[list[str]]   = None
    max_devices:                 Optional[int]         = None
    allow_downloads:             Optional[bool]        = None
    is_active:                   Optional[bool]        = None
    sort_order:                  Optional[int]         = None
    discount_type:                Optional[DiscountType] = None
    discount_value:                 Optional[float]       = None
    discount_expires_at:              Optional[str]        = None
    max_parental_rating:                Optional[int]      = None
