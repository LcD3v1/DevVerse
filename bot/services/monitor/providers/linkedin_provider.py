from __future__ import annotations

import re
from html import unescape
from urllib.parse import quote_plus

import httpx

from bot.config import settings
from bot.services.monitor.providers.base import JobProviderFilters, JobProviderResult


class LinkedInJobsProvider:
    source = "linkedin"
    base_url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, filters: JobProviderFilters) -> list[JobProviderResult]:
        query = quote_plus(" OR ".join(filters.get("areas", [])) or "software developer")
        location = quote_plus(settings.jobs_default_location)
        url = f"{self.base_url}?keywords={query}&location={location}&start=0"
        response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse_cards(response.text)

    def _parse_cards(self, html_text: str) -> list[JobProviderResult]:
        cards = re.split(r'<li\b', html_text)
        jobs: list[JobProviderResult] = []
        for card in cards:
            title = self._text(card, r'class="[^"]*base-search-card__title[^"]*"[^>]*>(.*?)</')
            company = self._text(card, r'class="[^"]*base-search-card__subtitle[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>')
            location = self._text(card, r'class="[^"]*job-search-card__location[^"]*"[^>]*>(.*?)</')
            url = self._attr(card, r'<a[^>]+class="[^"]*base-card__full-link[^"]*"[^>]+href="([^"]+)"')
            external_id = self._attr(card, r'data-entity-urn="urn:li:jobPosting:([^"]+)"') or self._external_id(url)
            if not title or not url:
                continue
            text = f"{title} {company} {location}"
            jobs.append(
                {
                    "title": title,
                    "company": company or "Nao informado",
                    "location": location or "Nao informado",
                    "remote": self._detect_model(text),
                    "technologies": [],
                    "url": url.split("?")[0],
                    "source": self.source,
                    "external_id": external_id,
                }
            )
        return jobs

    def _text(self, html_text: str, pattern: str) -> str:
        match = re.search(pattern, html_text, flags=re.DOTALL)
        if not match:
            return ""
        return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", match.group(1)))).strip()

    def _attr(self, html_text: str, pattern: str) -> str:
        match = re.search(pattern, html_text, flags=re.DOTALL)
        return unescape(match.group(1)).strip() if match else ""

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
        match = re.search(r"currentJobId=([0-9]+)|/jobs/view/([0-9]+)", url)
        if not match:
            return url
        return next(group for group in match.groups() if group)
