from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


class PlanCreate(BaseModel):
    slug:                        str
    name:                        str
    description:                 str            = ""
    price:                       float
    currency:                    str            = "EUR"
    billing_period:              str            = "month"
    jellyfin_library_folder_ids: list[str]       = Field(default_factory=list)
    jellyfin_library_names:      list[str]       = Field(default_factory=list)
    max_devices:                 int             = 2
    allow_downloads:             bool            = False
    is_active:                   bool            = True
    sort_order:                  int             = 0


class PlanUpdate(BaseModel):
    name:                        Optional[str]        = None
    description:                 Optional[str]        = None
    price:                       Optional[float]       = None
    currency:                    Optional[str]         = None
    jellyfin_library_folder_ids: Optional[list[str]]   = None
    jellyfin_library_names:      Optional[list[str]]   = None
    max_devices:                 Optional[int]         = None
    allow_downloads:             Optional[bool]        = None
    is_active:                   Optional[bool]        = None
    sort_order:                  Optional[int]         = None
