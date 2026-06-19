"""
Service de planification des synchronisations automatiques.

Utilise APScheduler (déjà présent comme dépendance).
Chaque programmation en DB génère un job APScheduler identifié par son _id MongoDB.
"""

import asyncio
from datetime import datetime, timezone, timedelta
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from utils.logger import logger

# Instance partagée — démarrée/arrêtée dans main.py
scheduler = AsyncIOScheduler(timezone="UTC")


# ---------------------------------------------------------------------------
# Calcul du déclencheur APScheduler depuis un dict de programmation
# ---------------------------------------------------------------------------

def _make_trigger(sched: dict):
    freq = sched.get("frequency", "daily")
    h    = int(sched.get("hour",   2))
    m    = int(sched.get("minute", 0))

    if freq == "daily":
        return CronTrigger(hour=h, minute=m, timezone="UTC")

    elif freq == "weekly":
        dow = sched.get("day_of_week", 0)   # 0=lun, 6=dim
        return CronTrigger(day_of_week=dow, hour=h, minute=m, timezone="UTC")

    elif freq == "biweekly":
        # Toutes les 2 semaines — IntervalTrigger avec start_date au prochain lundi (ou DOW)
        dow  = sched.get("day_of_week", 0)
        next_dt = _next_weekday(datetime.now(timezone.utc), dow, h, m)
        return IntervalTrigger(weeks=2, start_date=next_dt, timezone="UTC")

    elif freq == "monthly":
        dom = min(int(sched.get("day_of_month", 1)), 28)
        return CronTrigger(day=dom, hour=h, minute=m, timezone="UTC")

    elif freq == "custom":
        days = max(1, int(sched.get("interval_days", 7)))
        start = datetime.now(timezone.utc) + timedelta(days=days)
        start = start.replace(hour=h, minute=m, second=0, microsecond=0)
        return IntervalTrigger(days=days, start_date=start, timezone="UTC")

    return CronTrigger(hour=h, minute=m, timezone="UTC")


def _next_weekday(from_dt: datetime, dow: int, hour: int, minute: int) -> datetime:
    """Prochaine occurrence d'un jour de la semaine donné."""
    candidate = from_dt.replace(hour=hour, minute=minute, second=0, microsecond=0)
    days_ahead = (dow - from_dt.weekday()) % 7
    if days_ahead == 0 and candidate <= from_dt:
        days_ahead = 7
    return candidate + timedelta(days=days_ahead)


# ---------------------------------------------------------------------------
# Gestion des jobs
# ---------------------------------------------------------------------------

async def _run_schedule_job(slug: str, schedule_id: str) -> None:
    """Appelé par APScheduler à l'heure programmée."""
    from services.sync_manager import sync_manager

    if sync_manager.is_active(slug):
        logger.info(f"Scheduler : '{slug}' déjà en cours, skip")
        return

    can, reason = sync_manager.can_start(slug)
    if not can:
        logger.info(f"Scheduler : impossible de démarrer '{slug}' ({reason})")
        return

    logger.info(f"Scheduler : démarrage auto de '{slug}' (schedule {schedule_id})")
    task = asyncio.create_task(
        sync_manager.run_sync(slug, triggered_by=f"schedule:{schedule_id}")
    )
    sync_manager.register(slug, task)


def add_job(sched: dict) -> None:
    """Enregistre ou remplace un job APScheduler pour la programmation donnée."""
    sid     = sched["id"]
    trigger = _make_trigger(sched)
    scheduler.add_job(
        _run_schedule_job,
        trigger,
        id=sid,
        args=[sched["slug"], sid],
        replace_existing=True,
        name=f"auto-sync:{sched['slug']}",
        misfire_grace_time=3600,   # 1h de grâce en cas de démarrage tardif
    )
    logger.info(f"Scheduler : job ajouté '{sched['slug']}' ({sched.get('frequency')})")


def remove_job(sid: str) -> None:
    try:
        scheduler.remove_job(sid)
        logger.info(f"Scheduler : job supprimé {sid}")
    except Exception:
        pass


def pause_job(sid: str) -> None:
    try:
        scheduler.pause_job(sid)
    except Exception:
        pass


def resume_job(sid: str) -> None:
    try:
        scheduler.resume_job(sid)
    except Exception:
        pass


def get_next_run(sid: str) -> Optional[str]:
    """Retourne la prochaine date d'exécution (ISO) ou None."""
    try:
        job = scheduler.get_job(sid)
        if job and job.next_run_time:
            return job.next_run_time.isoformat()
    except Exception:
        pass
    return None


async def load_schedules_from_db() -> None:
    """Charge toutes les programmations actives depuis la DB au démarrage."""
    import db.schedules_repository as repo
    schedules = await repo.find_active()
    for sched in schedules:
        try:
            add_job(sched)
        except Exception as e:
            logger.error(f"Scheduler : impossible de charger {sched['id']}: {e}")
    logger.info(f"Scheduler : {len(schedules)} programmation(s) chargée(s)")
