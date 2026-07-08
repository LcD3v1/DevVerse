from __future__ import annotations

import hashlib
import logging
import re
from html import unescape
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from bot.config import settings
from bot.services.monitor.providers.base import JobProviderFilters, JobProviderResult


logger = logging.getLogger("devverse.monitor.jobs.public")


PUBLIC_JOB_SOURCES: tuple[tuple[str, str, str], ...] = (
    ("programathor", "Programathor", "https://programathor.com.br/jobs"),
    ("geekhunter", "GeekHunter", "https://www.geekhunter.com.br/vagas"),
    ("revelo", "Revelo", "https://www.revelo.com.br/vagas"),
    ("trampos", "Trampos.co", "https://trampos.co/oportunidades"),
    ("coodesh", "Coodesh", "https://coodesh.com/vagas"),
    ("gupy_tecnologia", "Gupy tecnologia", "https://portal.gupy.io/job-search/term=tecnologia"),
    ("remotar", "Remotar", "https://remotar.com.br"),
    ("hipsters", "Hipsters.jobs", "https://hipsters.jobs/jobs"),
    ("weworkremotely", "WeWorkRemotely", "https://weworkremotely.com/categories/remote-programming-jobs"),
    ("wellfound", "Wellfound", "https://wellfound.com/jobs"),
)


class PublicJobsProvider:
    source = "public_jobs"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self, filters: JobProviderFilters) -> list[JobProviderResult]:
        jobs: list[JobProviderResult] = []
        for url in settings.jobs_source_urls:
            try:
                response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
                response.raise_for_status()
                if "json" in response.headers.get("content-type", "") or url.endswith("/api"):
                    jobs.extend(self._parse_json(url, response.json()))
            except Exception:
                logger.exception("Falha ao buscar feed de vagas em %s", url)
        for source, label, url in PUBLIC_JOB_SOURCES:
            try:
                response = await self.client.get(url, headers={"User-Agent": "Mozilla/5.0 DevVerseAssistant/1.0"})
                response.raise_for_status()
                jobs.extend(self._parse_html(source, label, url, response.text))
            except Exception:
                logger.exception("Falha ao buscar vagas em %s", label)
        return self._dedupe(jobs)

    def _parse_json(self, source_url: str, payload: Any) -> list[JobProviderResult]:
        raw_jobs = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
        parsed: list[JobProviderResult] = []
        for job in raw_jobs:
            if not isinstance(job, dict):
                continue
            title = str(job.get("position") or job.get("title") or job.get("job_title") or "").strip()
            company = str(job.get("company") or job.get("company_name") or "").strip()
            url = str(job.get("url") or job.get("apply_url") or job.get("job_url") or "").strip()
            if not title or not url or not self._is_tech_text(f"{title} {company} {job}"):
                continue
            tags = job.get("tags") if isinstance(job.get("tags"), list) else []
            location = str(job.get("location") or job.get("candidate_required_location") or "Global")
            source = "remoteok" if "remoteok" in source_url else "public_jobs"
            text = f"{title} {company} {location} {tags}".lower()
            parsed.append(
                {
                    "title": title,
                    "company": company or "Nao informado",
                    "location": location,
                    "remote": self._detect_model(text),
                    "technologies": [str(tag) for tag in tags[:8]],
                    "url": url,
                    "source": source,
                    "external_id": str(job.get("id") or job.get("slug") or self._hash(url)),
                    "region": self._detect_region(location, source),
                    "seniority": self._detect_seniority(text),
                }
            )
        return parsed

    def _parse_html(self, source: str, label: str, source_url: str, html: str) -> list[JobProviderResult]:
        parsed: list[JobProviderResult] = []
        base = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"
        for match in re.finditer(r'href=["\'](?P<url>[^"\']+)["\'][^>]*>(?P<title>[^<]{6,180})<', html, flags=re.IGNORECASE):
            title = unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", match.group("title")))).strip()
            raw_url = unescape(match.group("url")).strip()
            if not title or not raw_url:
                continue
            url = raw_url if raw_url.startswith("http") else urljoin(base, raw_url)
            text = f"{title} {url}"
            if not self._looks_like_job_url(source, url) or not self._is_tech_text(text):
                continue
            parsed.append(
                {
                    "title": title,
                    "company": label,
                    "location": "Nao informado",
                    "remote": self._detect_model(text),
                    "technologies": self._detect_technologies(text),
                    "url": url,
                    "source": source,
                    "external_id": self._hash(url),
                    "region": self._detect_region(text, source),
                    "seniority": self._detect_seniority(text),
                }
            )
            if len(parsed) >= 12:
                break
        return parsed

    def _looks_like_job_url(self, source: str, url: str) -> bool:
        lowered = url.lower()
        if any(blocked in lowered for blocked in ("login", "signin", "cadastro", "privacy", "termos", "blog", "empresa")):
            return False
        source_terms = {
            "weworkremotely": ("/remote-jobs/", "/remote-programming-jobs"),
            "wellfound": ("/jobs",),
            "remoteok": ("/remote-jobs/",),
        }
        terms = source_terms.get(source, ("vaga", "job", "oportunidade", "trabalho", "developer", "programador"))
        return any(term in lowered for term in terms)

    def _is_tech_text(self, text: str) -> bool:
        lowered = text.lower()
        terms = (
            "developer",
            "programador",
            "programadora",
            "software",
            "backend",
            "frontend",
            "full stack",
            "fullstack",
            "dados",
            "data",
            "devops",
            "cloud",
            "python",
            "javascript",
            "typescript",
            "java",
            "mobile",
            "android",
            "ios",
            "security",
            "cyber",
            "qa",
            "api",
            "react",
            "node",
        )
        return any(term in lowered for term in terms)

    def _detect_technologies(self, text: str) -> list[str]:
        lowered = text.lower()
        technologies = []
        for tech in ("Python", "JavaScript", "TypeScript", "Java", "React", "Node", "AWS", "Docker", "Kubernetes", "SQL", "Android", "iOS", "Go", "PHP", "Ruby"):
            if tech.lower() in lowered:
                technologies.append(tech)
        return technologies

    def _detect_model(self, text: str) -> str:
        lowered = text.lower()
        if "remote" in lowered or "remoto" in lowered or "remotar" in lowered:
            return "Remote"
        if "hybrid" in lowered or "hibrido" in lowered or "híbrido" in lowered:
            return "Hybrid"
        if "presencial" in lowered or "on-site" in lowered or "onsite" in lowered:
            return "On-site"
        return "Nao informado"

    def _detect_region(self, text: str, source: str) -> str:
        lowered = text.lower()
        if source in {"programathor", "geekhunter", "revelo", "trampos", "coodesh", "gupy_tecnologia", "remotar", "hipsters"}:
            return "Brasil"
        if "brazil" in lowered or "brasil" in lowered:
            return "Brasil"
        if "united states" in lowered or "usa" in lowered or "eua" in lowered:
            return "Estados Unidos"
        return "Global"

    def _detect_seniority(self, text: str) -> str:
        lowered = text.lower()
        if any(term in lowered for term in ("intern", "estagio", "estágio", "estagiario", "estagiário", "trainee")):
            return "Estagio"
        if any(term in lowered for term in ("junior", "júnior", "jr.", "jr ")):
            return "Junior"
        if any(term in lowered for term in ("pleno", "mid", "mid-level")):
            return "Pleno"
        if any(term in lowered for term in ("senior", "sênior", "sr.", "staff", "lead")):
            return "Senior"
        return "Nao informado"

    def _dedupe(self, jobs: list[JobProviderResult]) -> list[JobProviderResult]:
        seen: set[str] = set()
        unique: list[JobProviderResult] = []
        for job in jobs:
            key = f"{job['source']}:{job.get('external_id', '')}:{job['url']}"
            if key in seen:
                continue
            seen.add(key)
            unique.append(job)
        return unique

    def _hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]

