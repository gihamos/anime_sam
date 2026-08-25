"""
Authentification du service shop_backend — entièrement indépendante d'anime_sam.

Aucune fonction ici n'importe quoi que ce soit du package `anime_sam` (api/dependencies.py,
db/user_repository.py, etc.) : secret JWT distinct (SHOP_JWT_SECRET), collection Mongo
distincte (customers, dans la base anime_sama_shop), rôles distincts (customer|admin). Un
token émis ici n'est jamais valide sur l'API anime_sam et inversement.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt as _bcrypt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt

from params import SHOP_JWT_SECRET, SHOP_JWT_EXPIRE_MINUTES, SHOP_JWT_REFRESH_EXPIRE_DAYS

ALGORITHM     = "HS256"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


def hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode("utf-8"), _bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    return _bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))


def create_access_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=SHOP_JWT_EXPIRE_MINUTES)
    return jwt.encode({"sub": username, "exp": expire}, SHOP_JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(username: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=SHOP_JWT_REFRESH_EXPIRE_DAYS)
    return jwt.encode(
        {"sub": username, "type": "refresh", "exp": expire},
        SHOP_JWT_SECRET, algorithm=ALGORITHM,
    )


def decode_refresh_token(token: str) -> Optional[str]:
    try:
        payload = jwt.decode(token, SHOP_JWT_SECRET, algorithms=[ALGORITHM])
        if payload.get("type") != "refresh":
            return None
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_customer(token: str = Depends(oauth2_scheme)) -> dict:
    exc = HTTPException(
        status_code=401,
        detail="Token invalide ou expiré",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SHOP_JWT_SECRET, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username or payload.get("type") == "refresh":
            raise exc
    except JWTError:
        raise exc

    import db.customers_repository as customers_repo
    customer = await customers_repo.find_by_username(username)
    if not customer or not customer.get("is_active", True):
        raise exc
    return customer


async def require_admin(customer: dict = Depends(get_current_customer)) -> dict:
    if customer.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Accès réservé aux administrateurs")
    return customer
