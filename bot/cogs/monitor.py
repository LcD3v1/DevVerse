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
            app_commands.Choice(name="5 minutos", value=5),
            app_commands.Choice(name="15 minutos", value=15),
            app_commands.Choice(name="30 minutos", value=30),
            app_commands.Choice(name="1 hora", value=60),
        ]
    )
    @admin_check()
    async def setup(
        self,
        interaction: discord.Interaction,
        canal: discord.TextChannel,
        fontes: str = "linkedin,indeed,existing",
        frequencia_minutos: int = 5,
    ) -> None:
        await self.cog.upsert_jobs_monitor(interaction, canal.id, fontes, frequencia_minutos)

    @app_commands.command(name="interval", description="Altera o intervalo do monitor de vagas.")
    @app_commands.choices(
        minutos=[
            app_commands.Choice(name="5 minutos", value=5),
            app_commands.Choice(name="15 minutos", value=15),
            app_commands.Choice(name="30 minutos", value=30),
            app_commands.Choice(name="1 hora", value=60),
        ]
    )
    @admin_check()
    async def interval(self, interaction: discord.Interaction, minutos: int) -> None:
        await self.cog.update_jobs_interval(interaction, minutos)


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
    run_group = app_commands.Group(name="run", description="Executa monitores imediatamente.")

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

    @run_group.command(name="jobs", description="Executa o monitor de vagas agora.")
    @admin_check()
    async def run_jobs(self, interaction: discord.Interaction) -> None:
        await self.cog.run_monitor_now(interaction, "jobs", "\U0001f680 Executando monitor de vagas...")

    @run_group.command(name="hackathons", description="Executa o monitor de hackathons agora.")
    @admin_check()
    async def run_hackathons(self, interaction: discord.Interaction) -> None:
        await self.cog.run_monitor_now(interaction, "hackathons", "\U0001f3c6 Executando monitor de hackathons...")

    @run_group.command(name="instagram", description="Executa o monitor de Instagram agora.")
    @admin_check()
    async def run_instagram(self, interaction: discord.Interaction) -> None:
        await self.cog.run_monitor_now(interaction, "instagram", "\U0001f3a5 Executando monitor de Instagram...")


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
        frequency_minutes: int,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        frequency_minutes = max(frequency_minutes, 5)
        config = {
            "sources": self._split_csv(sources) or ["linkedin", "indeed", "existing"],
            "areas": "all_technology",
            "levels": "all",
            "models": "all",
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
                        "Areas: todas as areas de tecnologia",
                        f"Frequencia: {frequency_minutes} minutos.",
                    ]
                ),
            ),
            ephemeral=True,
        )

    async def update_jobs_interval(self, interaction: discord.Interaction, minutes: int) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        cursor = await self.bot.db.execute(
            "UPDATE monitors SET frequency_minutes = ? WHERE guild_id = ? AND type = ? AND enabled = 1",
            (minutes, interaction.guild.id, "jobs"),
        )
        if not cursor.rowcount:
            await interaction.response.send_message("Nenhum monitor de vagas ativo. Use `/jobs setup` primeiro.", ephemeral=True)
            return
        await interaction.response.send_message(embed=make_embed("Intervalo atualizado", f"Monitor de vagas rodando a cada {minutes} minutos."), ephemeral=True)

    async def run_monitor_now(self, interaction: discord.Interaction, monitor_type: str, title: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        stats = await self.manager.run_now(interaction.guild.id, monitor_type)
        await interaction.followup.send(
            embed=make_embed(
                title,
                f"Encontradas:\n{stats.found} novas vagas\n\nEnviadas:\n{stats.sent}\n\nErros:\n{stats.errors}"
                if monitor_type == "jobs"
                else f"Encontrados:\n{stats.found}\n\nEnviados:\n{stats.sent}\n\nErros:\n{stats.errors}",
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
        sections = {"jobs": [], "hackathons": [], "content": []}
        for row in rows[:20]:
            error = row["last_error"] or "sem erros"
            last_check = row["last_check"] or "ainda nao executado"
            if row["type"] == "jobs":
                config = self._load_json(row["filters"])
                sources = config.get("sources", []) if isinstance(config, dict) else []
                source_lines = "\n".join(f"\u2705 {self._source_label(source)}" for source in sources) or "todas"
                sections["jobs"].append(
                    "\n".join(
                        [
                            "\U0001f4bc Jobs",
                            "Status: \U0001f7e2 Online",
                            f"Fontes:\n{source_lines}",
                            f"Ultima execucao: {last_check}",
                            f"Novas vagas encontradas: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
            elif row["type"] == "hackathons":
                sections["hackathons"].append(
                    "\n".join(
                        [
                            "\U0001f3c6 Hackathons",
                            "Status: \U0001f7e2 Online",
                            f"Ultima execucao: {last_check}",
                            f"Novos eventos encontrados: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
            else:
                sections["content"].append(
                    "\n".join(
                        [
                            "\U0001f3a5 Conteudo",
                            "Status: \U0001f7e2 Online",
                            f"Fonte: {row['type']} | {row['source']}",
                            f"Ultima execucao: {last_check}",
                            f"Novos conteudos encontrados: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
        lines = ["\U0001f4e1 DevVerse Monitor"]
        for key in ("jobs", "hackathons", "content"):
            lines.extend(sections[key] or [self._empty_status(key)])
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

    def _empty_status(self, key: str) -> str:
        labels = {"jobs": "\U0001f4bc Jobs", "hackathons": "\U0001f3c6 Hackathons", "content": "\U0001f3a5 Conteudo"}
        return f"{labels[key]}\nStatus: \U0001f534 Offline"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MonitorCog(bot))
