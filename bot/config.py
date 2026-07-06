from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _int_or_none(value: str | None) -> int | None:
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


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
)
