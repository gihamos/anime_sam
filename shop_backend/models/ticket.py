from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from enum import Enum


class TicketStatus(str, Enum):
    OPEN    = "open"
    PENDING = "pending"
    CLOSED  = "closed"


class TicketCreate(BaseModel):
    subject: str
    message: str


class TicketMessageCreate(BaseModel):
    body: str


class TicketStatusUpdate(BaseModel):
    status: TicketStatus
