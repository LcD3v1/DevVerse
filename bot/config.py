from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
DEFAULT_INSTAGRAM_RSS_TEMPLATE = "https://rsshub.app/instagram/user/{username}"


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _int_or_default(value: str | None, default: int) -> int:
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _ids(value: str | None) -> set[int]:
    if not value:
        return set()
    return {int(part.strip()) for part in value.split(",") if part.strip().isdigit()}


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int | None
    command_prefix: str
    ai_provider: str
    ai_gateway_url: str
    ollama_host: str
    ollama_model: str
    ai_channel_name: str
    database_path: Path
    owner_ids: set[int]
    enable_github: bool
    github_webhook_secret: str
    monitor_enabled: bool
    monitor_interval_minutes: int
    jobs_default_sources: tuple[str, ...]
    jobs_source_urls: tuple[str, ...]
    jobs_default_location: str
    hackathon_source_urls: tuple[str, ...]
    freelance_source_urls: tuple[str, ...]
    instagram_provider: str
    instagram_rss_template: str
    apify_token: str
    rss_bridge_url: str


settings = Settings(
    token=os.getenv("DISCORD_TOKEN", ""),
    guild_id=_int_or_none(os.getenv("GUILD_ID")),
    command_prefix=os.getenv("COMMAND_PREFIX", "!"),
    ai_provider=os.getenv("AI_PROVIDER", "ollama"),
    ai_gateway_url=os.getenv("AI_GATEWAY_URL", "").rstrip("/"),
    ollama_host=os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/"),
    ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5-coder"),
    ai_channel_name=os.getenv("AI_CHANNEL_NAME", "🤖・ai-assistant"),
    database_path=BASE_DIR / os.getenv("DATABASE_PATH", "data/database.sqlite3"),
    owner_ids=_ids(os.getenv("OWNER_IDS")),
    enable_github=os.getenv("ENABLE_GITHUB", "false").lower() == "true",
    github_webhook_secret=os.getenv("GITHUB_WEBHOOK_SECRET", ""),
    monitor_enabled=os.getenv("MONITOR_ENABLED", "true").lower() == "true",
    monitor_interval_minutes=_int_or_default(os.getenv("MONITOR_INTERVAL_MINUTES"), 5),
    jobs_default_sources=tuple(
        part.strip().lower()
        for part in os.getenv("JOBS_DEFAULT_SOURCES", "linkedin,indeed,public").split(",")
        if part.strip()
    ),
    jobs_source_urls=tuple(
        part.strip()
        for part in os.getenv("JOBS_SOURCE_URLS", "https://remoteok.com/api").split(",")
        if part.strip()
    ),
    jobs_default_location=os.getenv("JOBS_DEFAULT_LOCATION", "Worldwide"),
    hackathon_source_urls=tuple(
        part.strip()
        for part in os.getenv("HACKATHON_SOURCE_URLS", "https://devpost.com/api/hackathons").split(",")
        if part.strip()
    ),
    freelance_source_urls=tuple(
        part.strip()
        for part in os.getenv("FREELANCE_SOURCE_URLS", "https://remoteok.com/api").split(",")
        if part.strip()
    ),
    instagram_provider=os.getenv("INSTAGRAM_PROVIDER", "disabled").strip().lower(),
    instagram_rss_template=os.getenv("INSTAGRAM_RSS_TEMPLATE", DEFAULT_INSTAGRAM_RSS_TEMPLATE) or DEFAULT_INSTAGRAM_RSS_TEMPLATE,
    apify_token=os.getenv("APIFY_TOKEN", ""),
    rss_bridge_url=os.getenv("RSS_BRIDGE_URL", "").rstrip("/"),
)
