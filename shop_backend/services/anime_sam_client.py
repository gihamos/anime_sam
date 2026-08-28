"""
Client pour l'API anime_sam elle-même — utilisé UNIQUEMENT pour le raccourci "Synchroniser
Jellyfin" de l'admin boutique (décision explicite de l'utilisateur : shop_backend reste par
ailleurs totalement indépendant d'anime_sam, aucun autre appel vers son API — voir le plan de
commercialisation). La synchronisation existe déjà côté anime_sam (manuelle et automatique
toutes les heures) ; ce module se contente de déclencher ce mécanisme existant à distance.

Authentification : identifiants d'un compte admin anime_sam dédié
(ANIME_SAM_ADMIN_USERNAME/PASSWORD dans .env), distincts de tout autre compte. Un login frais
à chaque appel plutôt qu'un token mis en cache — ce raccourci n'est pas appelé à haute
fréquence (action manuelle depuis l'admin), pas besoin de gérer un rafraîchissement.

Contrat identique aux autres clients externes du projet : ne lève jamais d'exception vers
l'appelant, retourne None/False en cas d'échec et logue.
"""

from __future__ import annotations

from typing import Optional

import httpx

from params import ANIME_SAM_API_URL, ANIME_SAM_ADMIN_USERNAME, ANIME_SAM_ADMIN_PASSWORD
from utils.logger import logger


async def _get_token() -> Optional[str]:
    if not ANIME_SAM_ADMIN_USERNAME or not ANIME_SAM_ADMIN_PASSWORD:
        logger.warning("anime_sam : ANIME_SAM_ADMIN_USERNAME/PASSWORD non configurés dans .env")
        return None
    try:
        async with httpx.AsyncClient(base_url=ANIME_SAM_API_URL, timeout=15) as c:
            r = await c.post("/auth/login", data={
                "username": ANIME_SAM_ADMIN_USERNAME, "password": ANIME_SAM_ADMIN_PASSWORD,
            })
            if r.status_code != 200:
                logger.warning(f"anime_sam : échec d'authentification pour le déclenchement du sync — {r.status_code}")
                return None
            return r.json()["access_token"]
    except Exception as exc:
        logger.warning(f"anime_sam : erreur réseau authentification — {exc}")
        return None


async def trigger_jellyfin_sync() -> bool:
    """Déclenche le même scan Jellyfin que le bouton de l'admin anime_sam."""
    token = await _get_token()
    if not token:
        return False
    try:
        async with httpx.AsyncClient(base_url=ANIME_SAM_API_URL, timeout=30) as c:
            r = await c.post("/admin/api/jellyfin/sync", headers={"Authorization": f"Bearer {token}"})
            if r.status_code != 200:
                logger.warning(f"anime_sam : échec déclenchement sync — {r.status_code} {r.text}")
                return False
            return bool(r.json().get("ok"))
    except Exception as exc:
        logger.warning(f"anime_sam : erreur réseau déclenchement sync — {exc}")
        return False


async def get_sync_status() -> Optional[dict]:
    """Retourne {"last_sync": iso|null}, ou None si le statut n'a pas pu être récupéré
    (identifiants absents, anime_sam injoignable...) — distinct de {"last_sync": null}, qui
    signifie qu'aucune synchronisation n'a encore eu lieu."""
    token = await _get_token()
    if not token:
        return None
    try:
        async with httpx.AsyncClient(base_url=ANIME_SAM_API_URL, timeout=15) as c:
            r = await c.get("/admin/api/jellyfin/sync-status", headers={"Authorization": f"Bearer {token}"})
            if r.status_code != 200:
                return None
            return r.json()
    except Exception as exc:
        logger.warning(f"anime_sam : erreur réseau statut sync — {exc}")
        return None
