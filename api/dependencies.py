"""
Dépendances FastAPI pour l'authentification et les autorisations.

Hiérarchie des permissions :
  admin  → tous les droits
  user   → selon UserPermissions (can_sync, can_delete, can_refresh,
            allowed_catalogues)
  client → selon APIClientPermissions

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


def create_client_token(client_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRE_MINUTES)
    return jwt.encode(
        {"sub": client_id, "type": "client", "exp": expire},
        JWT_SECRET,
        algorithm=ALGORITHM,
    )


# ---------------------------------------------------------------------------
# Vérification du blocage
# ---------------------------------------------------------------------------

def _check_not_blocked(doc: dict) -> None:
    """Lève 403 si le compte est bloqué (et que le blocage temporaire n'a pas expiré)."""
    if not doc.get("is_blocked", False):
        return
    blocked_until = doc.get("blocked_until")
    if blocked_until:
        until_dt = datetime.fromisoformat(blocked_until)
        if until_dt <= datetime.now(timezone.utc):
            # Blocage temporaire expiré → on laisse passer
            return
    reason = doc.get("blocked_reason") or "Compte bloqué par un administrateur"
    raise HTTPException(status_code=403, detail=f"Accès bloqué : {reason}")


# ---------------------------------------------------------------------------
# Dépendances FastAPI
# ---------------------------------------------------------------------------

_oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _validate_token(token: str) -> dict:
    """Valide un JWT et retourne l'utilisateur ou le client API. Lève 401 si invalide."""
    exc = HTTPException(
        status_code=401,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            raise exc
    except JWTError:
        raise exc

    if payload.get("type") == "client":
        import db.clients_repository as clients_repo
        doc = await clients_repo.find_by_client_id(subject)
        if not doc or not doc.get("is_active", True):
            raise exc
        doc = dict(doc)
        doc.pop("client_secret_hash", None)
        doc["_id"] = str(doc.get("_id", ""))
        doc.setdefault("role", "client")
        _check_not_blocked(doc)
        return doc

    import db.user_repository as user_repo
    user = await user_repo.find_by_username(subject)
    if not user or not user.get("is_active", True):
        raise exc
    _check_not_blocked(user)
    return user


async def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    return await _validate_token(token)


async def get_optional_user(
    token: Optional[str] = Depends(_oauth2_optional),
) -> Optional[dict]:
    if not token:
        return None
    try:
        return await _validate_token(token)
    except HTTPException:
        return None


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


async def decode_ws_token(token: str) -> Optional[dict]:
    """Valide un JWT pour WebSocket. Supporte les tokens utilisateur et client API."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
        subject = payload.get("sub")
        if not subject:
            return None

        if payload.get("type") == "client":
            import db.clients_repository as clients_repo
            doc = await clients_repo.find_by_client_id(subject)
            if not doc or not doc.get("is_active", True):
                return None
            doc = dict(doc)
            doc.pop("client_secret_hash", None)
            doc["_id"] = str(doc.get("_id", ""))
            doc.setdefault("role", "client")
            try:
                _check_not_blocked(doc)
            except HTTPException:
                return None
            return doc

        import db.user_repository as user_repo
        user = await user_repo.find_by_username(subject)
        if not user or not user.get("is_active", True):
            return None
        try:
            _check_not_blocked(user)
        except HTTPException:
            return None
        return user
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Vérificateurs de permissions
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
    if user.get("role") == "admin":
        return
    allowed = user.get("permissions", {}).get("allowed_catalogues", [])
    if allowed and slug not in allowed:
        raise HTTPException(403, f"Accès non autorisé au catalogue '{slug}'")


async def check_quota(user: dict) -> None:
    """Lève 429 si le quota de synchronisation est atteint."""
    if user.get("role") == "admin":
        return
    perms = user.get("permissions", {})
    quota = perms.get("quota", {})
    if not quota.get("enabled", False):
        return
    max_syncs = int(quota.get("max_syncs", 0))
    if max_syncs <= 0:
        return
    period    = quota.get("period", "month")
    entity_id = user.get("username") or user.get("client_id", "")
    if not entity_id:
        return
    import db.usage_repository as usage_repo
    current = await usage_repo.get_count(entity_id, period)
    if current >= max_syncs:
        raise HTTPException(
            status_code=429,
            detail=f"Quota de synchronisation atteint ({current}/{max_syncs} par {period})"
        )


async def increment_quota(user: dict) -> None:
    """Incrémente le compteur de sync pour l'entité."""
    if user.get("role") == "admin":
        return
    perms = user.get("permissions", {})
    quota = perms.get("quota", {})
    if not quota.get("enabled", False):
        return
    period    = quota.get("period", "month")
    entity_id = user.get("username") or user.get("client_id", "")
    if not entity_id:
        return
    import db.usage_repository as usage_repo
    await usage_repo.increment(entity_id, period)
