from __future__ import annotations

import logging

import discord
from discord.ext import commands

from bot.services.monitor.models import MonitorItem
from bot.utils import utcnow


logger = logging.getLogger("devverse.monitor.notifications")


class NotificationService:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def was_sent(self, item: MonitorItem) -> bool:
        unique_hash = item.metadata.get("unique_hash", "")
        if item.type == "job" and unique_hash:
            row = await self.bot.db.fetchone(
                "SELECT id FROM notifications WHERE type = ? AND unique_hash = ?",
                (item.type, unique_hash),
            )
            return row is not None
        row = await self.bot.db.fetchone("SELECT id FROM notifications WHERE type = ? AND url = ?", (item.type, item.url))
        return row is not None

    async def send(self, channel_id: int, item: MonitorItem) -> bool:
        if await self.was_sent(item):
            return False
        channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        if not hasattr(channel, "send"):
            logger.warning("Canal %s nao aceita mensagens", channel_id)
            return False
        embed = self._build_embed(item)
        await channel.send(embed=embed)
        await self._record(item)
        return True

    async def _record(self, item: MonitorItem) -> None:
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO notifications (type, title, url, source, external_id, unique_hash) VALUES (?, ?, ?, ?, ?, ?)",
            (
                item.type,
                item.title,
                item.url,
                item.metadata.get("source", item.source),
                item.metadata.get("external_id", ""),
                item.metadata.get("unique_hash", ""),
            ),
        )
        if item.type == "job":
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO jobs (title, company, url, source, external_id, unique_hash) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item.title,
                    item.metadata.get("company", ""),
                    item.url,
                    item.metadata.get("source", item.source),
                    item.metadata.get("external_id", ""),
                    item.metadata.get("unique_hash", ""),
                ),
            )
        elif item.type == "hackathon":
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO hackathons (name, url) VALUES (?, ?)",
                (item.title, item.url),
            )
        elif item.type == "social":
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO social_posts (platform, creator, url) VALUES (?, ?, ?)",
                (item.metadata.get("platform", ""), item.metadata.get("creator", ""), item.url),
            )

    def _build_embed(self, item: MonitorItem) -> discord.Embed:
        if item.type == "job":
            color = discord.Color.blue()
            embed = discord.Embed(title="\U0001f680 Nova vaga encontrada!", color=color, timestamp=utcnow())
            embed.add_field(name="\U0001f4bc Cargo", value=item.title, inline=False)
            embed.add_field(name="\U0001f3e2 Empresa", value=item.metadata.get("company", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f310 Fonte", value=item.metadata.get("source_label", item.source.title()), inline=True)
            embed.add_field(name="\U0001f6e0 Tecnologias", value=item.metadata.get("technologies", "Nao informado"), inline=False)
            embed.add_field(name="\U0001f4cd Local", value=item.metadata.get("location", "Nao informado"), inline=False)
            embed.add_field(name="\U0001f517 Aplicar", value=item.url, inline=False)
            embed.set_footer(text="DevVerse Career Monitor")
            return embed
        elif item.type == "hackathon":
            embed = discord.Embed(title="\U0001f680 DevVerse Alert", description="\U0001f3c6 Novo Hackathon encontrado!", color=discord.Color.purple(), timestamp=utcnow())
            embed.add_field(name="Nome", value=item.title, inline=False)
            embed.add_field(name="Categoria", value=item.metadata.get("category", "Nao informado"), inline=True)
            embed.add_field(name="Tecnologias", value=item.metadata.get("technologies", "Nao informado"), inline=True)
            embed.add_field(name="Data", value=item.metadata.get("date", "Nao informado"), inline=True)
            embed.add_field(name="Premiacao", value=item.metadata.get("prize", "Nao informado"), inline=True)
            embed.add_field(name="Formato", value=item.metadata.get("format", "Nao informado"), inline=True)
            embed.add_field(name="Link de inscricao", value=item.url, inline=False)
        else:
            embed = discord.Embed(title="\U0001f680 DevVerse Alert", description="\U0001f3a5 Novo conteudo publicado!", color=discord.Color.orange(), timestamp=utcnow())
            embed.add_field(name="Criador", value=item.metadata.get("creator", "Nao informado"), inline=True)
            embed.add_field(name="Titulo", value=item.title, inline=False)
            embed.add_field(name="Categoria", value=item.metadata.get("category", "Conteudo"), inline=True)
            embed.add_field(name="Resumo", value=item.summary or "Resumo automatico preparado para IA futura.", inline=False)
            embed.add_field(name="Link", value=item.url, inline=False)
        embed.set_footer(text="DevVerse Assistant")
        return embed
