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
            "INSERT OR IGNORE INTO notifications (type, title, url) VALUES (?, ?, ?)",
            (item.type, item.title, item.url),
        )
        if item.type == "job":
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO jobs (title, company, url) VALUES (?, ?, ?)",
                (item.title, item.metadata.get("company", ""), item.url),
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
            embed = discord.Embed(title="\U0001f680 DevVerse Alert", description="Nova oportunidade encontrada!", color=color, timestamp=utcnow())
            embed.add_field(name="\U0001f4bb Cargo", value=item.title, inline=False)
            embed.add_field(name="Empresa", value=item.metadata.get("company", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f6e0 Tecnologias", value=item.metadata.get("technologies", "Nao informado"), inline=False)
            embed.add_field(name="\U0001f4cd Local", value=item.metadata.get("location", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f30e Modelo", value=item.metadata.get("model", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f517 Link da vaga", value=item.url, inline=False)
            embed.add_field(name="\U0001f4c5 Data encontrada", value=utcnow().strftime("%Y-%m-%d %H:%M UTC"), inline=False)
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
