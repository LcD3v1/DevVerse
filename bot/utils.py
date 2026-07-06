from __future__ import annotations

import logging
import math
from datetime import datetime, timezone

import discord


logger = logging.getLogger("devverse")
BRAND_COLOR = discord.Color.from_rgb(87, 111, 230)
SUCCESS_COLOR = discord.Color.from_rgb(34, 197, 94)
WARN_COLOR = discord.Color.from_rgb(245, 158, 11)
ERROR_COLOR = discord.Color.from_rgb(239, 68, 68)


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def make_embed(title: str, description: str = "", color: discord.Color = BRAND_COLOR) -> discord.Embed:
    embed = discord.Embed(title=title, description=description, color=color, timestamp=utcnow())
    embed.set_footer(text="DevVerse Assistant")
    return embed


def level_from_xp(xp: int) -> int:
    return int(math.sqrt(max(xp, 0) / 100))


def progress_bar(current: int, total: int, width: int = 12) -> str:
    total = max(total, 1)
    filled = min(width, int((current / total) * width))
    return "█" * filled + "░" * (width - filled)


def split_message(text: str, limit: int = 1900) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.splitlines() or [text]:
        if len(current) + len(line) + 1 > limit:
            chunks.append(current)
            current = line
        else:
            current = f"{current}\n{line}" if current else line
    if current:
        chunks.append(current)
    return chunks


async def send_long(interaction: discord.Interaction, text: str, title: str = "Resposta") -> None:
    chunks = split_message(text)
    first = make_embed(title, chunks[0])
    if interaction.response.is_done():
        await interaction.followup.send(embed=first)
    else:
        await interaction.response.send_message(embed=first)
    for chunk in chunks[1:]:
        await interaction.followup.send(chunk)
