from __future__ import annotations

import json

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import settings
from bot.permissions import admin_check
from bot.services.monitor.monitor_manager import MonitorManager
from bot.utils import make_embed


class JobsGroup(app_commands.Group):
    def __init__(self, cog: "MonitorCog") -> None:
        super().__init__(name="jobs", description="Configura monitoramento de vagas.")
        self.cog = cog

    @app_commands.command(name="setup", description="Configura alertas automaticos de vagas.")
    @admin_check()
    async def setup(self, interaction: discord.Interaction, canal: discord.TextChannel, areas: str = "", frequencia_minutos: int = 60) -> None:
        await self.cog.upsert_monitor(interaction, "jobs", "internet", canal.id, areas, frequencia_minutos)


class HackathonGroup(app_commands.Group):
    def __init__(self, cog: "MonitorCog") -> None:
        super().__init__(name="hackathon", description="Configura monitoramento de hackathons.")
        self.cog = cog

    @app_commands.command(name="setup", description="Configura alertas automaticos de hackathons.")
    @admin_check()
    async def setup(self, interaction: discord.Interaction, canal: discord.TextChannel, categorias: str = "", frequencia_minutos: int = 720) -> None:
        await self.cog.upsert_monitor(interaction, "hackathons", "internet", canal.id, categorias, frequencia_minutos)


class MonitorGroup(app_commands.Group):
    def __init__(self, cog: "MonitorCog") -> None:
        super().__init__(name="monitor", description="Gerencia monitores externos.")
        self.cog = cog

    instagram = app_commands.Group(name="instagram", description="Monitora perfis do Instagram.")
    youtube = app_commands.Group(name="youtube", description="Monitora canais do YouTube.")

    @instagram.command(name="adicionar", description="Adiciona um perfil do Instagram ao monitoramento.")
    @admin_check()
    async def instagram_add(self, interaction: discord.Interaction, perfil: str, canal: discord.TextChannel, frequencia_minutos: int = 120) -> None:
        await self.cog.upsert_monitor(interaction, "instagram", perfil, canal.id, "", frequencia_minutos)

    @youtube.command(name="adicionar", description="Adiciona um canal do YouTube ao monitoramento.")
    @admin_check()
    async def youtube_add(self, interaction: discord.Interaction, canal_youtube: str, canal: discord.TextChannel, frequencia_minutos: int = 120) -> None:
        await self.cog.upsert_monitor(interaction, "youtube", canal_youtube, canal.id, "", frequencia_minutos)

    @app_commands.command(name="status", description="Mostra fontes monitoradas, ultimo check e erros.")
    @admin_check()
    async def status(self, interaction: discord.Interaction) -> None:
        await self.cog.status(interaction)

    @app_commands.command(name="remove", description="Remove uma fonte monitorada pelo ID.")
    @admin_check()
    async def remove(self, interaction: discord.Interaction, monitor_id: int) -> None:
        await self.cog.remove(interaction, monitor_id)


class MonitorCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = MonitorManager(bot)
        bot.tree.add_command(JobsGroup(self))
        bot.tree.add_command(HackathonGroup(self))
        bot.tree.add_command(MonitorGroup(self))
        if settings.monitor_enabled:
            self.monitor_task.change_interval(minutes=max(settings.monitor_interval_minutes, 1))
            self.monitor_task.start()

    async def cog_unload(self) -> None:
        if self.monitor_task.is_running():
            self.monitor_task.cancel()
        await self.manager.close()

    async def upsert_monitor(
        self,
        interaction: discord.Interaction,
        monitor_type: str,
        source: str,
        channel_id: int,
        filters: str,
        frequency_minutes: int,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        frequency_minutes = max(frequency_minutes, 5)
        filter_list = [part.strip().lower() for part in filters.split(",") if part.strip()]
        await self.bot.db.execute(
            """
            INSERT INTO monitors (guild_id, type, source, channel_id, filters, frequency_minutes)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(guild_id, type, source) DO UPDATE SET
                channel_id = excluded.channel_id,
                filters = excluded.filters,
                frequency_minutes = excluded.frequency_minutes,
                enabled = 1
            """,
            (interaction.guild.id, monitor_type, source.strip(), channel_id, json.dumps(filter_list), frequency_minutes),
        )
        await interaction.response.send_message(
            embed=make_embed(
                "Monitor configurado",
                f"Tipo: `{monitor_type}`\nFonte: `{source}`\nCanal: <#{channel_id}>\nFrequencia: {frequency_minutes} minutos.",
            ),
            ephemeral=True,
        )

    async def status(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        rows = await self.bot.db.fetchall(
            "SELECT id, type, source, channel_id, frequency_minutes, last_check, last_error FROM monitors WHERE guild_id = ? AND enabled = 1 ORDER BY id",
            (interaction.guild.id,),
        )
        if not rows:
            await interaction.response.send_message(embed=make_embed("Monitor status", "Nenhuma fonte ativa."), ephemeral=True)
            return
        lines = []
        for row in rows[:20]:
            error = row["last_error"] or "sem erros"
            last_check = row["last_check"] or "ainda nao executado"
            lines.append(f"`#{row['id']}` {row['type']} | {row['source']} | <#{row['channel_id']}> | {row['frequency_minutes']} min | {last_check} | {error}")
        await interaction.response.send_message(embed=make_embed("Monitor status", "\n".join(lines)), ephemeral=True)

    async def remove(self, interaction: discord.Interaction, monitor_id: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        cursor = await self.bot.db.execute(
            "UPDATE monitors SET enabled = 0 WHERE id = ? AND guild_id = ?",
            (monitor_id, interaction.guild.id),
        )
        message = "Monitor removido." if cursor.rowcount else "Monitor nao encontrado neste servidor."
        await interaction.response.send_message(embed=make_embed("Monitor remove", message), ephemeral=True)

    @tasks.loop(minutes=5)
    async def monitor_task(self) -> None:
        await self.manager.run_due_monitors()

    @monitor_task.before_loop
    async def before_monitor_task(self) -> None:
        await self.bot.wait_until_ready()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MonitorCog(bot))
