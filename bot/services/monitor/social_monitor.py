from __future__ import annotations

import logging
import re
import xml.etree.ElementTree as ET

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
        if not settings.instagram_rss_template:
            logger.info("Monitor Instagram sem INSTAGRAM_RSS_TEMPLATE configurado; pulando %s", creator)
            return []
        source = settings.instagram_rss_template.format(username=creator.lstrip("@"))
        response = await self.client.get(source, headers={"User-Agent": "DevVerseAssistant/1.0"})
        response.raise_for_status()
        return self._parse_rss("instagram", creator, source, response.text)

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
            if title and url:
                items.append(
                    MonitorItem(
                        type="social",
                        title=title,
                        url=url,
                        source=source,
                        summary=summary[:600],
                        metadata={"platform": platform, "creator": creator, "category": "Conteudo"},
                    )
                )
        return items
