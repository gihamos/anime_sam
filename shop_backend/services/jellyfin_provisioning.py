"""
Provisioning des comptes Jellyfin clients — appelé par services/billing_service.py en
réaction aux événements d'abonnement (activation, annulation, expiration...).

Authentification par clé d'API dédiée (X-Emby-Token), générée une seule fois via
POST /Auth/Keys après authentification admin (voir README / procédure de setup) — jamais de
réauthentification username/password au runtime.

Noms de champs `UserPolicy` vérifiés en conditions réelles contre l'instance Jellyfin de
production (version 10.11.11) avant l'écriture de ce module : EnabledFolders,
EnableAllFolders, EnableContentDownloading, MaxActiveSessions, IsDisabled — cycle de vie
complet (création, mot de passe, policy, désactivation, suppression) testé de bout en bout
sur un compte jetable.

Contrat identique aux autres clients externes du projet (cf. anime_sam/services/*.py) :
ne lève jamais d'exception vers l'appelant, retourne None/False en cas d'échec et logue.
"""

from __future__ import annotations

import secrets
from typing import Optional

import httpx

from params import JELLYFIN_BASE_URL, JELLYFIN_API_KEY
from utils.logger import logger

_HEADERS = {"X-Emby-Token": JELLYFIN_API_KEY}
_TIMEOUT = 15


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(base_url=JELLYFIN_BASE_URL, headers=_HEADERS, timeout=_TIMEOUT)


def generate_password() -> str:
    return secrets.token_urlsafe(12)


async def create_user(username: str) -> Optional[tuple[str, str]]:
    """Crée un compte Jellyfin désactivé par défaut (aucun accès tant que
    set_library_access n'a pas été appelé). Retourne (jellyfin_user_id, mot_de_passe) ou None."""
    password = generate_password()
    try:
        async with _client() as c:
            r = await c.post("/Users/New", json={"Name": username})
            if r.status_code != 200:
                logger.warning(f"Jellyfin : échec création utilisateur '{username}' — {r.status_code} {r.text}")
                return None
            jellyfin_user_id = r.json()["Id"]

            r2 = await c.post(f"/Users/{jellyfin_user_id}/Password", json={
                "CurrentPw": "", "NewPw": password,
            })
            if r2.status_code not in (200, 204):
                logger.warning(f"Jellyfin : mot de passe non défini pour '{username}' — {r2.status_code}")
    except Exception as exc:
        logger.warning(f"Jellyfin : erreur réseau création utilisateur '{username}' — {exc}")
        return None

    logger.info(f"Jellyfin : compte '{username}' créé (id={jellyfin_user_id})")
    return jellyfin_user_id, password


async def set_library_access(
    jellyfin_user_id: str,
    folder_ids: list[str],
    max_devices: int,
    allow_downloads: bool,
    enabled: bool,
) -> bool:
    """Applique l'accès bibliothèques/appareils/téléchargement. Jellyfin ne fusionne pas les
    policies partielles : on récupère la policy actuelle, on la mute, on la renvoie entière."""
    try:
        async with _client() as c:
            r = await c.get(f"/Users/{jellyfin_user_id}")
            if r.status_code != 200:
                logger.warning(f"Jellyfin : utilisateur {jellyfin_user_id} introuvable — {r.status_code}")
                return False
            policy = r.json()["Policy"]

            policy["IsDisabled"]               = not enabled
            policy["EnableAllFolders"]         = False
            policy["EnabledFolders"]           = folder_ids if enabled else []
            policy["EnableContentDownloading"] = allow_downloads and enabled
            policy["MaxActiveSessions"]        = max_devices if enabled else 0

            r2 = await c.post(f"/Users/{jellyfin_user_id}/Policy", json=policy)
            if r2.status_code not in (200, 204):
                logger.warning(f"Jellyfin : échec mise à jour policy {jellyfin_user_id} — {r2.status_code} {r2.text}")
                return False
    except Exception as exc:
        logger.warning(f"Jellyfin : erreur réseau policy {jellyfin_user_id} — {exc}")
        return False

    return True


async def enable_user(jellyfin_user_id: str, folder_ids: list[str], max_devices: int, allow_downloads: bool) -> bool:
    return await set_library_access(jellyfin_user_id, folder_ids, max_devices, allow_downloads, enabled=True)


async def disable_user(jellyfin_user_id: str) -> bool:
    """Désactive le compte et vide son accès, sans le supprimer — préserve l'historique de
    visionnage en cas de réabonnement ultérieur."""
    return await set_library_access(jellyfin_user_id, [], 0, False, enabled=False)


async def delete_user(jellyfin_user_id: str) -> bool:
    """Suppression définitive — réservée à une action admin explicite, pas au cycle de vie
    normal d'un abonnement (préférer disable_user)."""
    try:
        async with _client() as c:
            r = await c.delete(f"/Users/{jellyfin_user_id}")
            return r.status_code in (200, 204)
    except Exception as exc:
        logger.warning(f"Jellyfin : erreur réseau suppression {jellyfin_user_id} — {exc}")
        return False


async def list_library_folders() -> list[dict]:
    """GET /Library/VirtualFolders — alimente le sélecteur de bibliothèques du formulaire
    admin de création de palier. Retourne [{"id": ..., "name": ..., "type": ...}]."""
    try:
        async with _client() as c:
            r = await c.get("/Library/VirtualFolders")
            if r.status_code != 200:
                logger.warning(f"Jellyfin : échec récupération des bibliothèques — {r.status_code}")
                return []
            return [
                {"id": f.get("ItemId"), "name": f.get("Name"), "type": f.get("CollectionType")}
                for f in r.json()
            ]
    except Exception as exc:
        logger.warning(f"Jellyfin : erreur réseau récupération des bibliothèques — {exc}")
        return []
