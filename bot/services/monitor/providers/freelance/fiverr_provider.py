from __future__ import annotations

import re
from html import unescape

import httpx

from bot.services.monitor.providers.freelance.base import FreelanceOpportunity


class FiverrFreelanceProvider:
    platform = "Fiverr"
    search_url = "https://www.fiverr.com/search/gigs?query=programming"

    def __init__(self, client: httpx.AsyncClient) -> None:
        self.client = client

    async def fetch(self) -> list[FreelanceOpportunity]:
        response = await self.client.get(self.search_url, headers={"User-Agent": "Mozilla/5.0 DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse(response.text)

    def _parse(self, html: str) -> list[FreelanceOpportunity]:
        items: list[FreelanceOpportunity] = []
        for match in re.finditer(r'href="(?P<url>/[^"]+?/[^"]+?)"[^>]*>(?P<title>[^<]{8,180})<', html):
            raw_url = unescape(match.group("url"))
            if "/categories/" in raw_url or raw_url.startswith("/search"):
                continue
            url = "https://www.fiverr.com" + raw_url
            title = unescape(re.sub(r"\s+", " ", match.group("title"))).strip()
            if title and not any(item["url"] == url for item in items):
                items.append(self._item(title, url))
            if len(items) >= 10:
                break
        return items

    def _item(self, title: str, url: str) -> FreelanceOpportunity:
        external_id = url.rstrip("/").split("/")[-1]
        return {
            "title": title,
            "client_or_company": "Fiverr Marketplace",
            "platform": self.platform,
            "budget": "Nao informado",
            "skills": ["programming"],
            "location": "Remote",
            "remote": True,
            "url": url,
            "external_id": external_id,
        }

