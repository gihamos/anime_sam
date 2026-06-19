from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class Role(str, Enum):
    ADMIN = "admin"
    USER  = "user"


class ContentAccess(BaseModel):
    """Accès fin aux contenus d'un catalogue (slugs autorisés, vide = tous)."""
    saisons: list[str] = Field(default_factory=list)
    films:   list[str] = Field(default_factory=list)
    scans:   list[str] = Field(default_factory=list)


class QuotaConfig(BaseModel):
    """Quota de synchronisation par période."""
    enabled:    bool = False
    period:     str  = "month"   # "day" | "month" | "year"
    max_syncs:  int  = 10


class UserPermissions(BaseModel):
    """Permissions accordées à un utilisateur non-admin."""
    can_sync:           bool        = False
    can_delete:         bool        = False
    can_refresh:        bool        = False
    allowed_catalogues: list[str]   = Field(default_factory=list)
    catalogue_content:  dict        = Field(default_factory=dict)
    quota:              QuotaConfig = Field(default_factory=QuotaConfig)


class UserInDB(BaseModel):
    username:        str
    email:           Optional[str]   = None
    role:            Role            = Role.USER
    hashed_password: str
    is_active:       bool            = True
    is_blocked:      bool            = False
    blocked_reason:  Optional[str]   = None
    blocked_until:   Optional[str]   = None   # ISO datetime ou None (permanent)
    permissions:     UserPermissions = Field(default_factory=UserPermissions)


class UserCreate(BaseModel):
    username:    str
    password:    str
    email:       Optional[str]   = None
    role:        Role            = Role.USER
    permissions: UserPermissions = Field(default_factory=UserPermissions)


class UserUpdate(BaseModel):
    email:          Optional[str]             = None
    password:       Optional[str]             = None
    is_active:      Optional[bool]            = None
    is_blocked:     Optional[bool]            = None
    blocked_reason: Optional[str]             = None
    blocked_until:  Optional[str]             = None
    role:           Optional[Role]            = None
    permissions:    Optional[UserPermissions] = None


class UserPublic(BaseModel):
    username:       str
    email:          Optional[str]
    role:           Role
    is_active:      bool
    is_blocked:     bool            = False
    blocked_reason: Optional[str]   = None
    blocked_until:  Optional[str]   = None
    permissions:    UserPermissions
