"""
Gestionnaire de synchronisation d'épisodes.

Contraintes :
  - Un slug ne peut pas être synchronisé deux fois en même temps
  - Cooldown de 7h entre deux syncs du même slug
  - MAX_CONCURRENT syncs simultanées maximum
  - Progression diffusée en temps réel aux abonnés WebSocket
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
        # slug → asyncio.Task en cours
        self._active:      dict[str, asyncio.Task]                  = {}
        # slug → datetime de fin de dernière sync
        self._last_sync:   dict[str, datetime]                      = {}
        # slug → {conn_id → asyncio.Queue}  (abonnés WebSocket)
        self._subscribers: dict[str, dict[str, asyncio.Queue[Optional[dict]]]] = {}

    # ------------------------------------------------------------------
    # Vérification des droits de démarrage
    # ------------------------------------------------------------------

    def is_active(self, slug: str) -> bool:
        return slug in self._active

    def can_start(self, slug: str) -> tuple[bool, Optional[str]]:
        """
        Retourne (peut_démarrer, raison_du_refus_ou_None).
        Raisons possibles :
          "already_syncing"
          "max_concurrent_reached"
          "cooldown:{secondes_restantes}"
        """
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
            return {"status": "syncing", "slug": slug}

        if slug in self._last_sync:
            last = self._last_sync[slug]
            elapsed   = datetime.now(timezone.utc) - last
            remaining = max(0, int((timedelta(hours=COOLDOWN_HOURS) - elapsed).total_seconds()))
            return {
                "status":              "idle",
                "slug":                slug,
                "last_sync":           last.isoformat(),
                "cooldown_remaining_s": remaining,
                "cooldown_active":     remaining > 0,
            }

        return {"status": "never_synced", "slug": slug}

    def active_syncs(self) -> list[str]:
        return list(self._active.keys())

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
        """Envoie le sentinel None pour fermer tous les abonnés."""
        for q in list(self._subscribers.get(slug, {}).values()):
            await q.put(None)

    # ------------------------------------------------------------------
    # Cycle de vie d'une sync
    # ------------------------------------------------------------------

    def register(self, slug: str, task: asyncio.Task) -> None:
        """À appeler juste après create_task(), avant le premier await."""
        self._active[slug] = task

    def _finish(self, slug: str) -> None:
        self._active.pop(slug, None)
        self._last_sync[slug] = datetime.now(timezone.utc)
        logger.info(f"SyncManager : sync de '{slug}' terminée")

    async def run_sync(self, slug: str) -> None:
        """
        Coroutine principale de synchronisation.
        Doit être wrappée dans asyncio.create_task().
        Appeler register(slug, task) AVANT d'attendre cette coroutine.
        """
        from services.catalogue_service import sync_content_bg

        await self.broadcast(slug, {"type": "started", "slug": slug})
        try:
            total = await sync_content_bg(
                slug,
                broadcast=lambda e: self.broadcast(slug, e),
            )
            await self.broadcast(slug, {
                "type":           "completed",
                "slug":           slug,
                "total_episodes": total,
            })
        except Exception as exc:
            logger.exception(f"SyncManager : erreur sur '{slug}'")
            await self.broadcast(slug, {
                "type":    "error",
                "slug":    slug,
                "message": str(exc),
            })
        finally:
            self._finish(slug)
            await self._close_queues(slug)


sync_manager = SyncManager()
