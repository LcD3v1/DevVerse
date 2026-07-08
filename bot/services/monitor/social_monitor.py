from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET
from datetime import datetime

import httpx

from bot.config import settings
from bot.services.monitor.models import MonitorItem


logger = logging.getLogger("devverse.monitor.social")
YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


class SocialMonitor:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=True)

    async def fetch(self, platform: str, creator: str) -> list[MonitorItem]:
        platform = platform.lower()
        if platform == "youtube":
            return await self._fetch_youtube(creator)
        if platform == "instagram":
            return await self._fetch_instagram(creator)
        return []

    async def _fetch_youtube(self, creator: str) -> list[MonitorItem]:
        source = await self._resolve_youtube_source(creator)
        response = await self.client.get(source, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse_rss("youtube", creator, source, response.text)

    async def _resolve_youtube_source(self, creator: str) -> str:
        creator = creator.strip()
        if creator.startswith("http"):
            if "feeds/videos.xml" in creator:
                return creator
            page = await self.client.get(creator, headers={"User-Agent": "DevVerseAssistant/1.0"})
            page.raise_for_status()
            match = re.search(r'https://www\.youtube\.com/feeds/videos\.xml\?channel_id=[A-Za-z0-9_-]+', page.text)
            if match:
                return match.group(0)
        if creator.startswith("UC"):
            return YOUTUBE_RSS.format(channel_id=creator)
        if creator.startswith("@"):
            page = await self.client.get(f"https://www.youtube.com/{creator}", headers={"User-Agent": "DevVerseAssistant/1.0"})
            page.raise_for_status()
            match = re.search(r'https://www\.youtube\.com/feeds/videos\.xml\?channel_id=[A-Za-z0-9_-]+', page.text)
            if match:
                return match.group(0)
        return f"https://www.youtube.com/feeds/videos.xml?user={creator.lstrip('@')}"

    async def _fetch_instagram(self, creator: str) -> list[MonitorItem]:
        provider = settings.instagram_provider
        if provider == "disabled":
            raise RuntimeError("Instagram configurado, mas provider nao definido. Configure INSTAGRAM_PROVIDER=rss_bridge, apify ou manual_public_page.")
        if provider == "rss_bridge":
            return await self._fetch_instagram_rss_bridge(creator)
        if provider == "apify":
            return await self._fetch_instagram_apify(creator)
        if provider == "manual_public_page":
            return await self._fetch_instagram_public_page(creator)
        raise RuntimeError(f"INSTAGRAM_PROVIDER invalido: {provider}")

    async def _fetch_instagram_rss_bridge(self, creator: str) -> list[MonitorItem]:
        username = creator.lstrip("@")
        template = settings.rss_bridge_url or settings.instagram_rss_template
        if not template:
            raise RuntimeError("Instagram RSS Bridge nao configurado. Defina RSS_BRIDGE_URL ou INSTAGRAM_RSS_TEMPLATE.")
        source = template.format(username=username)
        response = await self.client.get(source, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse_rss("instagram", creator, source, response.text)

    async def _fetch_instagram_apify(self, creator: str) -> list[MonitorItem]:
        if not settings.apify_token:
            raise RuntimeError("Instagram provider apify selecionado, mas APIFY_TOKEN esta vazio.")
        username = creator.lstrip("@")
        url = "https://api.apify.com/v2/acts/apify~instagram-post-scraper/run-sync-get-dataset-items"
        payload = {"directUrls": [f"https://www.instagram.com/{username}/"], "resultsLimit": 5}
        response = await self.client.post(url, params={"token": settings.apify_token}, json=payload, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        rows = response.json() if isinstance(response.json(), list) else []
        items: list[MonitorItem] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            post_url = str(row.get("url") or row.get("displayUrl") or "").strip()
            external_id = str(row.get("id") or row.get("shortCode") or post_url)
            title = str(row.get("caption") or row.get("type") or "Post Instagram").strip()
            if post_url:
                items.append(self._instagram_item(creator, "apify", title, post_url, external_id, str(row.get("timestamp") or "")))
        return items

    async def _fetch_instagram_public_page(self, creator: str) -> list[MonitorItem]:
        username = creator.lstrip("@")
        source = f"https://www.instagram.com/{username}/"
        response = await self.client.get(source, headers={"User-Agent": "Mozilla/5.0 DevVerseAssistant/1.0"})
        response.raise_for_status()
        codes = re.findall(r'/(?:p|reel)/([A-Za-z0-9_-]+)/', response.text)
        items: list[MonitorItem] = []
        for code in dict.fromkeys(codes):
            url = f"https://www.instagram.com/p/{code}/"
            items.append(self._instagram_item(creator, "manual_public_page", f"Post de {creator}", url, code, ""))
            if len(items) >= 5:
                break
        if not items:
            raise RuntimeError("Instagram bloqueou a pagina publica ou nao retornou posts recentes.")
        return items

    def _instagram_item(self, creator: str, source: str, title: str, url: str, external_id: str, published_at: str) -> MonitorItem:
        return MonitorItem(
            type="social",
            title=title[:250],
            url=url,
            source=source,
            summary="",
            metadata={
                "platform": "instagram",
                "creator": creator,
                "thumbnail": "",
                "published_at": published_at,
                "external_id": external_id,
                "source": source,
            },
        )

    def _parse_rss(self, platform: str, creator: str, source: str, xml_text: str) -> list[MonitorItem]:
        root = ET.fromstring(xml_text)
        items: list[MonitorItem] = []
        ns = {
            "atom": "http://www.w3.org/2005/Atom",
            "media": "http://search.yahoo.com/mrss/",
        }
        for entry in root.findall("atom:entry", ns) or root.findall(".//item"):
            title = (entry.findtext("atom:title", default="", namespaces=ns) or entry.findtext("title", default="")).strip()
            link_node = entry.find("atom:link", ns)
            url = link_node.attrib.get("href", "") if link_node is not None else (entry.findtext("link", default="").strip())
            summary = (entry.findtext("atom:summary", default="", namespaces=ns) or entry.findtext("description", default="")).strip()
            published_at = (
                entry.findtext("atom:published", default="", namespaces=ns)
                or entry.findtext("atom:updated", default="", namespaces=ns)
                or entry.findtext("pubDate", default="")
                or datetime.utcnow().isoformat()
            ).strip()
            external_id = (entry.findtext("atom:id", default="", namespaces=ns) or url).strip()
            if title and url:
                items.append(
                    MonitorItem(
                        type="social",
                        title=title,
                        url=url,
                        source=source,
                        summary=summary[:600],
                        metadata={
                            "platform": platform,
                            "creator": creator,
                            "category": "Conteudo",
                            "published_at": published_at,
                            "external_id": external_id,
                            "source": source,
                        },
                    )
                )
        return items
