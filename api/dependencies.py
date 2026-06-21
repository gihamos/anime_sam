"""
Dépendances FastAPI pour l'authentification et les autorisations.

Hiérarchie des permissions :
  admin  → tous les droits
  user   → permissions directes + groupes
  client → permissions directes (pas de groupes pour l'instant)

EffectiveAccess (_eff) est calculé une fois par requête et attaché à l'utilisateur.
"""

from dataclasses import dataclass, field
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
        JWT_SECRET, algorithm=ALGORITHM,
    )


# ---------------------------------------------------------------------------
# Vérification du blocage
# ---------------------------------------------------------------------------

def _check_not_blocked(doc: dict) -> None:
    if not doc.get("is_blocked", False):
        return
    blocked_until = doc.get("blocked_until")
    if blocked_until:
        until_dt = datetime.fromisoformat(blocked_until)
        if until_dt <= datetime.now(timezone.utc):
            return  # blocage temporaire expiré
    reason = doc.get("blocked_reason") or "Compte bloqué par un administrateur"
    raise HTTPException(status_code=403, detail=f"Accès bloqué : {reason}")


# ---------------------------------------------------------------------------
# Résolution des accès effectifs (fusion user + groupes)
# ---------------------------------------------------------------------------

@dataclass
class EffectiveAccess:
    is_admin:      bool       = False
    can_sync:      bool       = False
    can_delete:    bool       = False
    can_refresh:   bool       = False
    can_download:  bool       = True    # téléchargement global autorisé
    allowed_slugs: set        = field(default_factory=set)   # slugs spécifiques
    genre_access:  set        = field(default_factory=set)   # genres → accès à tous leurs catalogues
    cat_content:   dict       = field(default_factory=dict)  # slug → {saisons,films,scans}
    dl_forbidden:  set        = field(default_factory=set)   # slugs interdits au téléchargement
    dl_quota:      dict       = field(default_factory=dict)  # quota téléchargement (groupe)
    quota:         dict       = field(default_factory=dict)  # quota de synchronisation


async def resolve_effective_access(user: dict) -> EffectiveAccess:
    if user.get("role") == "admin":
        return EffectiveAccess(
            is_admin=True, can_sync=True, can_delete=True, can_refresh=True,
        )

    perms = user.get("permissions", {})
    acc = EffectiveAccess(
        can_sync      = bool(perms.get("can_sync",    False)),
        can_delete    = bool(perms.get("can_delete",  False)),
        can_refresh   = bool(perms.get("can_refresh", False)),
        can_download  = bool(perms.get("can_download", True)),
        allowed_slugs = set(perms.get("allowed_catalogues", [])),
        cat_content   = dict(perms.get("catalogue_content", {})),
        dl_forbidden  = set(perms.get("download_forbidden_slugs", [])),
        quota         = dict(perms.get("quota", {})),
    )

    group_ids = user.get("groups", [])
    if group_ids:
        import db.groups_repository as groups_repo
        groups = await groups_repo.find_by_ids(group_ids)
        for g in groups:
            gp = g.get("permissions", {})
            acc.can_sync    = acc.can_sync    or bool(gp.get("can_sync",    False))
            acc.can_delete  = acc.can_delete  or bool(gp.get("can_delete",  False))
            acc.can_refresh = acc.can_refresh or bool(gp.get("can_refresh", False))

            # Un groupe peut interdire le téléchargement (logique AND)
            if not gp.get("can_download", True):
                acc.can_download = False
            # Cumul des slugs interdits
            acc.dl_forbidden |= set(gp.get("download_forbidden_slugs", []))
            # Premier quota téléchargement de groupe activé (si aucun quota user)
            gdl_q = gp.get("download_quota", {})
            if gdl_q.get("enabled") and not acc.dl_quota.get("enabled"):
                acc.dl_quota = gdl_q

            gtype = g.get("type")
            if gtype == "catalogue":
                for slug in g.get("catalogue_slugs", []):
                    acc.allowed_slugs.add(slug)
                acc.cat_content.update(g.get("catalogue_content", {}))
            elif gtype == "genre":
                for genre in g.get("genres", []):
                    acc.genre_access.add(genre.lower())

            # Quota de sync — prendre le premier activé
            gq = gp.get("quota", {})
            if gq.get("enabled") and not acc.quota.get("enabled"):
                acc.quota = gq

    return acc


async def _enrich_user(user: dict) -> dict:
    """Attache l'accès effectif (_eff) au dict utilisateur."""
    user = dict(user)
    user["_eff"] = await resolve_effective_access(user)
    return user


# ---------------------------------------------------------------------------
# Dépendances FastAPI
# ---------------------------------------------------------------------------

_oauth2_optional = OAuth2PasswordBearer(tokenUrl="/auth/login", auto_error=False)


async def _validate_token(token: str) -> dict:
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
    user = await _validate_token(token)
    return await _enrich_user(user)


async def get_optional_user(
    token: Optional[str] = Depends(_oauth2_optional),
) -> Optional[dict]:
    if not token:
        return None
    try:
        user = await _validate_token(token)
        return await _enrich_user(user)
    except HTTPException as e:
        if e.status_code == 403:
            raise  # compte bloqué → propager l'erreur (ne pas traiter comme anonyme)
        return None  # token invalide/expiré → traiter comme anonyme


async def require_admin(user: dict = Depends(get_current_user)) -> dict:
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return user


async def decode_ws_token(token: str) -> Optional[dict]:
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
            return await _enrich_user(doc)

        import db.user_repository as user_repo
        user = await user_repo.find_by_username(subject)
        if not user or not user.get("is_active", True):
            return None
        try:
            _check_not_blocked(user)
        except HTTPException:
            return None
        return await _enrich_user(user)
    except JWTError:
        return None


# ---------------------------------------------------------------------------
# Vérificateurs de permissions (utilisent _eff si disponible)
# ---------------------------------------------------------------------------

def _eff(user: dict) -> EffectiveAccess:
    e = user.get("_eff")
    if e and isinstance(e, EffectiveAccess):
        return e
    # Fallback si _eff absent (ne devrait pas arriver avec get_current_user)
    perms = user.get("permissions", {})
    return EffectiveAccess(
        is_admin    = user.get("role") == "admin",
        can_sync    = bool(perms.get("can_sync",    False)),
        can_delete  = bool(perms.get("can_delete",  False)),
        can_refresh = bool(perms.get("can_refresh", False)),
        allowed_slugs = set(perms.get("allowed_catalogues", [])),
        quota = dict(perms.get("quota", {})),
    )


def check_can_sync(user: dict) -> None:
    e = _eff(user)
    if not e.is_admin and not e.can_sync:
        raise HTTPException(403, "Permission 'can_sync' requise")


def check_can_delete(user: dict) -> None:
    e = _eff(user)
    if not e.is_admin and not e.can_delete:
        raise HTTPException(403, "Permission 'can_delete' requise")


def check_can_refresh(user: dict) -> None:
    e = _eff(user)
    if not e.is_admin and not e.can_refresh:
        raise HTTPException(403, "Permission 'can_refresh' requise")


async def check_catalogue_access(user: dict, slug: str) -> None:
    """
    Vérifie que l'utilisateur peut accéder à ce slug.
    Prend en compte : permissions directes + groupes catalogue + groupes genre.
    """
    e = _eff(user)
    if e.is_admin:
        return

    # Pas de restriction explicite → accès total
    if not e.allowed_slugs and not e.genre_access:
        return

    if slug in e.allowed_slugs:
        return

    if e.genre_access:
        import db.repository as repo
        doc = await repo.find_by_slug(slug)
        if doc:
            cat_genres = {g.lower() for g in doc.get("genres", [])}
            if cat_genres & e.genre_access:
                return

    raise HTTPException(403, f"Accès non autorisé au catalogue '{slug}'")


async def check_quota(user: dict) -> None:
    """Lève 429 si le quota de synchronisation est atteint."""
    e = _eff(user)
    if e.is_admin:
        return
    quota = e.quota or {}
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
            detail=f"Quota de synchronisation atteint ({current}/{max_syncs} par {period})",
        )


async def increment_quota(user: dict) -> None:
    e = _eff(user)
    if e.is_admin:
        return
    quota = e.quota or {}
    if not quota.get("enabled", False):
        return
    period    = quota.get("period", "month")
    entity_id = user.get("username") or user.get("client_id", "")
    if not entity_id:
        return
    import db.usage_repository as usage_repo
    await usage_repo.increment(entity_id, period)
