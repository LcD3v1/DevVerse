from __future__ import annotations

import logging
from dataclasses import dataclass

import discord
from discord.ext import commands

from bot.services.monitor.models import MonitorItem
from bot.utils import utcnow


logger = logging.getLogger("devverse.monitor.notifications")


@dataclass(slots=True)
class NotificationSendResult:
    status: str
    sent: bool = False
    duplicate: bool = False
    error: str = ""


class NotificationService:
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    async def was_sent(self, item: MonitorItem) -> bool:
        unique_hash = item.metadata.get("unique_hash", "")
        if unique_hash:
            row = await self.bot.db.fetchone(
                "SELECT id FROM notifications WHERE type = ? AND unique_hash = ?",
                (item.type, unique_hash),
            )
            if row is not None:
                return True
        external_id = item.metadata.get("external_id", item.url)
        sent_row = await self.bot.db.fetchone(
            "SELECT id FROM sent_notifications WHERE type = ? AND (external_id = ? OR url = ?)",
            (item.type, external_id, item.url),
        )
        if sent_row:
            return True
        row = await self.bot.db.fetchone("SELECT id FROM notifications WHERE type = ? AND url = ?", (item.type, item.url))
        return row is not None

    async def send(self, channel_id: int, item: MonitorItem) -> NotificationSendResult:
        if await self.was_sent(item):
            return NotificationSendResult(status="duplicate", duplicate=True)
        try:
            channel = self.bot.get_channel(channel_id) or await self.bot.fetch_channel(channel_id)
        except (discord.NotFound, discord.Forbidden, discord.HTTPException) as exc:
            logger.warning("Canal %s nao encontrado para notificacao: %s", channel_id, exc)
            return NotificationSendResult(status="missing_channel", error=str(exc))
        if not hasattr(channel, "send"):
            logger.warning("Canal %s nao aceita mensagens", channel_id)
            return NotificationSendResult(status="missing_channel", error="Canal nao aceita mensagens")
        embed = self._build_embed(item)
        try:
            await channel.send(embed=embed)
        except discord.HTTPException as exc:
            logger.exception("Falha ao enviar notificacao no canal %s", channel_id)
            return NotificationSendResult(status="error", error=str(exc))
        await self._record(item)
        return NotificationSendResult(status="sent", sent=True)

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
        await self.bot.db.execute(
            "INSERT OR IGNORE INTO sent_notifications (type, source, external_id, url, sent_at) VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)",
            (item.type, item.metadata.get("source", item.source), item.metadata.get("external_id", item.url), item.url),
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
        elif item.type == "freelance":
            await self.bot.db.execute(
                "INSERT OR IGNORE INTO freelance_opportunities (platform, external_id, title, url, budget, skills) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    item.metadata.get("platform", item.source),
                    item.metadata.get("external_id", item.url),
                    item.title,
                    item.url,
                    item.metadata.get("budget", ""),
                    item.metadata.get("skills", ""),
                ),
            )

    def _build_embed(self, item: MonitorItem) -> discord.Embed:
        if item.type == "job":
            color = discord.Color.green()
            embed = discord.Embed(title="\U0001f680 Nova vaga encontrada!", color=color, timestamp=utcnow())
            embed.add_field(name="\U0001f4bc Cargo", value=item.title, inline=False)
            embed.add_field(name="\U0001f3e2 Empresa", value=item.metadata.get("company", "Nao informado"), inline=False)
            embed.add_field(name="\U0001f30e Regiao", value=item.metadata.get("region", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f4cd Local", value=item.metadata.get("location", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f310 Modalidade", value=item.metadata.get("model", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f4da Senioridade", value=item.metadata.get("seniority", "Nao informado"), inline=True)
            embed.add_field(name="\U0001f6e0 Tecnologias", value=item.metadata.get("technologies", "Nao informado"), inline=False)
            embed.add_field(name="\U0001f517 Link", value=f"[Abrir vaga]({item.url})", inline=False)
            embed.add_field(name="Fonte", value=item.metadata.get("source_label", item.source.title()), inline=True)
            embed.set_footer(text="DevVerse Career Monitor")
            return embed
        elif item.type == "hackathon":
            embed = discord.Embed(title="\U0001f3c6 Novo hackathon encontrado!", color=discord.Color.purple(), timestamp=utcnow())
            embed.add_field(name="Nome", value=self._clean_field(item.title), inline=False)
            embed.add_field(name="Categoria", value=self._clean_field(item.metadata.get("category")), inline=False)
            embed.add_field(name="Tecnologias", value=self._clean_field(item.metadata.get("technologies")), inline=False)
            embed.add_field(name="Premiacao", value=self._clean_field(item.metadata.get("prize")), inline=True)
            embed.add_field(name="Data", value=self._clean_field(item.metadata.get("date")), inline=True)
            embed.add_field(name="Formato", value=self._clean_field(item.metadata.get("format")), inline=True)
            embed.add_field(name="Inscricao", value=f"[Abrir pagina]({item.url})", inline=False)
        elif item.type == "freelance":
            embed = discord.Embed(title="\U0001f680 Novo freelance encontrado!", color=discord.Color.teal(), timestamp=utcnow())
            embed.add_field(name="\U0001f4bc Projeto", value=self._clean_field(item.title), inline=False)
            embed.add_field(name="\U0001f464 Cliente/Empresa", value=self._clean_field(item.metadata.get("client_or_company")), inline=True)
            embed.add_field(name="\U0001f310 Plataforma", value=self._clean_field(item.metadata.get("platform", item.source)), inline=True)
            embed.add_field(name="\U0001f4b0 Orcamento", value=self._clean_field(item.metadata.get("budget")), inline=True)
            embed.add_field(name="\U0001f6e0 Skills", value=self._clean_field(item.metadata.get("skills")), inline=False)
            embed.add_field(name="\U0001f4cd Local/Remoto", value=self._clean_field(item.metadata.get("location", "Remote")), inline=True)
            embed.add_field(name="\U0001f517 Link", value=f"[Abrir oportunidade]({item.url})", inline=False)
            embed.set_footer(text="DevVerse Freelance Monitor")
            return embed
        else:
            platform = item.metadata.get("platform", "").lower()
            title = "\U0001f3a5 Novo conteudo no Instagram!" if platform == "instagram" else "\U0001f3a5 Novo conteudo publicado!"
            embed = discord.Embed(title=title, color=discord.Color.orange(), timestamp=utcnow())
            embed.add_field(name="Criador", value=item.metadata.get("creator", "Nao informado"), inline=True)
            embed.add_field(name="Titulo", value=item.title, inline=False)
            if item.metadata.get("published_at"):
                embed.add_field(name="Publicado", value=item.metadata.get("published_at", ""), inline=True)
            if item.summary:
                embed.add_field(name="Resumo", value=item.summary, inline=False)
            embed.add_field(name="Ver post" if platform == "instagram" else "Link", value=f"[Abrir conteudo]({item.url})", inline=False)
        embed.set_footer(text="DevVerse Social Monitor" if item.type == "social" else "DevVerse System")
        return embed

    def _clean_field(self, value: object, fallback: str = "Nao informado") -> str:
        text = str(value or "").strip()
        return text[:1024] if text else fallback
