"""
Déclenche un scan de la bibliothèque Jellyfin pour que les nouveaux fichiers `.strm`
générés par le plugin anime-sama (voir jellyfin-plugin/) soient pris en compte sans
attendre le scan périodique interne de Jellyfin.

Authentification par clé d'API dédiée (X-Emby-Token) — même principe que
shop_backend/services/jellyfin_provisioning.py mais clé distincte : ce module gère la
bibliothèque (contenu), l'autre gère les comptes clients, deux préoccupations séparées
malgré la même instance Jellyfin cible.

Contrat identique aux autres clients externes du projet : ne lève jamais d'exception.
"""

from __future__ import annotations

import httpx

from params import JELLYFIN_BASE_URL, JELLYFIN_API_KEY
from utils.logger import logger

_HEADERS = {"X-Emby-Token": JELLYFIN_API_KEY}


async def refresh_library() -> bool:
    """POST /Library/Refresh — scan asynchrone côté Jellyfin (répond immédiatement, le
    scan se poursuit en arrière-plan sur le serveur)."""
    if not JELLYFIN_API_KEY:
        logger.warning("Jellyfin sync : JELLYFIN_API_KEY non configurée — synchronisation ignorée")
        return False
    try:
        async with httpx.AsyncClient(base_url=JELLYFIN_BASE_URL, headers=_HEADERS, timeout=15) as c:
            r = await c.post("/Library/Refresh")
            if r.status_code not in (200, 204):
                logger.warning(f"Jellyfin sync : échec du déclenchement — {r.status_code} {r.text}")
                return False
    except Exception as exc:
        logger.warning(f"Jellyfin sync : erreur réseau — {exc}")
        return False

    logger.info("Jellyfin sync : scan de bibliothèque déclenché")
    return True
