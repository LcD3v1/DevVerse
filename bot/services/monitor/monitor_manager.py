from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

import httpx
from discord.ext import commands

from bot.services.monitor.hackathon_monitor import HackathonMonitor
from bot.services.monitor.jobs_monitor import JobsMonitor
from bot.services.monitor.notification_service import NotificationService
from bot.services.monitor.social_monitor import SocialMonitor


logger = logging.getLogger("devverse.monitor")


@dataclass(slots=True)
class MonitorRunStats:
    found: int = 0
    sent: int = 0
    errors: int = 0


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

    async def run_now(self, guild_id: int, monitor_type: str) -> MonitorRunStats:
        db_type = "hackathons" if monitor_type == "hackathons" else monitor_type
        rows = await self.bot.db.fetchall(
            "SELECT * FROM monitors WHERE guild_id = ? AND type = ? AND enabled = 1 ORDER BY id",
            (guild_id, db_type),
        )
        stats = MonitorRunStats()
        for row in rows:
            try:
                result = await self._run_monitor(row)
                stats.found += result.found
                stats.sent += result.sent
                await self._mark_checked(row["id"], result_count=result.found)
            except Exception as exc:
                stats.errors += 1
                logger.exception("Erro na execucao manual do monitor %s", row["id"])
                await self._mark_checked(row["id"], str(exc)[:500], 0)
        return stats

    async def _run_with_retry(self, row) -> None:
        last_error = ""
        for attempt in range(1, 4):
            try:
                result = await self._run_monitor(row)
                await self._mark_checked(row["id"], result_count=result.found)
                return
            except Exception as exc:
                last_error = str(exc)[:500]
                logger.exception("Erro no monitor %s tentativa %s", row["id"], attempt)
                await asyncio.sleep(min(2 * attempt, 10))
        await self._mark_checked(row["id"], last_error)

    async def _run_monitor(self, row) -> MonitorRunStats:
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
            return MonitorRunStats()
        sent = 0
        for item in items[:10]:
            if await self.notifications.send(row["channel_id"], item):
                sent += 1
        logger.info("Monitor %s encontrou %s item(ns), enviados %s", row["id"], len(items), sent)
        return MonitorRunStats(found=len(items), sent=sent)

    def _load_filters(self, raw: str):
        if not raw:
            return []
        try:
            value = json.loads(raw)
            return value if isinstance(value, (list, dict)) else []
        except json.JSONDecodeError:
            return [part.strip() for part in raw.split(",") if part.strip()]

    async def _mark_checked(self, monitor_id: int, error: str = "", result_count: int = 0) -> None:
        await self.bot.db.execute(
            "UPDATE monitors SET last_check = ?, last_error = ?, last_result_count = ? WHERE id = ?",
            (datetime.now(timezone.utc).isoformat(), error, result_count, monitor_id),
        )
