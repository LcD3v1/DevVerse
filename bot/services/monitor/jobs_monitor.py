from __future__ import annotations

import logging
from typing import Any

import httpx

from bot.config import settings
from bot.services.monitor.models import MonitorItem


logger = logging.getLogger("devverse.monitor.jobs")

TECH_AREAS = {
    "frontend": ("frontend", "front-end", "react", "vue", "angular", "javascript", "typescript"),
    "backend": ("backend", "back-end", "python", "django", "fastapi", "node", "java", "api"),
    "full stack": ("full stack", "full-stack", "fullstack"),
    "mobile": ("mobile", "android", "ios", "react native", "flutter"),
    "data science": ("data science", "data scientist", "analytics", "pandas"),
    "machine learning": ("machine learning", "ml engineer", "deep learning"),
    "artificial intelligence": ("artificial intelligence", "ai engineer", "generative ai", "llm"),
    "cybersecurity": ("cybersecurity", "security", "infosec", "pentest"),
    "devops": ("devops", "sre", "kubernetes", "docker", "ci/cd"),
    "cloud": ("cloud", "aws", "azure", "gcp"),
    "blockchain": ("blockchain", "web3", "solidity", "smart contract"),
}


class JobsMonitor:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def fetch(self, areas: list[str]) -> list[MonitorItem]:
        items: list[MonitorItem] = []
        for url in settings.jobs_source_urls:
            try:
                response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
                response.raise_for_status()
                payload = response.json()
                items.extend(self._parse_payload(url, payload, areas))
            except Exception:
                logger.exception("Falha ao buscar vagas em %s", url)
                raise
        return items

    def _parse_payload(self, source_url: str, payload: Any, areas: list[str]) -> list[MonitorItem]:
        raw_jobs = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
        parsed: list[MonitorItem] = []
        for job in raw_jobs:
            if not isinstance(job, dict):
                continue
            title = str(job.get("position") or job.get("title") or job.get("job_title") or "").strip()
            company = str(job.get("company") or job.get("company_name") or "").strip()
            url = str(job.get("url") or job.get("apply_url") or job.get("job_url") or "").strip()
            if not title or not url:
                continue
            description = str(job.get("description") or job.get("tags") or job.get("category") or "")
            text = f"{title} {company} {description}".lower()
            matched = self._matched_areas(text, areas)
            if not matched:
                continue
            tags = job.get("tags") if isinstance(job.get("tags"), list) else []
            location = str(job.get("location") or job.get("candidate_required_location") or "Nao informado")
            model = "Remoto" if "remote" in text or "remoto" in text else "Nao informado"
            parsed.append(
                MonitorItem(
                    type="job",
                    title=title,
                    url=url,
                    source=source_url,
                    metadata={
                        "company": company or "Nao informado",
                        "technologies": ", ".join(map(str, tags[:8])) or ", ".join(matched),
                        "location": location,
                        "model": model,
                    },
                )
            )
        return parsed

    def _matched_areas(self, text: str, areas: list[str]) -> list[str]:
        selected = [area.strip().lower() for area in areas if area.strip()]
        if not selected:
            selected = list(TECH_AREAS)
        matched: list[str] = []
        for area in selected:
            keywords = TECH_AREAS.get(area, (area,))
            if any(keyword in text for keyword in keywords):
                matched.append(area)
        return matched

