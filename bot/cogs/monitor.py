from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

import discord
from discord import app_commands
from discord.ext import commands, tasks

from bot.config import settings
from bot.permissions import admin_check
from bot.services.monitor.monitor_manager import MonitorManager
from bot.utils import make_embed


logger = logging.getLogger("devverse.monitor.cog")


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
        frequencia_minutos: int = 5,
    ) -> None:
        await self.cog.upsert_jobs_monitor(interaction, canal.id, frequencia_minutos)

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


class FreelanceGroup(app_commands.Group):
    def __init__(self, cog: "MonitorCog") -> None:
        super().__init__(name="freelance", description="Configura monitoramento de oportunidades freelance.")
        self.cog = cog

    @app_commands.command(name="setup", description="Configura alertas automaticos de freelances.")
    @app_commands.choices(
        frequencia_minutos=[
            app_commands.Choice(name="5 minutos", value=5),
            app_commands.Choice(name="15 minutos", value=15),
            app_commands.Choice(name="30 minutos", value=30),
            app_commands.Choice(name="1 hora", value=60),
        ]
    )
    @admin_check()
    async def setup(self, interaction: discord.Interaction, canal: discord.TextChannel, frequencia_minutos: int = 5) -> None:
        await self.cog.upsert_monitor(interaction, "freelance", "marketplaces", canal.id, "", frequencia_minutos)

    @app_commands.command(name="interval", description="Altera o intervalo do monitor freelance.")
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
        await self.cog.update_monitor_interval(interaction, "freelance", minutos, "freelance")


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

    @run_group.command(name="freelance", description="Executa o monitor freelance agora.")
    @admin_check()
    async def run_freelance(self, interaction: discord.Interaction) -> None:
        await self.cog.run_monitor_now(interaction, "freelance", "\U0001f680 Executando monitor freelance...")


class MonitorCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.manager = MonitorManager(bot)
        bot.tree.add_command(JobsGroup(self))
        bot.tree.add_command(HackathonGroup(self))
        bot.tree.add_command(FreelanceGroup(self))
        bot.tree.add_command(MonitorGroup(self))
        if settings.monitor_enabled:
            self.monitor_task.change_interval(minutes=max(settings.monitor_interval_minutes, 1))
            self.monitor_task.start()
            logger.info("Task iniciada: monitor_task a cada %s minuto(s)", max(settings.monitor_interval_minutes, 1))
        else:
            logger.info("Task monitor_task desativada por configuracao")

    async def cog_unload(self) -> None:
        if self.monitor_task.is_running():
            self.monitor_task.cancel()
            logger.info("Task cancelada: monitor_task")
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
        frequency_minutes: int,
    ) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        frequency_minutes = max(frequency_minutes, 5)
        config = {
            "sources": ["linkedin", "indeed", "public"],
            "regions": ["Estados Unidos", "Brasil", "Global"],
            "filters": "none",
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
                        "Fontes: LinkedIn, Indeed e fontes publicas de tecnologia",
                        "Regioes: Estados Unidos, Brasil e Global",
                        "Filtros: nenhum",
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

    async def update_monitor_interval(self, interaction: discord.Interaction, monitor_type: str, minutes: int, label: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        cursor = await self.bot.db.execute(
            "UPDATE monitors SET frequency_minutes = ? WHERE guild_id = ? AND type = ? AND enabled = 1",
            (minutes, interaction.guild.id, monitor_type),
        )
        if not cursor.rowcount:
            await interaction.response.send_message(f"Nenhum monitor {label} ativo. Use `/{label} setup` primeiro.", ephemeral=True)
            return
        await interaction.response.send_message(embed=make_embed("Intervalo atualizado", f"Monitor {label} rodando a cada {minutes} minutos."), ephemeral=True)

    async def run_monitor_now(self, interaction: discord.Interaction, monitor_type: str, title: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        stats = await self.manager.run_now(interaction.guild.id, monitor_type)
        channel_warning = "\n\n\u26a0\ufe0f Canal de destino nao configurado." if stats.missing_channel else ""
        channel_line = "Canal destino:\n" + (", ".join(f"<#{channel_id}>" for channel_id in sorted(stats.channel_ids)) if stats.channel_ids else "nao configurado")
        error_details = ""
        if stats.error_details:
            details = "\n".join(f"- {detail}" for detail in stats.error_details[:3])
            error_details = f"\n\nDetalhes:\n{details}"
        found_label = "Encontradas" if monitor_type == "jobs" else "Encontrados"
        item_label = "novas vagas" if monitor_type == "jobs" else "itens"
        await interaction.followup.send(
            embed=make_embed(
                title,
                "\n\n".join(
                    [
                        f"{found_label}:\n{stats.found} {item_label}",
                        f"Novos:\n{stats.new}",
                        f"Enviados:\n{stats.sent}",
                        f"Duplicados:\n{stats.duplicates}",
                        f"Erros:\n{stats.errors}",
                        f"Tempo de execucao:\n{stats.execution_time:.2f}s",
                        channel_line,
                    ]
                )
                + channel_warning
                + error_details,
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
        sections = {"jobs": [], "hackathons": [], "freelance": [], "content": []}
        for row in rows[:20]:
            error = row["last_error"] or "sem erros"
            last_check = row["last_check"] or "ainda nao executado"
            next_check = self._next_execution(row["last_check"], row["frequency_minutes"])
            if row["type"] == "jobs":
                config = self._load_json(row["filters"])
                sources = config.get("sources", ["linkedin", "indeed", "public"]) if isinstance(config, dict) else ["linkedin", "indeed", "public"]
                source_lines = "\n".join(f"\u2705 {self._source_label(source)}" for source in sources) or "todas"
                latest_log = await self._latest_monitor_log("jobs")
                sections["jobs"].append(
                    "\n".join(
                        [
                            "\U0001f4bc Jobs Monitor",
                            f"Canal: <#{row['channel_id']}>",
                            f"Intervalo: {row['frequency_minutes']} minutos",
                            f"Fontes ativas:\n{source_lines}",
                            f"Ultima busca: {last_check}",
                            f"Novas vagas: {latest_log.get('items_new', row['last_result_count'])}",
                            f"Enviadas: {latest_log.get('items_sent', 0)}",
                            f"Duplicadas: {latest_log.get('duplicates', 0)}",
                            f"Erros: {latest_log.get('errors', 0) if latest_log else error}",
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
                            f"Proxima execucao: {next_check}",
                            f"Novos eventos encontrados: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
            elif row["type"] == "freelance":
                sections["freelance"].append(
                    "\n".join(
                        [
                            "\U0001f680 Freelance",
                            "Status: \U0001f7e2 Online",
                            f"Canal: <#{row['channel_id']}>",
                            f"Ultima execucao: {last_check}",
                            f"Proxima execucao: {next_check}",
                            f"Novas oportunidades encontradas: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
            else:
                if row["type"] == "instagram" and settings.instagram_provider == "disabled":
                    error = "Instagram configurado, mas provider nao definido."
                sections["content"].append(
                    "\n".join(
                        [
                            "\U0001f3a5 Conteudo",
                            "Status: \U0001f7e2 Online",
                            f"Fonte: {row['type']} | {row['source']}",
                            f"Ultima execucao: {last_check}",
                            f"Proxima execucao: {next_check}",
                            f"Novos conteudos encontrados: {row['last_result_count']}",
                            f"Erros: {error}",
                        ]
                    )
                )
        lines = ["\U0001f4e1 DevVerse Monitor"]
        for key in ("jobs", "hackathons", "freelance", "content"):
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
        return {
            "linkedin": "LinkedIn + LinkedIn Brasil",
            "indeed": "Indeed + Indeed Brasil",
            "public": "Programathor, GeekHunter, Revelo, Trampos.co, Coodesh, Gupy tecnologia, Remotar, Hipsters.jobs, RemoteOK, WeWorkRemotely, Wellfound",
            "existing": "Outras",
        }.get(source, source.title())

    async def _latest_monitor_log(self, monitor_type: str) -> dict[str, int]:
        row = await self.bot.db.fetchone(
            """
            SELECT items_new, items_sent, duplicates, errors
            FROM monitor_logs
            WHERE type = ? OR monitor_type = ?
            ORDER BY id DESC
            LIMIT 1
            """,
            (monitor_type, monitor_type),
        )
        return dict(row) if row else {}

    def _empty_status(self, key: str) -> str:
        labels = {"jobs": "\U0001f4bc Jobs", "hackathons": "\U0001f3c6 Hackathons", "freelance": "\U0001f680 Freelance", "content": "\U0001f3a5 Conteudo"}
        return f"{labels[key]}\nStatus: \U0001f534 Offline"

    def _next_execution(self, last_check: str | None, frequency_minutes: int) -> str:
        if not last_check:
            return "assim que o bot executar o ciclo"
        try:
            checked_at = datetime.fromisoformat(last_check)
        except ValueError:
            return "nao calculado"
        return (checked_at + timedelta(minutes=frequency_minutes)).isoformat()


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(MonitorCog(bot))
