from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from bot.config import settings


VERSION = "DevVerse Assistant 1.0"


@dataclass(slots=True)
class HelpCommand:
    path: str
    description: str


CATEGORIES: dict[str, tuple[str, str]] = {
    "bot": ("\U0001f916 Bot", "Status geral do DevVerse Assistant."),
    "estudos": ("\U0001f4da Estudos", "Comandos para estudo, roadmaps, recursos e progresso."),
    "perfil": ("\U0001f464 Perfil", "Perfil, ranking, tarefas e produtividade pessoal."),
    "vagas": ("\U0001f4bc Vagas", "Monitor de vagas de tecnologia."),
    "freelance": ("\U0001f680 Freelance", "Monitor de oportunidades freelance."),
    "hackathons": ("\U0001f3c6 Hackathons", "Alertas e execucao do monitor de hackathons."),
    "monitores": ("\U0001f3a5 Monitores", "Status, execucao manual e fontes de conteudo."),
    "administracao": ("\U0001f6e0 Administracao", "Moderacao, permissoes e manutencao do servidor."),
    "configuracao": ("\u2699\ufe0f Configuracao", "Setups e configuracoes principais."),
    "utilidades": ("\U0001f4ca Utilidades", "Comandos auxiliares e integracoes."),
}

FALLBACK_DESCRIPTIONS = {
    "/setup_devserver": "Cria automaticamente a estrutura principal do servidor.",
    "/setup_roles": "Configura o sistema de cargos e selecao de perfil.",
    "/setup_study_channels": "Cria todas as categorias e canais de estudo.",
    "/jobs setup": "Configura o canal e intervalo das vagas.",
    "/jobs interval": "Altera o intervalo de atualizacao das vagas.",
    "/freelance setup": "Configura o monitor de freelances.",
    "/freelance interval": "Define o intervalo do monitor freelance.",
    "/monitor status": "Mostra o status de todos os monitores.",
    "/monitor run jobs": "Executa imediatamente o monitor de vagas.",
    "/monitor run freelance": "Executa imediatamente o monitor de freelances.",
    "/monitor run hackathons": "Executa imediatamente o monitor de hackathons.",
    "/monitor run instagram": "Executa imediatamente o monitor do Instagram.",
    "/clear quantidade": "Apaga uma quantidade de mensagens.",
    "/clear tempo": "Apaga mensagens de um periodo especifico.",
    "/clear usuario": "Apaga mensagens de um usuario no canal atual.",
    "/permissions check": "Mostra as permissoes de um usuario.",
    "/profile": "Mostra o perfil do usuario.",
    "/ranking": "Mostra o ranking do servidor.",
    "/pomodoro": "Inicia um cronometro Pomodoro.",
}


class CommandsHelpView(discord.ui.View):
    def __init__(self, cog: "HelpCog", interaction: discord.Interaction, commands_by_category: dict[str, list[HelpCommand]]) -> None:
        super().__init__(timeout=180)
        self.cog = cog
        self.interaction = interaction
        self.commands_by_category = commands_by_category
        self.add_item(CommandsCategorySelect(cog, commands_by_category))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.interaction.user.id:
            await interaction.response.send_message("Use `/comandos` para abrir sua propria central.", ephemeral=True)
            return False
        return True


class CommandsCategorySelect(discord.ui.Select):
    def __init__(self, cog: "HelpCog", commands_by_category: dict[str, list[HelpCommand]]) -> None:
        self.cog = cog
        options = [
            discord.SelectOption(
                label=label,
                value=key,
                description=description[:100],
            )
            for key, (label, description) in CATEGORIES.items()
        ]
        super().__init__(placeholder="Escolha uma categoria", min_values=1, max_values=1, options=options)
        self.commands_by_category = commands_by_category

    async def callback(self, interaction: discord.Interaction) -> None:
        category = self.values[0]
        embed = await self.cog.build_category_embed(interaction, category, self.commands_by_category)
        await interaction.response.edit_message(embed=embed, view=self.view)


class HelpCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.started_at = datetime.now(timezone.utc)

    @app_commands.command(name="comandos", description="Abre a central interativa de comandos do DevVerse.")
    @app_commands.describe(pesquisar="Opcional: busque comandos por nome ou descricao.")
    async def comandos(self, interaction: discord.Interaction, pesquisar: str = "") -> None:
        commands_by_category = self.collect_commands()
        if pesquisar.strip():
            embed = self.build_search_embed(pesquisar.strip(), commands_by_category)
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        embed = self.build_home_embed(commands_by_category)
        view = CommandsHelpView(self, interaction, commands_by_category)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    def collect_commands(self) -> dict[str, list[HelpCommand]]:
        commands_by_category: dict[str, list[HelpCommand]] = {key: [] for key in CATEGORIES}
        for command in self.bot.tree.get_commands():
            for item in self._flatten_command(command):
                category = self._category_for(item.path)
                commands_by_category.setdefault(category, []).append(item)
        for commands_list in commands_by_category.values():
            commands_list.sort(key=lambda item: item.path)
        return commands_by_category

    def _flatten_command(self, command: app_commands.Command | app_commands.Group, prefix: str = "") -> list[HelpCommand]:
        path = f"{prefix} {command.name}".strip()
        if isinstance(command, app_commands.Group):
            items: list[HelpCommand] = []
            for child in command.commands:
                items.extend(self._flatten_command(child, path))
            if not items:
                items.append(HelpCommand(path=f"/{path}", description=self._description_for(f"/{path}", command.description)))
            return items
        full_path = f"/{path}"
        return [HelpCommand(path=full_path, description=self._description_for(full_path, command.description))]

    def _description_for(self, path: str, automatic: str | None) -> str:
        description = (automatic or "").strip()
        if not description or description.lower() in {"...", "sem descricao", "no description"}:
            return FALLBACK_DESCRIPTIONS.get(path, "Comando DevVerse.")
        return FALLBACK_DESCRIPTIONS.get(path, description)

    def _category_for(self, path: str) -> str:
        if path in {"/setup_devserver", "/setup_roles", "/setup_study_channels"} or path.startswith(("/jobs setup", "/freelance setup")):
            return "configuracao"
        if path.startswith("/jobs"):
            return "vagas"
        if path.startswith("/freelance"):
            return "freelance"
        if path.startswith("/hackathon") or path == "/monitor run hackathons":
            return "hackathons"
        if path.startswith("/monitor"):
            return "monitores"
        if path.startswith(("/clear", "/permissions", "/warn", "/warnings", "/timeout", "/kick", "/ban", "/limpar_devserver", "/sync_visitors")):
            return "administracao"
        if path.startswith(("/checkin", "/roadmap", "/resource", "/quiz", "/challenge", "/setup_study_channels")):
            return "estudos"
        if path.startswith(("/profile", "/ranking", "/task_", "/pomodoro")):
            return "perfil"
        if path.startswith(("/ping", "/ask", "/explain_code", "/debug_code", "/review_code", "/optimize_code", "/generate_code")):
            return "bot"
        return "utilidades"

    def build_home_embed(self, commands_by_category: dict[str, list[HelpCommand]]) -> discord.Embed:
        total = sum(len(commands_list) for commands_list in commands_by_category.values())
        embed = discord.Embed(
            title="\U0001f4da Central de Comandos DevVerse",
            description="Escolha uma categoria abaixo para visualizar os comandos disponiveis.",
            color=discord.Color.blurple(),
        )
        lines = []
        for key, (label, description) in CATEGORIES.items():
            lines.append(f"{label} - {len(commands_by_category.get(key, []))} comandos\n{description}")
        embed.add_field(name="Categorias", value="\n\n".join(lines)[:1024], inline=False)
        embed.add_field(name="Total de comandos", value=str(total), inline=True)
        embed.set_footer(text="DevVerse Assistant")
        return embed

    async def build_category_embed(
        self,
        interaction: discord.Interaction,
        category: str,
        commands_by_category: dict[str, list[HelpCommand]],
    ) -> discord.Embed:
        if category == "bot":
            return self.build_bot_embed(interaction, commands_by_category)
        label, description = CATEGORIES[category]
        embed = discord.Embed(title=label, description=description, color=discord.Color.blurple())
        commands_list = commands_by_category.get(category, [])
        if not commands_list:
            embed.add_field(name="Comandos", value="Nenhum comando registrado nesta categoria.", inline=False)
        else:
            for chunk_index, chunk in enumerate(self._chunks(commands_list, 8), start=1):
                embed.add_field(
                    name="Comandos" if chunk_index == 1 else f"Comandos {chunk_index}",
                    value="\n".join(f"`{item.path}`\n{item.description}" for item in chunk)[:1024],
                    inline=False,
                )
        embed.set_footer(text="DevVerse Assistant")
        return embed

    def build_bot_embed(self, interaction: discord.Interaction, commands_by_category: dict[str, list[HelpCommand]]) -> discord.Embed:
        total = sum(len(commands_list) for commands_list in commands_by_category.values())
        uptime = datetime.now(timezone.utc) - self.started_at
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        db_status = "Online" if getattr(self.bot, "db", None) and self.bot.db.conn else "Indisponivel"
        embed = discord.Embed(
            title="\U0001f916 Bot",
            description="Informacoes gerais do DevVerse Assistant.",
            color=discord.Color.blurple(),
        )
        embed.add_field(name="Versao", value=VERSION, inline=True)
        embed.add_field(name="Comandos", value=str(total), inline=True)
        embed.add_field(name="Servidores", value=str(len(self.bot.guilds)), inline=True)
        embed.add_field(name="Tempo online", value=f"{hours}h {minutes}m {seconds}s", inline=True)
        embed.add_field(name="Ping", value=f"{round(self.bot.latency * 1000)} ms", inline=True)
        embed.add_field(name="Banco de dados", value=db_status, inline=True)
        embed.add_field(name="Modelo de IA", value=settings.ollama_model, inline=True)
        embed.add_field(name="Servidor atual", value=interaction.guild.name if interaction.guild else "DM", inline=True)
        embed.set_footer(text="DevVerse Assistant")
        return embed

    def build_search_embed(self, query: str, commands_by_category: dict[str, list[HelpCommand]]) -> discord.Embed:
        lowered = query.lower()
        results = [
            item
            for commands_list in commands_by_category.values()
            for item in commands_list
            if lowered in item.path.lower() or lowered in item.description.lower()
        ]
        embed = discord.Embed(
            title=f"\U0001f50e Pesquisa: {query}",
            description=f"Resultados encontrados: {len(results)}",
            color=discord.Color.blurple(),
        )
        if not results:
            embed.add_field(name="Comandos", value="Nenhum comando encontrado.", inline=False)
        else:
            for chunk_index, chunk in enumerate(self._chunks(results[:24], 8), start=1):
                embed.add_field(
                    name="Resultados" if chunk_index == 1 else f"Resultados {chunk_index}",
                    value="\n".join(f"`{item.path}`\n{item.description}" for item in chunk)[:1024],
                    inline=False,
                )
        embed.set_footer(text="DevVerse Assistant")
        return embed

    def _chunks(self, values: list[HelpCommand], size: int) -> list[list[HelpCommand]]:
        return [values[index : index + size] for index in range(0, len(values), size)]


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(HelpCog(bot))
