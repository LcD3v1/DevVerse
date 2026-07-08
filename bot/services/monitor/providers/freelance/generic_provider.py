from __future__ import annotations

import hashlib
import logging
import re
from typing import Any
from html import unescape
from urllib.parse import urljoin, urlparse

import httpx

from bot.config import settings
from bot.services.monitor.providers.freelance.base import FreelanceOpportunity


logger = logging.getLogger("devverse.monitor.freelance.generic")


class GenericFreelanceProvider:
    platform = "RemoteOK"
    public_pages = (
        ("PeoplePerHour", "https://www.peopleperhour.com/freelance-jobs/technology-programming"),
        ("Guru", "https://www.guru.com/d/jobs/c/programming-development/"),
        ("WeWorkRemotely", "https://weworkremotely.com/remote-contract-programming-jobs"),
    )

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self) -> list[FreelanceOpportunity]:
        opportunities: list[FreelanceOpportunity] = []
        for url in settings.freelance_source_urls:
            try:
                response = await self.client.get(url, headers={"User-Agent": "DevVerseAssistant/1.0"})
                response.raise_for_status()
                content_type = response.headers.get("content-type", "")
                if "json" in content_type or url.endswith("/api"):
                    opportunities.extend(self._parse_json(url, response.json()))
            except Exception:
                logger.exception("Falha ao buscar feed freelance generico em %s", url)
        for platform, url in self.public_pages:
            try:
                response = await self.client.get(url, headers={"User-Agent": "Mozilla/5.0 DevVerseAssistant/1.0"})
                response.raise_for_status()
                opportunities.extend(self._parse_html(platform, url, response.text))
            except Exception:
                logger.exception("Falha ao buscar pagina freelance publica em %s", url)
        return opportunities

    def _parse_json(self, source_url: str, payload: Any) -> list[FreelanceOpportunity]:
        rows = payload if isinstance(payload, list) else payload.get("data", []) if isinstance(payload, dict) else []
        parsed: list[FreelanceOpportunity] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("position") or row.get("title") or row.get("job_title") or "").strip()
            if not title or not self._looks_contract(title, row):
                continue
            url = str(row.get("url") or row.get("apply_url") or row.get("job_url") or "").strip()
            if not url:
                slug = str(row.get("slug") or row.get("id") or "").strip()
                url = urljoin("https://remoteok.com/remote-jobs/", slug) if slug else source_url
            tags = row.get("tags") if isinstance(row.get("tags"), list) else []
            external_id = str(row.get("id") or row.get("slug") or self._hash(url))
            platform = "RemoteOK" if "remoteok" in source_url else "Public feed"
            parsed.append(
                {
                    "title": title,
                    "client_or_company": str(row.get("company") or row.get("company_name") or "Nao informado"),
                    "platform": platform,
                    "budget": str(row.get("salary") or row.get("budget") or "Nao informado"),
                    "skills": [str(tag) for tag in tags[:8]],
                    "location": str(row.get("location") or row.get("candidate_required_location") or "Remote"),
                    "remote": True,
                    "url": url,
                    "external_id": external_id,
                }
            )
        return parsed

    def _parse_html(self, platform: str, source_url: str, html: str) -> list[FreelanceOpportunity]:
        parsed: list[FreelanceOpportunity] = []
        base = f"{urlparse(source_url).scheme}://{urlparse(source_url).netloc}"
        for match in re.finditer(r'href="(?P<url>[^"]+)"[^>]*>(?P<title>[^<]{8,180})<', html):
            title = unescape(re.sub(r"\s+", " ", match.group("title"))).strip()
            raw_url = unescape(match.group("url"))
            if not self._looks_like_programming_link(title, raw_url):
                continue
            url = raw_url if raw_url.startswith("http") else urljoin(base, raw_url)
            parsed.append(
                {
                    "title": title,
                    "client_or_company": platform,
                    "platform": platform,
                    "budget": "Nao informado",
                    "skills": ["programming", "development"],
                    "location": "Remote",
                    "remote": True,
                    "url": url,
                    "external_id": self._hash(url),
                }
            )
            if len(parsed) >= 10:
                break
        return parsed

    def _looks_contract(self, title: str, row: dict[str, Any]) -> bool:
        text = " ".join(
            [
                title,
                str(row.get("description", "")),
                str(row.get("type", "")),
                " ".join(str(tag) for tag in row.get("tags", []) if isinstance(row.get("tags"), list)),
            ]
        ).lower()
        freelance_terms = ("freelance", "contract", "contractor", "gig", "temporary", "part-time")
        tech_terms = ("developer", "software", "python", "javascript", "backend", "frontend", "web", "api", "ai", "cloud")
        return any(term in text for term in freelance_terms) and any(term in text for term in tech_terms)

    def _looks_like_programming_link(self, title: str, url: str) -> bool:
        text = f"{title} {url}".lower()
        terms = ("program", "developer", "software", "python", "javascript", "web", "api", "wordpress", "app", "remote", "contract")
        blocked = ("login", "signup", "privacy", "terms", "category", "blog")
        return any(term in text for term in terms) and not any(term in text for term in blocked)

    def _hash(self, value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
