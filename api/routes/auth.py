"""
Routes d'authentification et gestion des utilisateurs.

POST /auth/login                      → retourne un JWT (public)
GET  /auth/me                         → profil de l'utilisateur courant
POST /auth/register                   → crée un utilisateur (admin)
GET  /auth/users                      → liste tous les utilisateurs (admin)
PUT  /auth/users/{username}           → modifie rôle/permissions (admin)
DELETE /auth/users/{username}         → supprime un utilisateur (admin)

GET  /auth/oidc/providers             → fournisseurs OIDC configurés (public)
GET  /auth/oidc/authorize             → URL d'autorisation OIDC (public)
GET  /auth/oidc/callback              → callback OIDC (redirect depuis le fournisseur)
"""

import secrets as _secrets
import re
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel

from models.user import UserCreate, UserUpdate, UserPublic, UserInDB, Role
from api.dependencies import (
    get_current_user, require_admin,
    hash_password, verify_password, create_access_token, create_client_token,
)
import db.user_repository as user_repo
import db.clients_repository as clients_repo
from params import OIDC_ADMIN_REDIRECT

router = APIRouter(prefix="/auth", tags=["Authentification"])


class ClientTokenRequest(BaseModel):
    client_id:     str
    client_secret: str


# ---------------------------------------------------------------------------
# Login
# ---------------------------------------------------------------------------

@router.post("/login", summary="Connexion — retourne un JWT")
async def login(form: OAuth2PasswordRequestForm = Depends()):
    """
    Utilise le formulaire OAuth2 standard (username + password).
    Compatible avec le bouton **Authorize** de Swagger UI.
    """
    user = await user_repo.find_by_username(form.username)
    if not user or not verify_password(form.password, user.get("hashed_password", "")):
        raise HTTPException(status_code=401, detail="Identifiants incorrects")
    if not user.get("is_active", True):
        raise HTTPException(status_code=403, detail="Compte désactivé")

    token = create_access_token(user["username"])
    return {"access_token": token, "token_type": "bearer"}


@router.post("/client-token", summary="Token pour une application tierce (client_id + secret)")
async def client_token_endpoint(body: ClientTokenRequest):
    """
    Authentifie une application tierce via client_id + client_secret.
    Retourne un JWT Bearer utilisable sur tous les endpoints protégés.
    """
    doc = await clients_repo.find_by_client_id(body.client_id)
    if not doc or not verify_password(body.client_secret, doc.get("client_secret_hash", "")):
        raise HTTPException(status_code=401, detail="client_id ou client_secret invalide")
    if not doc.get("is_active", True):
        raise HTTPException(status_code=403, detail="Application désactivée")
    token = create_client_token(body.client_id)
    return {"access_token": token, "token_type": "bearer"}


# ---------------------------------------------------------------------------
# Profil courant
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserPublic, summary="Mon profil")
async def me(user: dict = Depends(get_current_user)):
    return user


# ---------------------------------------------------------------------------
# Gestion des utilisateurs (admin)
# ---------------------------------------------------------------------------

@router.post(
    "/register",
    response_model=UserPublic,
    status_code=201,
    summary="Créer un utilisateur (admin)",
)
async def register(body: UserCreate, _: dict = Depends(require_admin)):
    if await user_repo.find_by_username(body.username):
        raise HTTPException(409, f"L'utilisateur '{body.username}' existe déjà")

    user_doc = UserInDB(
        username        = body.username,
        email           = body.email,
        role            = body.role,
        hashed_password = hash_password(body.password),
        is_active       = True,
        permissions     = body.permissions,
    ).model_dump()

    await user_repo.create_user(user_doc)
    return user_doc


@router.get(
    "/users",
    response_model=list[UserPublic],
    summary="Liste des utilisateurs (admin)",
)
async def list_users(_: dict = Depends(require_admin)):
    return await user_repo.list_users()


@router.put(
    "/users/{username}",
    response_model=UserPublic,
    summary="Modifier un utilisateur (admin)",
)
async def update_user(
    username: str,
    body:     UserUpdate,
    admin:    dict = Depends(require_admin),
):
    if username == admin["username"] and body.role is not None and body.role != "admin":
        raise HTTPException(400, "Impossible de retirer son propre rôle admin")

    existing = await user_repo.find_by_username(username)
    if not existing:
        raise HTTPException(404, f"Utilisateur '{username}' introuvable")

    fields: dict = {}
    if body.email          is not None: fields["email"]          = body.email
    if body.is_active      is not None: fields["is_active"]      = body.is_active
    if body.is_blocked     is not None: fields["is_blocked"]     = body.is_blocked
    if body.blocked_reason is not None: fields["blocked_reason"] = body.blocked_reason
    if body.blocked_until  is not None: fields["blocked_until"]  = body.blocked_until
    if body.role           is not None: fields["role"]           = body.role
    if body.permissions    is not None: fields["permissions"]    = body.permissions.model_dump()
    if body.password       is not None: fields["hashed_password"] = hash_password(body.password)
    if body.groups         is not None: fields["groups"]         = body.groups

    if fields:
        await user_repo.update_user(username, fields)

    updated = await user_repo.find_by_username(username)
    return updated


@router.delete(
    "/users/{username}",
    status_code=204,
    summary="Supprimer un utilisateur (admin)",
)
async def delete_user(username: str, admin: dict = Depends(require_admin)):
    if username == admin["username"]:
        raise HTTPException(400, "Impossible de supprimer son propre compte")

    deleted = await user_repo.delete_user(username)
    if not deleted:
        raise HTTPException(404, f"Utilisateur '{username}' introuvable")


# ---------------------------------------------------------------------------
# OpenID Connect
# ---------------------------------------------------------------------------

@router.get("/oidc/providers", summary="Fournisseurs OIDC configurés (public)")
async def list_oidc_providers():
    from services.oidc_service import list_providers
    return list_providers()


@router.get("/oidc/authorize", summary="URL d'autorisation OIDC")
async def oidc_authorize(provider: str = Query(..., description="ID du fournisseur OIDC")):
    from services.oidc_service import get_authorization_url
    try:
        state = _secrets.token_urlsafe(16)
        url = await get_authorization_url(provider, state)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(502, f"Erreur lors de la récupération de l'URL : {e}")
    return {"url": url, "provider": provider}


@router.get("/oidc/callback", summary="Callback OIDC (redirect fournisseur → app)")
async def oidc_callback(
    code:     str = Query(...),
    state:    str = Query(default=""),
    provider: str = Query(default=""),
    error:    str = Query(default=""),
):
    if error:
        return RedirectResponse(f"{OIDC_ADMIN_REDIRECT}/#oidc_error={error}")

    # L'état encode "{provider}:{nonce}" — extraire le provider si absent
    if not provider and ":" in state:
        provider = state.split(":")[0]

    if not provider:
        return RedirectResponse(f"{OIDC_ADMIN_REDIRECT}/#oidc_error=missing_provider")

    from services.oidc_service import exchange_code
    try:
        profile = await exchange_code(provider, code)
    except Exception as e:
        return RedirectResponse(f"{OIDC_ADMIN_REDIRECT}/#oidc_error=exchange_failed")

    oidc_sub = profile.get("sub", "")
    email    = profile.get("email", "")
    name     = profile.get("name", "")

    # Chercher un utilisateur existant par oidc_sub + provider
    from db.connection import get_db
    db = get_db()
    user = await db.users.find_one(
        {"oidc_sub": oidc_sub, "oidc_provider": provider},
        {"_id": 0}
    )

    if not user and email:
        # Essayer de lier à un compte existant par email
        user = await db.users.find_one({"email": email}, {"_id": 0})
        if user:
            await user_repo.update_user(user["username"], {
                "oidc_sub": oidc_sub, "oidc_provider": provider
            })

    if not user:
        # Créer un nouveau compte
        base = re.sub(r"[^a-z0-9_]", "", (email.split("@")[0] if email else name or "user").lower()) or "user"
        username = base
        suffix = 1
        while await user_repo.find_by_username(username):
            username = f"{base}{suffix}"; suffix += 1

        user_doc = UserInDB(
            username        = username,
            email           = email or None,
            role            = Role.USER,
            hashed_password = hash_password(_secrets.token_urlsafe(24)),
            is_active       = True,
            oidc_sub        = oidc_sub,
            oidc_provider   = provider,
        ).model_dump()
        await user_repo.create_user(user_doc)
        user = await user_repo.find_by_username(username)

    if not user.get("is_active", True):
        return RedirectResponse(f"{OIDC_ADMIN_REDIRECT}/#oidc_error=account_disabled")

    token = create_access_token(user["username"])
    return RedirectResponse(f"{OIDC_ADMIN_REDIRECT}/#token={token}")
