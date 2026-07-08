from __future__ import annotations

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

import httpx
from discord.ext import commands

from bot.services.monitor.freelance_monitor import FreelanceMonitor
from bot.services.monitor.hackathon_monitor import HackathonMonitor
from bot.services.monitor.jobs_monitor import JobsMonitor
from bot.services.monitor.notification_service import NotificationService
from bot.services.monitor.social_monitor import SocialMonitor


logger = logging.getLogger("devverse.monitor")


@dataclass(slots=True)
class MonitorRunStats:
    found: int = 0
    new: int = 0
    sent: int = 0
    duplicates: int = 0
    errors: int = 0
    missing_channel: bool = False
    execution_time: float = 0.0
    channel_ids: set[int] = field(default_factory=set)
    error_details: list[str] = field(default_factory=list)


class MonitorManager:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.client = httpx.AsyncClient(timeout=20, follow_redirects=True)
        self.jobs = JobsMonitor(self.client)
        self.hackathons = HackathonMonitor(self.client)
        self.freelance = FreelanceMonitor(self.client)
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
        if not rows:
            stats.missing_channel = True
            return stats
        for row in rows:
            try:
                result = await self._run_monitor(row)
                stats.found += result.found
                stats.new += result.new
                stats.sent += result.sent
                stats.duplicates += result.duplicates
                stats.errors += result.errors
                stats.missing_channel = stats.missing_channel or result.missing_channel
                stats.execution_time += result.execution_time
                stats.channel_ids.update(result.channel_ids)
                stats.error_details.extend(result.error_details)
                await self._mark_checked(row["id"], error=self._format_error_details(result.error_details), result_count=result.found)
                await self._record_monitor_log(row["type"], result)
            except Exception as exc:
                stats.errors += 1
                stats.error_details.append(str(exc)[:180])
                logger.exception("Erro na execucao manual do monitor %s", row["id"])
                await self._mark_checked(row["id"], str(exc)[:500], 0)
                await self._record_monitor_log(row["type"], MonitorRunStats(errors=1, error_details=[str(exc)[:180]]))
        return stats

    async def _run_with_retry(self, row) -> None:
        last_error = ""
        for attempt in range(1, 4):
            try:
                result = await self._run_monitor(row)
                await self._mark_checked(row["id"], error=self._format_error_details(result.error_details), result_count=result.found)
                await self._record_monitor_log(row["type"], result)
                return
            except Exception as exc:
                last_error = str(exc)[:500]
                logger.exception("Erro no monitor %s tentativa %s", row["id"], attempt)
                await asyncio.sleep(min(2 * attempt, 10))
        await self._mark_checked(row["id"], last_error)
        await self._record_monitor_log(row["type"], MonitorRunStats(errors=1, error_details=[last_error]))

    async def _run_monitor(self, row) -> MonitorRunStats:
        started = time.perf_counter()
        monitor_type = row["type"]
        filters = self._load_filters(row["filters"])
        provider_error_details: list[str] = []
        if monitor_type == "jobs":
            items = await self.jobs.fetch(filters)
            provider_error_details = list(self.jobs.last_errors)
        elif monitor_type == "hackathons":
            items = await self.hackathons.fetch(filters)
        elif monitor_type == "freelance":
            items = await self.freelance.fetch()
            provider_error_details = list(self.freelance.last_errors)
        elif monitor_type in {"youtube", "instagram"}:
            try:
                items = await self.social.fetch(monitor_type, row["source"])
            except RuntimeError as exc:
                return MonitorRunStats(
                    errors=1,
                    error_details=[str(exc)],
                    execution_time=time.perf_counter() - started,
                    channel_ids={row["channel_id"]},
                )
        else:
            logger.warning("Tipo de monitor desconhecido: %s", monitor_type)
            return MonitorRunStats()
        sent = 0
        duplicates = 0
        errors = len(provider_error_details)
        missing_channel = False
        delivery_errors = 0
        for item in items[:10]:
            await self._record_item_log(monitor_type, item, row["channel_id"], "found")
            result = await self.notifications.send(row["channel_id"], item)
            if result.sent:
                sent += 1
                await self._record_item_log(monitor_type, item, row["channel_id"], "sent")
            elif result.duplicate:
                duplicates += 1
                await self._record_item_log(monitor_type, item, row["channel_id"], "duplicate")
            elif result.status == "missing_channel":
                missing_channel = True
                errors += 1
                delivery_errors += 1
                await self._record_item_log(monitor_type, item, row["channel_id"], "missing_channel")
            else:
                errors += 1
                delivery_errors += 1
                await self._record_item_log(monitor_type, item, row["channel_id"], "error")
        logger.info("Monitor %s encontrou %s item(ns), enviados %s", row["id"], len(items), sent)
        execution_time = time.perf_counter() - started
        return MonitorRunStats(
            found=len(items),
            new=sent + delivery_errors,
            sent=sent,
            duplicates=duplicates,
            errors=errors,
            missing_channel=missing_channel,
            execution_time=execution_time,
            channel_ids={row["channel_id"]},
            error_details=provider_error_details,
        )

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

    def _format_error_details(self, details: list[str]) -> str:
        return "\n".join(details)[:500]

    async def _record_monitor_log(self, monitor_type: str, stats: MonitorRunStats) -> None:
        await self.bot.db.execute(
            """
            INSERT INTO monitor_logs
                (type, monitor_type, items_found, items_new, items_sent, duplicates, errors, execution_time, error_message)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                monitor_type,
                monitor_type,
                stats.found,
                stats.new,
                stats.sent,
                stats.duplicates,
                stats.errors,
                stats.execution_time,
                self._format_error_details(stats.error_details),
            ),
        )

    async def _record_item_log(self, monitor_type: str, item, channel_id: int, status: str) -> None:
        await self.bot.db.execute(
            "INSERT INTO monitor_item_logs (type, title, url, channel_id, status) VALUES (?, ?, ?, ?, ?)",
            (monitor_type, item.title, item.url, channel_id, status),
        )
