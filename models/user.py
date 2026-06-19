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


class UserPermissions(BaseModel):
    """Permissions accordées à un utilisateur non-admin."""
    can_sync:           bool = False   # POST /{slug}/sync-content
    can_delete:         bool = False   # DELETE /catalogues/{slug}
    can_refresh:        bool = False   # rafraichir + update-all
    # Catalogues accessibles — vide = tous, sinon whitelist de slugs
    allowed_catalogues: list[str] = Field(default_factory=list)
    # Restrictions de contenu par catalogue (slug → accès fin)
    # Clé absente = accès complet au catalogue
    catalogue_content:  dict[str, ContentAccess] = Field(default_factory=dict)


class UserInDB(BaseModel):
    username:        str
    email:           Optional[str]   = None
    role:            Role            = Role.USER
    hashed_password: str
    is_active:       bool            = True
    permissions:     UserPermissions = Field(default_factory=UserPermissions)


class UserCreate(BaseModel):
    username:    str
    password:    str
    email:       Optional[str]   = None
    role:        Role            = Role.USER
    permissions: UserPermissions = Field(default_factory=UserPermissions)


class UserUpdate(BaseModel):
    email:       Optional[str]             = None
    is_active:   Optional[bool]            = None
    role:        Optional[Role]            = None
    permissions: Optional[UserPermissions] = None


class UserPublic(BaseModel):
    username:    str
    email:       Optional[str]
    role:        Role
    is_active:   bool
    permissions: UserPermissions
