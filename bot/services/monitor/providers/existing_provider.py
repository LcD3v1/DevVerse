from __future__ import annotations

import logging
from typing import Any

import httpx

from bot.config import settings
from bot.services.monitor.providers.base import JobProviderFilters, JobProviderResult


logger = logging.getLogger("devverse.monitor.jobs.existing")


class ExistingJobsProvider:
    source = "existing"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, filters: JobProviderFilters) -> list[JobProviderResult]:
        jobs: list[JobProviderResult] = []
        for url in settings.jobs_source_urls:
            response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
            response.raise_for_status()
            jobs.extend(self._parse_payload(url, response.json()))
        return jobs

    def _parse_payload(self, source_url: str, payload: Any) -> list[JobProviderResult]:
        raw_jobs = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
        parsed: list[JobProviderResult] = []
        for job in raw_jobs:
            if not isinstance(job, dict):
                continue
            title = str(job.get("position") or job.get("title") or job.get("job_title") or "").strip()
            company = str(job.get("company") or job.get("company_name") or "").strip()
            url = str(job.get("url") or job.get("apply_url") or job.get("job_url") or "").strip()
            if not title or not url:
                continue
            tags = job.get("tags") if isinstance(job.get("tags"), list) else []
            location = str(job.get("location") or job.get("candidate_required_location") or "Nao informado")
            text = f"{title} {company} {location} {tags}".lower()
            parsed.append(
                {
                    "title": title,
                    "company": company or "Nao informado",
                    "location": location,
                    "remote": "Remote" if "remote" in text or "remoto" in text else "Nao informado",
                    "technologies": [str(tag) for tag in tags[:8]],
                    "url": url,
                    "source": self.source,
                    "external_id": str(job.get("id") or job.get("slug") or url),
                }
            )
        return parsed

