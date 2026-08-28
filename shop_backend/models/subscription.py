from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class SubscriptionStatus(str, Enum):
    PENDING   = "pending"
    ACTIVE    = "active"
    PAST_DUE  = "past_due"
    SUSPENDED = "suspended"
    CANCELLED = "cancelled"
    EXPIRED   = "expired"


class SubscribeRequest(BaseModel):
    plan_id:    str
    auto_renew: bool           = True
    promo_code: Optional[str]  = None


class ChangePlanRequest(BaseModel):
    new_plan_id: str


class CancelRequest(BaseModel):
    reason: Optional[str] = None


class SubscriptionExtendRequest(BaseModel):
    days: int


class SubscriptionAdminCancelRequest(BaseModel):
    reason: Optional[str] = None


class ManualSubscriptionCreate(BaseModel):
    username:      str
    plan_id:       str
    duration_days: Optional[int] = None  # remplace la durée par défaut du palier si fourni
