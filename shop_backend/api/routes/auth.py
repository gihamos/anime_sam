"""
Authentification des comptes shop_backend (clients + admin de la boutique).

POST /auth/register   → crée un compte client (public — c'est le formulaire d'inscription
                         de shop_app, pas une action admin)
POST /auth/login       → retourne access + refresh token
POST /auth/refresh     → renouvelle l'access token
GET  /auth/me          → profil du compte connecté
PUT  /auth/me/password → changer son mot de passe
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from models.customer import CustomerCreate, CustomerPublic, CustomerInDB, Role
from models.responses import TokenResponse, MessageResponse
from api.dependencies import (
    get_current_customer, hash_password, verify_password,
    create_access_token, create_refresh_token, decode_refresh_token,
)
import db.customers_repository as customers_repo

router = APIRouter(prefix="/auth", tags=["Authentification"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password:      str


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/register", response_model=CustomerPublic, status_code=201, summary="Créer un compte client")
async def register(body: CustomerCreate):
    if await customers_repo.find_by_username(body.username):
        raise HTTPException(409, f"Le compte '{body.username}' existe déjà")

    doc = CustomerInDB(
        username        = body.username,
        email           = body.email,
        role            = Role.CUSTOMER,
        hashed_password = hash_password(body.password),
        is_active       = True,
        created_at      = datetime.now(timezone.utc).isoformat(),
    ).model_dump()

    await customers_repo.create_customer(doc)
    return doc


@router.post("/login", response_model=TokenResponse, summary="Connexion — retourne un JWT")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    customer = await customers_repo.find_by_username(form.username)
    if not customer or not verify_password(form.password, customer.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    if not customer.get("is_active", True):
        raise HTTPException(status_code=403, detail="Compte désactivé")

    access  = create_access_token(customer["username"])
    refresh = create_refresh_token(customer["username"])
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.post("/refresh", response_model=TokenResponse, summary="Renouveler le token d'accès")
async def refresh_access_token(body: RefreshRequest):
    username = decode_refresh_token(body.refresh_token)
    if not username:
        raise HTTPException(status_code=401, detail="Refresh token invalide ou expiré")

    customer = await customers_repo.find_by_username(username)
    if not customer or not customer.get("is_active", True):
        raise HTTPException(status_code=401, detail="Compte introuvable ou inactif")

    access  = create_access_token(username)
    refresh = create_refresh_token(username)
    return {"access_token": access, "refresh_token": refresh, "token_type": "bearer"}


@router.get("/me", response_model=CustomerPublic, summary="Mon profil")
async def me(customer: dict = Depends(get_current_customer)):
    return customer


@router.put("/me/password", response_model=MessageResponse, summary="Changer mon mot de passe")
async def change_password(body: ChangePasswordRequest, customer: dict = Depends(get_current_customer)):
    if not verify_password(body.current_password, customer.get("hashed_password", "")):
        raise HTTPException(400, "Mot de passe actuel incorrect")
    if len(body.new_password) < 8:
        raise HTTPException(400, "Le nouveau mot de passe doit contenir au moins 8 caractères")

    await customers_repo.update_customer(customer["username"], {"hashed_password": hash_password(body.new_password)})
    return {"message": "Mot de passe mis à jour"}
