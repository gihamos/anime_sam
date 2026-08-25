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
    plan_id: str


class ChangePlanRequest(BaseModel):
    new_plan_id: str


class CancelRequest(BaseModel):
    reason: Optional[str] = None


class SubscriptionExtendRequest(BaseModel):
    days: int


class SubscriptionAdminCancelRequest(BaseModel):
    reason: Optional[str] = None
