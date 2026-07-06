from __future__ import annotations

import logging
import re
from html import unescape
from typing import Any

import httpx

from bot.config import settings
from bot.services.monitor.models import MonitorItem


logger = logging.getLogger("devverse.monitor.hackathons")


class HackathonMonitor:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def fetch(self, categories: list[str]) -> list[MonitorItem]:
        items: list[MonitorItem] = []
        for url in settings.hackathon_source_urls:
            try:
                response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
                response.raise_for_status()
                payload = response.json()
                items.extend(self._parse_payload(url, payload, categories))
            except Exception:
                logger.exception("Falha ao buscar hackathons em %s", url)
                raise
        return items

    def _parse_payload(self, source_url: str, payload: Any, categories: list[str]) -> list[MonitorItem]:
        raw_events = payload.get("hackathons", payload.get("data", [])) if isinstance(payload, dict) else payload if isinstance(payload, list) else []
        selected = [category.strip().lower() for category in categories if category.strip()]
        parsed: list[MonitorItem] = []
        for event in raw_events:
            if not isinstance(event, dict):
                continue
            name = str(event.get("title") or event.get("name") or "").strip()
            url = str(event.get("url") or event.get("website_url") or event.get("submission_gallery_url") or "").strip()
            if not name or not url:
                continue
            themes = self._names(event.get("themes"))
            category = ", ".join(themes[:4]) or self._clean_text(event.get("category")) or "Tecnologia"
            text = f"{name} {category}".lower()
            if selected and not any(category_filter in text for category_filter in selected):
                continue
            technologies = self._names(event.get("technologies")) or themes
            parsed.append(
                MonitorItem(
                    type="hackathon",
                    title=name,
                    url=url,
                    source=source_url,
                    metadata={
                        "category": category,
                        "technologies": ", ".join(technologies[:6]) or "Nao informado",
                        "date": self._clean_text(event.get("displayed_time") or event.get("start_date")) or "Nao informado",
                        "prize": self._clean_text(event.get("prize_amount") or event.get("prize")) or "Nao informado",
                        "format": self._format_state(event.get("open_state") or event.get("format")),
                    },
                )
            )
        return parsed

    def _names(self, value: Any) -> list[str]:
        if not isinstance(value, list):
            return []
        names: list[str] = []
        for item in value:
            if isinstance(item, dict):
                name = self._clean_text(item.get("name") or item.get("title") or item.get("label"))
            else:
                name = self._clean_text(item)
            if name:
                names.append(name)
        return names

    def _clean_text(self, value: Any) -> str:
        if value is None:
            return ""
        text = unescape(str(value))
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text

    def _format_state(self, value: Any) -> str:
        state = self._clean_text(value).lower()
        labels = {
            "open": "Inscricoes abertas",
            "closed": "Encerrado",
            "online": "Online",
            "in_person": "Presencial",
            "hybrid": "Hibrido",
        }
        return labels.get(state, self._clean_text(value) or "Nao informado")
