"""
Verrouillage global de l'API.

Quand l'API est verrouillée, toutes les requêtes sont rejetées (503)
sauf celles des administrateurs et la route /auth/login.

État persisté en DB (collection `settings`) et mis en cache en mémoire.
"""

_locked: bool = False
_reason: str  = ""


def is_locked() -> bool:
    return _locked


def get_state() -> dict:
    return {"locked": _locked, "reason": _reason}


async def load() -> None:
    """Appelé au démarrage pour restaurer l'état depuis la DB."""
    global _locked, _reason
    from db.settings_repository import get_setting
    _locked = bool(await get_setting("api_locked", False))
    _reason = str(await get_setting("api_lock_reason", "") or "")


async def set_state(locked: bool, reason: str = "") -> None:
    global _locked, _reason
    _locked = locked
    _reason = reason
    from db.settings_repository import set_setting
    await set_setting("api_locked", locked)
    await set_setting("api_lock_reason", reason)
