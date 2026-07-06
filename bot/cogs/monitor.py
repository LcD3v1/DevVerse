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
    @app_commands.choices(
        frequencia_minutos=[
            app_commands.Choice(name="30 minutos", value=30),
            app_commands.Choice(name="1 hora", value=60),
            app_commands.Choice(name="3 horas", value=180),
        ]
    )
    @admin_check()
    async def setup(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        fontes: str = "linkedin,indeed,existing",
        areas: str = "",
        niveis: str = "",
        modelos: str = "",
        frequencia_minutos: int = 60,
    ) -> None:
        await self.cog.upsert_jobs_monitor(interaction, canal.id, fontes, areas, niveis, modelos, frequencia_minutos)


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

    async def upsert_jobs_monitor(
        self,
        interaction: discord.Interaction,
        channel_id: int,
        sources: str,
        areas: str,
        levels: str,
        models: str,
        frequency_minutes: int,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        frequency_minutes = max(frequency_minutes, 30)
        config = {
            "sources": self._split_csv(sources) or ["linkedin", "indeed", "existing"],
            "areas": self._split_csv(areas),
            "levels": self._split_csv(levels),
            "models": self._split_csv(models),
        }
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
            (interaction.guild.id, "jobs", "career", channel_id, json.dumps(config), frequency_minutes),
        )
        await interaction.response.send_message(
            embed=make_embed(
                "Jobs Monitor configurado",
                "\n".join(
                    [
                        f"Canal: <#{channel_id}>",
                        f"Fontes: {', '.join(config['sources'])}",
                        f"Areas: {', '.join(config['areas']) or 'todas'}",
                        f"Niveis: {', '.join(config['levels']) or 'todos'}",
                        f"Modelos: {', '.join(config['models']) or 'todos'}",
                        f"Frequencia: {frequency_minutes} minutos.",
                    ]
                ),
            ),
            ephemeral=True,
        )

    async def status(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        rows = await self.bot.db.fetchall(
            "SELECT id, type, source, channel_id, filters, frequency_minutes, last_check, last_error, last_result_count FROM monitors WHERE guild_id = ? AND enabled = 1 ORDER BY id",
            (interaction.guild.id,),
        )
        if not rows:
            await interaction.response.send_message(embed=make_embed("Monitor status", "Nenhuma fonte ativa."), ephemeral=True)
            return
        lines = []
        for row in rows[:20]:
            error = row["last_error"] or "sem erros"
            last_check = row["last_check"] or "ainda nao executado"
            if row["type"] == "jobs":
                config = self._load_json(row["filters"])
                sources = config.get("sources", []) if isinstance(config, dict) else []
                source_lines = "\n".join(f"\u2705 {self._source_label(source)}" for source in sources) or "todas"
                lines.append(
                    "\n".join(
                        [
                            f"\U0001f4bc Jobs Monitor `#{row['id']}`",
                            f"Canal: <#{row['channel_id']}>",
                            f"Fontes:\n{source_lines}",
                            f"Ultima busca: {last_check}",
                            f"Novas vagas encontradas: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
            else:
                lines.append(f"`#{row['id']}` {row['type']} | {row['source']} | <#{row['channel_id']}> | {row['frequency_minutes']} min | {last_check} | {error}")
        await interaction.response.send_message(embed=make_embed("Monitor status", "\n\n".join(lines)), ephemeral=True)

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

    def _split_csv(self, value: str) -> list[str]:
        return [part.strip().lower() for part in value.split(",") if part.strip()]

    def _load_json(self, value: str):
        try:
            return json.loads(value) if value else {}
        except json.JSONDecodeError:
            return {}

    def _source_label(self, source: str) -> str:
        return {"linkedin": "LinkedIn", "indeed": "Indeed", "existing": "Outras"}.get(source, source.title())


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MonitorCog(bot))
