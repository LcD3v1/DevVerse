from __future__ import annotations

import hashlib
import logging
from typing import Any

import httpx

from bot.services.monitor.models import MonitorItem
from bot.services.monitor.providers.base import JobProviderFilters, JobProviderResult
from bot.services.monitor.providers.existing_provider import ExistingJobsProvider
from bot.services.monitor.providers.indeed_provider import IndeedJobsProvider
from bot.services.monitor.providers.linkedin_provider import LinkedInJobsProvider


logger = logging.getLogger("devverse.monitor.jobs")

TECH_AREAS = {
    "frontend": ("frontend", "front-end", "react", "vue", "angular", "javascript", "typescript"),
    "backend": ("backend", "back-end", "python", "django", "fastapi", "node", "java", "api"),
    "full stack": ("full stack", "full-stack", "fullstack"),
    "mobile": ("mobile", "android", "ios", "react native", "flutter"),
    "data science": ("data science", "data scientist", "analytics", "pandas"),
    "machine learning": ("machine learning", "ml engineer", "deep learning"),
    "ai engineer": ("ai engineer", "artificial intelligence", "generative ai", "llm", "machine learning"),
    "artificial intelligence": ("artificial intelligence", "ai engineer", "generative ai", "llm"),
    "cybersecurity": ("cybersecurity", "security", "infosec", "pentest"),
    "devops": ("devops", "sre", "kubernetes", "docker", "ci/cd"),
    "cloud": ("cloud", "aws", "azure", "gcp"),
    "blockchain": ("blockchain", "web3", "solidity", "smart contract"),
    "game development": ("game development", "game developer", "unity", "unreal", "gamedev"),
}

LEVELS = {
    "internship": ("internship", "intern", "estagio", "estagiario", "trainee"),
    "entry level": ("entry level", "entry-level", "associate"),
    "junior": ("junior", "jr.", "jr "),
    "mid": ("mid", "pleno", "mid-level"),
    "senior": ("senior", "sr.", "sr ", "staff", "lead"),
}

MODELS = {
    "remote": ("remote", "remoto"),
    "hybrid": ("hybrid", "hibrido"),
    "on-site": ("on-site", "onsite", "presencial"),
}

SOURCE_LABELS = {
    "linkedin": "LinkedIn",
    "indeed": "Indeed",
    "existing": "Outras",
}


class JobsMonitor:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)
        self.providers = {
            "linkedin": LinkedInJobsProvider(self.client),
            "indeed": IndeedJobsProvider(self.client),
            "existing": ExistingJobsProvider(self.client),
        }

    async def fetch(self, filters: list[str] | dict[str, Any]) -> list[MonitorItem]:
        config = self._normalize_filters(filters)
        selected_sources = config.get("sources") or ["linkedin", "indeed", "existing"]
        items: list[MonitorItem] = []
        provider_filters: JobProviderFilters = {
            "areas": config.get("areas", []),
            "levels": [],
            "models": [],
        }
        for source in selected_sources:
            provider = self.providers.get(source)
            if not provider:
                logger.warning("Provider de vagas desconhecido: %s", source)
                continue
            try:
                jobs = await provider.fetch(provider_filters)
                items.extend(self._to_monitor_item(job, config) for job in jobs if self._matches(job, config))
            except Exception:
                logger.exception("Falha ao buscar vagas no provider %s", source)
                raise
        return items

    def _normalize_filters(self, filters: list[str] | dict[str, Any]) -> dict[str, list[str]]:
        if isinstance(filters, dict):
            return {
                "sources": self._normalize_sources(filters.get("sources", [])),
                "areas": list(TECH_AREAS),
                "levels": [],
                "models": [],
            }
        return {
            "sources": ["linkedin", "indeed", "existing"],
            "areas": list(TECH_AREAS),
            "levels": [],
            "models": [],
        }

    def _to_monitor_item(self, job: JobProviderResult, filters: dict[str, list[str]]) -> MonitorItem:
        source = job["source"]
        external_id = job.get("external_id") or job["url"]
        unique_hash = self._unique_hash(source, external_id)
        technologies = job.get("technologies") or self._matched_areas(self._search_text(job), filters.get("areas", []))
        return MonitorItem(
            type="job",
            title=job["title"],
            url=job["url"],
            source=source,
            summary="Analise de compatibilidade preparada para IA futura.",
            metadata={
                "company": job.get("company", "Nao informado"),
                "technologies": ", ".join(technologies) or "Nao informado",
                "location": job.get("location", "Nao informado"),
                "model": job.get("remote", "Nao informado"),
                "source": source,
                "source_label": SOURCE_LABELS.get(source, source.title()),
                "external_id": external_id,
                "unique_hash": unique_hash,
            },
        )

    def _matches(self, job: JobProviderResult, filters: dict[str, list[str]]) -> bool:
        text = self._search_text(job)
        if not self._matched_areas(text, filters.get("areas", list(TECH_AREAS))):
            return False
        return True

    def _search_text(self, job: JobProviderResult) -> str:
        values = [
            job.get("title", ""),
            job.get("company", ""),
            job.get("location", ""),
            job.get("remote", ""),
            " ".join(job.get("technologies", [])),
        ]
        return " ".join(values).lower()

    def _matched_areas(self, text: str, areas: list[str]) -> list[str]:
        selected = areas or list(TECH_AREAS)
        matched: list[str] = []
        for area in selected:
            keywords = TECH_AREAS.get(area, (area,))
            if any(keyword in text for keyword in keywords):
                matched.append(area)
        return matched

    def _matches_map(self, text: str, selected: list[str], values: dict[str, tuple[str, ...]]) -> bool:
        for option in selected:
            keywords = values.get(option, (option,))
            if any(keyword in text for keyword in keywords):
                return True
        return False

    def _normalize_sources(self, values: Any) -> list[str]:
        aliases = {"outras": "existing", "outros": "existing", "other": "existing", "existing": "existing"}
        sources = [aliases.get(value, value) for value in self._normalize_list(values)]
        return [source for source in sources if source in self.providers]

    def _normalize_models(self, values: Any) -> list[str]:
        aliases = {"onsite": "on-site", "on site": "on-site", "presencial": "on-site", "hibrido": "hybrid", "remoto": "remote"}
        return [aliases.get(value, value) for value in self._normalize_list(values)]

    def _normalize_levels(self, values: Any) -> list[str]:
        aliases = {
            "estagio": "internship",
            "estagiario": "internship",
            "intern": "internship",
            "trainee": "internship",
            "entry": "entry level",
            "jr": "junior",
            "jr.": "junior",
            "pleno": "mid",
            "mid-level": "mid",
            "sr": "senior",
            "sr.": "senior",
        }
        return [aliases.get(value, value) for value in self._normalize_list(values)]

    def _normalize_areas(self, values: Any) -> list[str]:
        aliases = {
            "ai": "ai engineer",
            "ia": "ai engineer",
            "artificial intelligence": "ai engineer",
            "ml": "machine learning",
            "fullstack": "full stack",
            "full-stack": "full stack",
            "front-end": "frontend",
            "back-end": "backend",
            "security": "cybersecurity",
        }
        return [aliases.get(value, value) for value in self._normalize_list(values)]

    def _normalize_list(self, values: Any) -> list[str]:
        if isinstance(values, str):
            raw_values = values.split(",")
        elif isinstance(values, list):
            raw_values = values
        else:
            raw_values = []
        return [str(value).strip().lower() for value in raw_values if str(value).strip()]

    def _unique_hash(self, source: str, external_id: str) -> str:
        return hashlib.sha256(f"{source}:{external_id}".encode("utf-8")).hexdigest()
