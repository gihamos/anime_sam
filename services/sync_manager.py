"""
Gestionnaire de synchronisation d'épisodes.

Contraintes :
  - Un slug ne peut pas être synchronisé deux fois en même temps
  - Cooldown de 7h entre deux syncs du même slug
  - MAX_CONCURRENT syncs simultanées maximum
  - Progression diffusée en temps réel aux abonnés WebSocket

Commandes disponibles :
  - pause(slug)   → met en attente après l'item en cours
  - resume(slug)  → reprend l'exécution
  - cancel(slug)  → annule après l'item en cours
"""

import asyncio
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

from utils.logger import logger

MAX_CONCURRENT = 3
COOLDOWN_HOURS = 7


class SyncManager:

    def __init__(self):
        self._active:      dict[str, asyncio.Task]                             = {}
        self._last_sync:   dict[str, datetime]                                 = {}
        self._subscribers: dict[str, dict[str, asyncio.Queue[Optional[dict]]]] = {}
        self._paused:      set[str]                                             = set()
        self._cancel:      dict[str, bool]                                     = {}

    # ------------------------------------------------------------------
    # Vérification
    # ------------------------------------------------------------------

    def is_active(self, slug: str) -> bool:
        return slug in self._active

    def is_paused(self, slug: str) -> bool:
        return slug in self._paused

    def can_start(self, slug: str) -> tuple[bool, Optional[str]]:
        if slug in self._active:
            return False, "already_syncing"
        if len(self._active) >= MAX_CONCURRENT:
            return False, f"max_concurrent_reached:{MAX_CONCURRENT}"
        if slug in self._last_sync:
            elapsed = datetime.now(timezone.utc) - self._last_sync[slug]
            if elapsed < timedelta(hours=COOLDOWN_HOURS):
                remaining = int((timedelta(hours=COOLDOWN_HOURS) - elapsed).total_seconds())
                return False, f"cooldown:{remaining}"
        return True, None

    def status(self, slug: str) -> dict:
        if slug in self._active:
            paused = slug in self._paused
            return {
                "status":      "paused" if paused else "syncing",
                "slug":        slug,
                "paused":      paused,
                "cancelling":  self._cancel.get(slug, False),
            }
        if slug in self._last_sync:
            last      = self._last_sync[slug]
            elapsed   = datetime.now(timezone.utc) - last
            remaining = max(0, int((timedelta(hours=COOLDOWN_HOURS) - elapsed).total_seconds()))
            return {
                "status":               "idle",
                "slug":                 slug,
                "last_sync":            last.isoformat(),
                "cooldown_remaining_s": remaining,
                "cooldown_active":      remaining > 0,
            }
        return {"status": "never_synced", "slug": slug}

    def active_syncs(self) -> list[str]:
        return list(self._active.keys())

    # ------------------------------------------------------------------
    # Commandes de contrôle
    # ------------------------------------------------------------------

    async def pause(self, slug: str) -> bool:
        if slug not in self._active:
            return False
        self._paused.add(slug)
        await self.broadcast(slug, {
            "type":    "paused",
            "slug":    slug,
            "message": "Pause demandée — en attente de la fin de l'item en cours…",
        })
        logger.info(f"SyncManager : pause de '{slug}'")
        return True

    async def resume(self, slug: str) -> bool:
        if slug not in self._active:
            return False
        self._paused.discard(slug)
        await self.broadcast(slug, {"type": "resumed", "slug": slug})
        logger.info(f"SyncManager : reprise de '{slug}'")
        return True

    async def cancel(self, slug: str) -> bool:
        if slug not in self._active:
            return False
        self._cancel[slug] = True
        self._paused.discard(slug)
        await self.broadcast(slug, {
            "type":    "cancelling",
            "slug":    slug,
            "message": "Annulation en cours — l'item actuel se terminera avant l'arrêt…",
        })
        logger.info(f"SyncManager : annulation de '{slug}'")
        return True

    # ------------------------------------------------------------------
    # Pub/sub WebSocket
    # ------------------------------------------------------------------

    def subscribe(self, slug: str) -> tuple[str, asyncio.Queue]:
        conn_id = str(uuid.uuid4())
        q: asyncio.Queue = asyncio.Queue()
        self._subscribers.setdefault(slug, {})[conn_id] = q
        return conn_id, q

    def unsubscribe(self, slug: str, conn_id: str) -> None:
        subs = self._subscribers.get(slug)
        if subs:
            subs.pop(conn_id, None)
            if not subs:
                self._subscribers.pop(slug, None)

    async def broadcast(self, slug: str, event: dict) -> None:
        for q in list(self._subscribers.get(slug, {}).values()):
            await q.put(event)

    async def _close_queues(self, slug: str) -> None:
        for q in list(self._subscribers.get(slug, {}).values()):
            await q.put(None)

    # ------------------------------------------------------------------
    # Cycle de vie
    # ------------------------------------------------------------------

    def register(self, slug: str, task: asyncio.Task) -> None:
        self._active[slug] = task

    def _finish(self, slug: str) -> None:
        self._active.pop(slug, None)
        self._paused.discard(slug)
        self._cancel.pop(slug, None)
        self._last_sync[slug] = datetime.now(timezone.utc)
        logger.info(f"SyncManager : sync de '{slug}' terminée")

    async def run_sync(self, slug: str, triggered_by: str = "manual") -> None:
        """Coroutine principale. Wrappée dans asyncio.create_task()."""
        from services.catalogue_service import sync_content_bg

        self._cancel[slug] = False
        started_at  = datetime.now(timezone.utc)
        final_status = "error"
        total_items  = 0

        async def wait_if_paused() -> bool:
            while slug in self._paused:
                if self._cancel.get(slug):
                    return False
                await asyncio.sleep(0.3)
            return not self._cancel.get(slug, False)

        await self.broadcast(slug, {"type": "started", "slug": slug})
        try:
            total_items = await sync_content_bg(
                slug,
                broadcast=lambda e: self.broadcast(slug, e),
                wait_if_paused=wait_if_paused,
            )
            if self._cancel.get(slug):
                final_status = "cancelled"
                await self.broadcast(slug, {
                    "type":    "cancelled",
                    "slug":    slug,
                    "message": "Synchronisation annulée par l'utilisateur.",
                })
            else:
                final_status = "completed"
                await self.broadcast(slug, {
                    "type":           "completed",
                    "slug":           slug,
                    "total_episodes": total_items,
                })
        except asyncio.CancelledError:
            final_status = "cancelled"
            await self.broadcast(slug, {
                "type": "cancelled", "slug": slug, "message": "Tâche interrompue.",
            })
        except Exception as exc:
            final_status = "error"
            logger.exception(f"SyncManager : erreur sur '{slug}'")
            await self.broadcast(slug, {
                "type": "error", "slug": slug, "message": str(exc),
            })
        finally:
            self._finish(slug)
            await self._close_queues(slug)
            # Écriture de l'historique
            try:
                import db.sync_history_repository as hist_repo
                ended_at = datetime.now(timezone.utc)
                duration = int((ended_at - started_at).total_seconds())
                await hist_repo.add_entry({
                    "slug":         slug,
                    "triggered_by": triggered_by,
                    "started_at":   started_at.isoformat(),
                    "ended_at":     ended_at.isoformat(),
                    "duration_s":   duration,
                    "status":       final_status,
                    "total_items":  total_items,
                })
            except Exception as he:
                logger.error(f"SyncManager : impossible d'écrire l'historique : {he}")


sync_manager = SyncManager()
