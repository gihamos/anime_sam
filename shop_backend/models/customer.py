from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Role(str, Enum):
    ADMIN    = "admin"
    CUSTOMER = "customer"


class CustomerInDB(BaseModel):
    username:        str
    email:           Optional[str] = None
    role:            Role          = Role.CUSTOMER
    hashed_password: str
    is_active:       bool          = True
    created_at:      Optional[str] = None


class CustomerCreate(BaseModel):
    username: str
    password: str
    email:    Optional[str] = None


class CustomerPublic(BaseModel):
    username:   str
    email:      Optional[str] = None
    role:       Role
    is_active:  bool
    created_at: Optional[str] = None
