"""
Routes d'authentification et gestion des utilisateurs.

POST /auth/login                  → retourne un JWT (public)
GET  /auth/me                     → profil de l'utilisateur courant
POST /auth/register               → crée un utilisateur (admin)
GET  /auth/users                  → liste tous les utilisateurs (admin)
PUT  /auth/users/{username}       → modifie rôle/permissions (admin)
DELETE /auth/users/{username}     → supprime un utilisateur (admin)
"""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm

from models.user import UserCreate, UserUpdate, UserPublic, UserInDB
from api.dependencies import (
    get_current_user, require_admin,
    hash_password, verify_password, create_access_token,
)
import db.user_repository as user_repo

router = APIRouter(prefix="/auth", tags=["Authentification"])


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
    if body.email       is not None: fields["email"]       = body.email
    if body.is_active   is not None: fields["is_active"]   = body.is_active
    if body.role        is not None: fields["role"]        = body.role
    if body.permissions is not None: fields["permissions"] = body.permissions.model_dump()

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
