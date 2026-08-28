from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class DiscountType(str, Enum):
    PERCENT = "percent"
    FIXED   = "fixed"


class PromotionCreate(BaseModel):
    code:                str
    description:         str            = ""
    discount_type:       DiscountType
    discount_value:       float
    applicable_plan_ids: list[str]       = Field(default_factory=list)  # vide = tous les paliers
    max_uses:             Optional[int]  = None
    expires_at:           Optional[str]  = None
    is_active:             bool          = True


class PromotionUpdate(BaseModel):
    description:         Optional[str]         = None
    discount_type:        Optional[DiscountType] = None
    discount_value:        Optional[float]       = None
    applicable_plan_ids:  Optional[list[str]]   = None
    max_uses:              Optional[int]         = None
    expires_at:             Optional[str]        = None
    is_active:               Optional[bool]      = None
