from __future__ import annotations

import hashlib
import logging

import httpx

from bot.services.monitor.models import MonitorItem
from bot.services.monitor.providers.freelance.fiverr_provider import FiverrFreelanceProvider
from bot.services.monitor.providers.freelance.freelancer_provider import FreelancerProvider
from bot.services.monitor.providers.freelance.generic_provider import GenericFreelanceProvider
from bot.services.monitor.providers.freelance.upwork_provider import UpworkFreelanceProvider


logger = logging.getLogger("devverse.monitor.freelance")


class FreelanceMonitor:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)
        self.last_errors: list[str] = []
        self.providers = (
            UpworkFreelanceProvider(self.client),
            FiverrFreelanceProvider(self.client),
            FreelancerProvider(self.client),
            GenericFreelanceProvider(self.client),
        )

    async def fetch(self) -> list[MonitorItem]:
        items: list[MonitorItem] = []
        self.last_errors = []
        for provider in self.providers:
            try:
                opportunities = await provider.fetch()
                items.extend(self._to_monitor_item(opportunity) for opportunity in opportunities)
            except Exception as exc:
                detail = f"{provider.platform}: {type(exc).__name__}: {str(exc)[:180]}"
                self.last_errors.append(detail)
                logger.exception("Falha ao buscar freelances em %s", provider.platform)
        return self._dedupe(items)

    def _to_monitor_item(self, opportunity: dict) -> MonitorItem:
        platform = str(opportunity.get("platform", "freelance")).strip()
        external_id = str(opportunity.get("external_id") or opportunity.get("url") or "").strip()
        url = str(opportunity.get("url") or "").strip()
        unique_hash = self._unique_hash(platform, external_id, url)
        skills = opportunity.get("skills") if isinstance(opportunity.get("skills"), list) else []
        return MonitorItem(
            type="freelance",
            title=str(opportunity.get("title") or "Projeto freelance").strip(),
            url=url,
            source=platform,
            summary="Analise de compatibilidade preparada para IA futura.",
            metadata={
                "client_or_company": str(opportunity.get("client_or_company") or "Nao informado"),
                "platform": platform,
                "source": platform,
                "budget": str(opportunity.get("budget") or "Nao informado"),
                "skills": ", ".join(str(skill) for skill in skills[:8]) or "Nao informado",
                "location": str(opportunity.get("location") or "Remote"),
                "remote": str(bool(opportunity.get("remote", True))),
                "external_id": external_id or url,
                "unique_hash": unique_hash,
            },
        )

    def _dedupe(self, items: list[MonitorItem]) -> list[MonitorItem]:
        seen: set[str] = set()
        unique: list[MonitorItem] = []
        for item in items:
            key = item.metadata.get("unique_hash") or item.url
            if not item.url or key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique

    def _unique_hash(self, platform: str, external_id: str, url: str) -> str:
        return hashlib.sha256(f"{platform}:{external_id}:{url}".encode("utf-8")).hexdigest()

