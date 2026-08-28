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
    date_of_birth:    Optional[str] = None
    created_at:      Optional[str] = None


class CustomerCreate(BaseModel):
    username:      str
    password:      str
    email:          Optional[str] = None
    date_of_birth:   str  # requis à l'inscription — sert de base aux restrictions de contenu liées à l'âge


class CustomerPublic(BaseModel):
    username:   str
    email:      Optional[str] = None
    role:       Role
    is_active:  bool
    date_of_birth: Optional[str] = None
    created_at: Optional[str] = None


class CustomerSelfUpdate(BaseModel):
    email:          Optional[str] = None
    date_of_birth:   Optional[str] = None


class CustomerStatusUpdate(BaseModel):
    is_active: bool


class CustomerAdminUpdate(BaseModel):
    email:          Optional[str] = None
    new_password:    Optional[str] = None
    date_of_birth:     Optional[str] = None


class CustomerAdminCreate(BaseModel):
    username:      str
    email:          Optional[str] = None
    date_of_birth:   str
    # Laisser vide génère un mot de passe aléatoire, révélé une seule fois dans la réponse —
    # utile quand l'admin crée un compte pour un client qui n'a pas pu s'inscrire lui-même.
    password: Optional[str] = None
