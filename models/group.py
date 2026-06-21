from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field
from models.user import QuotaConfig


class GroupPermissions(BaseModel):
    can_sync:                 bool        = False
    can_delete:               bool        = False
    can_refresh:              bool        = False
    # Téléchargement
    can_download:             bool        = True
    download_forbidden_slugs: list[str]   = Field(default_factory=list)
    download_quota:           dict        = Field(default_factory=dict)
    # Quota de sync
    quota:                    QuotaConfig = Field(default_factory=QuotaConfig)


class GroupCreate(BaseModel):
    name:              str
    type:              str  # "catalogue" | "genre" | "permission"
    description:       Optional[str]      = None
    # Catalogue group — liste de slugs spécifiques
    catalogue_slugs:   list[str]          = Field(default_factory=list)
    catalogue_content: dict               = Field(default_factory=dict)  # slug → {saisons,films,scans}
    # Genre group — accès à tous les catalogues de ces genres
    genres:            list[str]          = Field(default_factory=list)
    # Permissions accordées aux membres (pour tous les types de groupe)
    permissions:       GroupPermissions   = Field(default_factory=GroupPermissions)


class GroupUpdate(BaseModel):
    name:              Optional[str]              = None
    description:       Optional[str]              = None
    catalogue_slugs:   Optional[list[str]]        = None
    catalogue_content: Optional[dict]             = None
    genres:            Optional[list[str]]         = None
    permissions:       Optional[GroupPermissions] = None
