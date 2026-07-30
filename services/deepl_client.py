"""
Client DeepL minimal (POST httpx direct, pas de SDK — cohérent avec le style du projet).

Sert uniquement de repli : le synopsis anime-sama.to, déjà en français, est toujours
prioritaire. DeepL n'est appelé que si ce synopsis est absent, pour traduire la
description anglaise fournie par AniList — une seule fois au moment de l'enrichissement,
jamais à la volée sur une requête utilisateur.

Si DEEPL_API_KEY est absente/invalide ou que l'appel échoue : log + None, jamais
d'exception (le synopsis anglais brut reste alors utilisé en dernier recours).
"""

from typing import Optional

import httpx

from params import DEEPL_API_KEY, DEEPL_API_URL
from utils.logger import logger


async def translate_to_fr(text: str) -> Optional[str]:
    if not DEEPL_API_KEY or not text:
        return None
    try:
        async with httpx.AsyncClient() as c:
            r = await c.post(
                DEEPL_API_URL,
                headers={"Authorization": f"DeepL-Auth-Key {DEEPL_API_KEY}"},
                json={"text": [text], "target_lang": "FR"},
                timeout=15,
            )
    except Exception as exc:
        logger.warning(f"DeepL : erreur réseau — {exc}")
        return None

    if r.status_code != 200:
        logger.warning(f"DeepL : échec traduction (HTTP {r.status_code})")
        return None

    translations = r.json().get("translations", [])
    return translations[0]["text"] if translations else None
