from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus

import httpx

from bot.config import settings
from bot.services.monitor.providers.base import JobProviderFilters, JobProviderResult


class IndeedJobsProvider:
    source = "indeed"
    base_url = "https://rss.indeed.com/rss"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, filters: JobProviderFilters) -> list[JobProviderResult]:
        query = quote_plus(" OR ".join(filters.get("areas", [])) or "software developer")
        location = quote_plus(settings.jobs_default_location)
        url = f"{self.base_url}?q={query}&l={location}"
        response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse_rss(response.text)

    def _parse_rss(self, xml_text: str) -> list[JobProviderResult]:
        root = ET.fromstring(xml_text)
        jobs: list[JobProviderResult] = []
        for item in root.findall(".//item"):
            title = (item.findtext("title") or "").strip()
            url = (item.findtext("link") or "").strip()
            description = self._strip_html(item.findtext("description") or "")
            company, location = self._split_title(title)
            if not title or not url:
                continue
            jobs.append(
                {
                    "title": title,
                    "company": company,
                    "location": location,
                    "remote": self._detect_model(f"{title} {description}"),
                    "technologies": [],
                    "url": url,
                    "source": self.source,
                    "external_id": self._external_id(url),
                }
            )
        return jobs

    def _split_title(self, title: str) -> tuple[str, str]:
        parts = [part.strip() for part in title.split(" - ")]
        company = parts[-2] if len(parts) >= 2 else "Nao informado"
        location = parts[-1] if len(parts) >= 1 else "Nao informado"
        return company, location

    def _detect_model(self, text: str) -> str:
        lowered = text.lower()
        if "remote" in lowered or "remoto" in lowered:
            return "Remote"
        if "hybrid" in lowered or "hibrido" in lowered:
            return "Hybrid"
        if "on-site" in lowered or "onsite" in lowered or "presencial" in lowered:
            return "On-site"
        return "Nao informado"

    def _external_id(self, url: str) -> str:
        match = re.search(r"jk=([A-Za-z0-9_-]+)", url)
        return match.group(1) if match else url

    def _strip_html(self, value: str) -> str:
        return re.sub(r"<[^>]+>", " ", value)

