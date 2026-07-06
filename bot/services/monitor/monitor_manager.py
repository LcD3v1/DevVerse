from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone

import httpx
from discord.ext import commands

from bot.services.monitor.hackathon_monitor import HackathonMonitor
from bot.services.monitor.jobs_monitor import JobsMonitor
from bot.services.monitor.notification_service import NotificationService
from bot.services.monitor.social_monitor import SocialMonitor


logger = logging.getLogger("devverse.monitor")


class MonitorManager:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = httpx.AsyncClient(timeout=20, follow_redirects=True)
        self.jobs = JobsMonitor(self.client)
        self.hackathons = HackathonMonitor(self.client)
        self.social = SocialMonitor(self.client)
        self.notifications = NotificationService(bot)

    async def close(self) -> None:
        await self.client.aclose()

    async def run_due_monitors(self) -> None:
        rows = await self.bot.db.fetchall(
            """
            SELECT * FROM monitors
            WHERE enabled = 1
              AND (
                last_check IS NULL OR
                datetime(last_check, '+' || frequency_minutes || ' minutes') <= datetime('now')
              )
            ORDER BY COALESCE(last_check, '1970-01-01') ASC
            """
        )
        if rows:
            logger.info("Executando %s monitor(es)", len(rows))
        for row in rows:
            await self._run_with_retry(row)

    async def _run_with_retry(self, row) -> None:
        last_error = ""
        for attempt in range(1, 4):
            try:
                await self._run_monitor(row)
                await self._mark_checked(row["id"])
                return
            except Exception as exc:
                last_error = str(exc)[:500]
                logger.exception("Erro no monitor %s tentativa %s", row["id"], attempt)
                await asyncio.sleep(min(2 * attempt, 10))
        await self._mark_checked(row["id"], last_error)

    async def _run_monitor(self, row) -> None:
        monitor_type = row["type"]
        filters = self._load_filters(row["filters"])
        if monitor_type == "jobs":
            items = await self.jobs.fetch(filters)
        elif monitor_type == "hackathons":
            items = await self.hackathons.fetch(filters)
        elif monitor_type in {"youtube", "instagram"}:
            items = await self.social.fetch(monitor_type, row["source"])
        else:
            logger.warning("Tipo de monitor desconhecido: %s", monitor_type)
            return
        sent = 0
        for item in items[:10]:
            if await self.notifications.send(row["channel_id"], item):
                sent += 1
        logger.info("Monitor %s encontrou %s item(ns), enviados %s", row["id"], len(items), sent)

    def _load_filters(self, raw: str) -> list[str]:
        if not raw:
            return []
        try:
            value = json.loads(raw)
            return value if isinstance(value, list) else []
        except json.JSONDecodeError:
            return [part.strip() for part in raw.split(",") if part.strip()]

    async def _mark_checked(self, monitor_id: int, error: str = "") -> None:
        await self.bot.db.execute(
            "UPDATE monitors SET last_check = ?, last_error = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), error, monitor_id),
        )

