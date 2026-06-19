"""
Service OIDC/OAuth2 pour l'authentification externe.
Supporte Google, GitHub (OAuth2) et tout fournisseur OIDC générique (Keycloak, Auth0, Authentik…).
"""

import httpx
from urllib.parse import urlencode
from typing import Optional
from params import OIDC_PROVIDERS, OIDC_CALLBACK_URL

_discovery_cache: dict[str, dict] = {}


async def _get_discovery(url: str) -> dict:
    if url in _discovery_cache:
        return _discovery_cache[url]
    async with httpx.AsyncClient() as c:
        r = await c.get(url, timeout=10, follow_redirects=True)
        r.raise_for_status()
        _discovery_cache[url] = r.json()
    return _discovery_cache[url]


def list_providers() -> list[dict]:
    return [{"id": k, "name": v["name"]} for k, v in OIDC_PROVIDERS.items()]


def get_provider(pid: str) -> dict:
    p = OIDC_PROVIDERS.get(pid)
    if not p:
        raise ValueError(f"Fournisseur OIDC '{pid}' non configuré")
    return p


async def get_authorization_url(provider_id: str, state: str) -> str:
    p = get_provider(provider_id)

    if provider_id == "github":
        return "https://github.com/login/oauth/authorize?" + urlencode({
            "client_id":    p["client_id"],
            "redirect_uri": OIDC_CALLBACK_URL,
            "scope":        "user:email read:user",
            "state":        f"github:{state}",
        })

    disc = await _get_discovery(p["discovery_url"])
    return disc["authorization_endpoint"] + "?" + urlencode({
        "client_id":     p["client_id"],
        "redirect_uri":  OIDC_CALLBACK_URL,
        "response_type": "code",
        "scope":         " ".join(p.get("scopes", ["openid", "email", "profile"])),
        "state":         f"{provider_id}:{state}",
    })


async def exchange_code(provider_id: str, code: str) -> dict:
    """Échange le code contre un token et retourne le profil normalisé."""
    p = get_provider(provider_id)

    if provider_id == "github":
        return await _github_exchange(p, code)

    disc = await _get_discovery(p["discovery_url"])
    async with httpx.AsyncClient() as c:
        r = await c.post(disc["token_endpoint"], data={
            "grant_type":   "authorization_code",
            "code":         code,
            "redirect_uri": OIDC_CALLBACK_URL,
            "client_id":    p["client_id"],
            "client_secret": p["client_secret"],
        }, headers={"Accept": "application/json"}, timeout=15)
        r.raise_for_status()
        tokens = r.json()

        r2 = await c.get(disc["userinfo_endpoint"], headers={
            "Authorization": f"Bearer {tokens['access_token']}"
        }, timeout=10)
        r2.raise_for_status()
        info = r2.json()

    return {
        "sub":      str(info.get("sub") or info.get("id") or ""),
        "email":    info.get("email"),
        "name":     info.get("name") or info.get("preferred_username") or info.get("login"),
        "picture":  info.get("picture"),
        "provider": provider_id,
    }


async def _github_exchange(p: dict, code: str) -> dict:
    async with httpx.AsyncClient() as c:
        r = await c.post("https://github.com/login/oauth/access_token", json={
            "client_id":     p["client_id"],
            "client_secret": p["client_secret"],
            "code":          code,
            "redirect_uri":  OIDC_CALLBACK_URL,
        }, headers={"Accept": "application/json"}, timeout=15)
        r.raise_for_status()
        tokens = r.json()
        access_token = tokens.get("access_token", "")

        r2 = await c.get("https://api.github.com/user", headers={
            "Authorization": f"Bearer {access_token}",
            "Accept":        "application/vnd.github+json",
        }, timeout=10)
        r2.raise_for_status()
        gh_user = r2.json()

        email: Optional[str] = gh_user.get("email")
        if not email:
            r3 = await c.get("https://api.github.com/user/emails", headers={
                "Authorization": f"Bearer {access_token}",
                "Accept":        "application/vnd.github+json",
            }, timeout=10)
            if r3.status_code == 200:
                emails = r3.json()
                primary = next((e for e in emails if e.get("primary") and e.get("verified")), None)
                email = primary["email"] if primary else None

    return {
        "sub":      str(gh_user["id"]),
        "email":    email,
        "name":     gh_user.get("name") or gh_user.get("login"),
        "picture":  gh_user.get("avatar_url"),
        "provider": "github",
    }
