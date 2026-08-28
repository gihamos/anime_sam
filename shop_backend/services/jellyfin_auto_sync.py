"""
Synchronisation Jellyfin automatique, configurable depuis l'admin boutique — décision
explicite de l'utilisateur (activer/désactiver, intervalle en heures). Indépendante de
l'éventuel job équivalent côté anime_sam lui-même (les deux peuvent coexister sans risque :
un rafraîchissement Jellyfin est une opération sans effet de bord à répéter).

Le scheduler lui-même appartient à main.py (une seule instance APScheduler pour tout
shop_backend) — injecté ici via init() plutôt qu'importé directement, pour éviter un import
circulaire (main.py importe api.routes.admin, qui a besoin de ce module).
"""

from __future__ import annotations

from typing import Optional

import db.settings_repository as settings_repo
import services.anime_sam_client as anime_sam_client
from utils.logger import logger

JOB_ID = "jellyfin_auto_sync"
_SETTING_KEY = "jellyfin_auto_sync"
_DEFAULT_INTERVAL_HOURS = 6
_DEFAULT_CONFIG = {"enabled": False, "interval_hours": _DEFAULT_INTERVAL_HOURS}

_scheduler: Optional[object] = None


def init(scheduler) -> None:
    global _scheduler
    _scheduler = scheduler


async def get_config() -> dict:
    return await settings_repo.get_setting(_SETTING_KEY, _DEFAULT_CONFIG)


async def _run_auto_sync() -> None:
    ok = await anime_sam_client.trigger_jellyfin_sync()
    if not ok:
        logger.warning("shop_backend : échec de la synchronisation Jellyfin automatique planifiée")


def _apply_schedule(config: dict) -> None:
    if _scheduler is None:
        return
    if _scheduler.get_job(JOB_ID):
        _scheduler.remove_job(JOB_ID)
    if config.get("enabled"):
        interval_hours = max(1, int(config.get("interval_hours") or _DEFAULT_INTERVAL_HOURS))
        _scheduler.add_job(
            _run_auto_sync, "interval", hours=interval_hours,
            id=JOB_ID, replace_existing=True, misfire_grace_time=1800,
        )


async def start() -> None:
    """Appelé au démarrage de l'app — programme (ou non) le job selon la config déjà
    enregistrée en base, pour que le réglage choisi survive un redémarrage du service."""
    _apply_schedule(await get_config())


async def set_config(enabled: bool, interval_hours: int) -> dict:
    config = {"enabled": enabled, "interval_hours": interval_hours}
    await settings_repo.set_setting(_SETTING_KEY, config)
    _apply_schedule(config)
    return config
