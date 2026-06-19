"""
Dépendances FastAPI pour l'authentification et les autorisations.

Hiérarchie des permissions :
  admin  → tous les droits
  user   → selon UserPermissions (can_sync, can_delete, can_refresh,
            allowed_catalogues)

Utilisation dans les routes :
  user = Depends(get_current_user)   # authentifié
  user = Depends(require_admin)      # admin seulement
  puis : check_can_sync(user) / check_catalogue_access(user, slug)
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from params import JWT_SECRET, JWT_EXPIRE_MINUTES

ALGORITHM     = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# ---------------------------------------------------------------------------
# Utilitaires mot de passe / token
# ---------------------------------------------------------------------------

def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, JWT_SECRET, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Dépendances FastAPI
# ---------------------------------------------------------------------------

_oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _validate_token(token: str) -> dict:
    """Valide un JWT et retourne l'utilisateur. Lève 401 si invalide."""
    import db.user_repository as user_repo
    exc = HTTPException(
        status_code=401,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload  = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            raise exc
    except JWTError:
        raise exc
    user = await user_repo.find_by_username(username)
    if not user or not user.get("is_active", True):
        raise exc
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    """Retourne l'utilisateur courant. Lève 401 si token absent/invalide."""
    return await _validate_token(token)


async def get_optional_user(
    token: Optional[str] = Depends(_oauth2_optional),
) -> Optional[dict]:
    """Retourne l'utilisateur si authentifié, None sinon — sans lever d'erreur."""
    if not token:
        return None
    try:
        return await _validate_token(token)
    except HTTPException:
        return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    """Lève 403 si l'utilisateur n'est pas admin."""
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


async def decode_ws_token(token: str) -> Optional[dict]:
    """Valide un JWT pour WebSocket (token transmis en query param). Retourne None si invalide."""
    import db.user_repository as user_repo
    try:
        payload  = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        user = await user_repo.find_by_username(username)
        return user if (user and user.get("is_active", True)) else None
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Vérificateurs de permissions (à appeler inline dans les routes)
# ---------------------------------------------------------------------------

def check_can_sync(user: dict) -> None:
    perms = user.get("permissions", {})
    if user.get("role") != "admin" and not perms.get("can_sync", False):
        raise HTTPException(403, "Permission 'can_sync' requise")


def check_can_delete(user: dict) -> None:
    perms = user.get("permissions", {})
    if user.get("role") != "admin" and not perms.get("can_delete", False):
        raise HTTPException(403, "Permission 'can_delete' requise")


def check_can_refresh(user: dict) -> None:
    perms = user.get("permissions", {})
    if user.get("role") != "admin" and not perms.get("can_refresh", False):
        raise HTTPException(403, "Permission 'can_refresh' requise")


def check_catalogue_access(user: dict, slug: str) -> None:
    """Vérifie que l'utilisateur peut accéder au catalogue donné."""
    if user.get("role") == "admin":
        return
    allowed = user.get("permissions", {}).get("allowed_catalogues", [])
    if allowed and slug not in allowed:
        raise HTTPException(403, f"Accès non autorisé au catalogue '{slug}'")
