from __future__ import annotations
from pydantic import BaseModel
from typing import Optional


class PaymentPublic(BaseModel):
    id:                  str
    plan_id:             str
    amount:              float
    currency:            str
    provider:            str
    status:               str
    paid_at:              Optional[str] = None
