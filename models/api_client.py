from typing import Optional
from pydantic import BaseModel, Field
from models.user import QuotaConfig


class APIClientPermissions(BaseModel):
    can_sync:           bool        = False
    can_delete:         bool        = False
    can_refresh:        bool        = False
    allowed_catalogues: list[str]   = Field(default_factory=list)
    catalogue_content:  dict        = Field(default_factory=dict)
    quota:              QuotaConfig = Field(default_factory=QuotaConfig)


class APIClientCreate(BaseModel):
    name:        str
    description: Optional[str]           = None
    permissions: APIClientPermissions    = Field(default_factory=APIClientPermissions)


class APIClientUpdate(BaseModel):
    name:           Optional[str]                    = None
    description:    Optional[str]                    = None
    is_active:      Optional[bool]                   = None
    is_blocked:     Optional[bool]                   = None
    blocked_reason: Optional[str]                    = None
    blocked_until:  Optional[str]                    = None
    permissions:    Optional[APIClientPermissions]   = None
