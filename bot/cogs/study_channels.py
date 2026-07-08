from __future__ import annotations

import time
from dataclasses import dataclass

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.services.audit_log import AuditReport, ensure_audit_channel, send_audit_report
from bot.utils import make_embed
from bot.views.onboarding import resolve_role


@dataclass(frozen=True)
class StudyCategory:
    name: str
    role_key: str
    role_names: tuple[str, ...]
    topic: str
    roadmap: str
    resources: str
    channels: tuple[str, ...]


STUDY_CATEGORIES: tuple[StudyCategory, ...] = (
    StudyCategory(
        name="🐍 Python",
        role_key="python",
        role_names=("🐍 Python", "Python"),
        topic="Python, automacao, backend, dados, IA e boas praticas de codigo.",
        roadmap="Sintaxe -> POO -> APIs -> Banco de dados -> Testes -> Projetos -> Deploy.",
        resources="Python.org, FastAPI/Django docs, Exercism, freeCodeCamp e projetos da comunidade.",
        channels=("💬・python-chat", "📢・python-news", "📚・python-recursos", "📝・python-anotacoes", "💻・python-projetos", "❓・python-duvidas", "🧩・python-desafios", "📦・python-bibliotecas", "🤖・python-ai", "🚀・python-roadmap"),
    ),
    StudyCategory(
        name="🟨 JavaScript",
        role_key="javascript",
        role_names=("🟨 JavaScript", "JavaScript"),
        topic="JavaScript moderno, DOM, Node.js, frontend e ecossistema web.",
        roadmap="Fundamentos -> DOM -> Async -> APIs -> Node.js -> Frameworks -> Projetos.",
        resources="MDN, JavaScript.info, Node.js docs, freeCodeCamp e desafios práticos.",
        channels=("💬・javascript-chat", "📢・javascript-news", "📚・javascript-recursos", "📝・javascript-anotacoes", "💻・javascript-projetos", "❓・javascript-duvidas", "🌐・javascript-web", "🚀・javascript-roadmap"),
    ),
    StudyCategory(
        name="🌐 Front-end",
        role_key="frontend",
        role_names=("🌐 Front-end", "Front-end", "Frontend"),
        topic="HTML, CSS, JavaScript, UI/UX, acessibilidade e frameworks front-end.",
        roadmap="HTML/CSS -> JS -> Responsividade -> React/Vue/Angular -> Performance -> Portfolio.",
        resources="MDN, web.dev, Frontend Mentor, React/Vue/Angular docs.",
        channels=("💬・frontend-chat", "📢・frontend-news", "📚・frontend-recursos", "📝・frontend-anotacoes", "💻・frontend-projetos", "❓・frontend-duvidas", "🎨・frontend-uiux", "⚛️・frontend-frameworks", "🚀・frontend-roadmap"),
    ),
    StudyCategory(
        name="⚙️ Back-end",
        role_key="backend",
        role_names=("⚙️ Back-end", "Back-end", "Backend"),
        topic="APIs, autenticacao, arquitetura, banco de dados, filas e deploy backend.",
        roadmap="HTTP -> APIs -> Auth -> Banco -> Cache/filas -> Testes -> Observabilidade -> Deploy.",
        resources="FastAPI, Django, Express, Spring Boot, system design e projetos guiados.",
        channels=("💬・backend-chat", "📢・backend-news", "📚・backend-recursos", "📝・backend-anotacoes", "💻・backend-projetos", "❓・backend-duvidas", "🗄️・backend-database", "🔌・backend-api", "🚀・backend-roadmap"),
    ),
    StudyCategory(
        name="🗄️ Database",
        role_key="database",
        role_names=("🗄️ Banco de Dados", "🗄️ Database", "Database", "Banco de Dados"),
        topic="Modelagem, SQL, NoSQL, performance, transacoes e administracao de dados.",
        roadmap="Modelagem -> SQL -> Indices -> Transacoes -> NoSQL -> Performance -> Projetos.",
        resources="SQLBolt, PostgreSQL docs, SQLite docs, MongoDB University e Kaggle datasets.",
        channels=("💬・database-chat", "📢・database-news", "📚・database-recursos", "📝・database-anotacoes", "💻・database-projetos", "❓・database-duvidas", "📊・sql", "🍃・nosql", "🚀・database-roadmap"),
    ),
    StudyCategory(
        name="🤖 AI & Machine Learning",
        role_key="ai",
        role_names=("🤖 Inteligencia Artificial", "🤖 Inteligência Artificial", "AI", "IA"),
        topic="Machine Learning, LLMs, dados, papers, agentes e projetos com IA.",
        roadmap="Python -> Algebra/estatistica -> ML -> Deep Learning -> LLMs -> MLOps -> Projetos.",
        resources="Kaggle Learn, Hugging Face, fast.ai, Google ML Crash Course e papers.",
        channels=("💬・ai-chat", "📢・ai-news", "📚・ai-recursos", "📝・ai-anotacoes", "💻・ai-projetos", "❓・ai-duvidas", "🧠・machine-learning", "📄・papers", "🚀・ai-roadmap"),
    ),
    StudyCategory(
        name="🔒 Cybersecurity",
        role_key="cybersecurity",
        role_names=("🔒 Cybersecurity", "Cybersecurity", "Security"),
        topic="Seguranca defensiva, CTFs, pentest etico, OWASP e hardening.",
        roadmap="Redes -> Linux -> Web -> OWASP -> CTF -> Pentest etico -> Blue Team.",
        resources="TryHackMe, PortSwigger Academy, OWASP, OverTheWire e CTFtime.",
        channels=("💬・cyber-chat", "📢・security-news", "📚・cyber-recursos", "📝・cyber-anotacoes", "💻・cyber-projetos", "❓・cyber-duvidas", "🏴‍☠️・ctf", "🛡️・pentest", "🚀・cyber-roadmap"),
    ),
    StudyCategory(
        name="☁️ Cloud",
        role_key="cloud",
        role_names=("☁️ Cloud", "Cloud"),
        topic="AWS, Azure, GCP, infraestrutura, deploy, redes e custos.",
        roadmap="Linux/redes -> Cloud basics -> IAM -> Compute -> Storage -> IaC -> Projetos.",
        resources="AWS Skill Builder, Microsoft Learn, Google Cloud Skills Boost e Terraform docs.",
        channels=("💬・cloud-chat", "📢・cloud-news", "📚・cloud-recursos", "📝・cloud-anotacoes", "💻・cloud-projetos", "❓・cloud-duvidas", "☁️・aws", "☁️・azure", "☁️・gcp", "🚀・cloud-roadmap"),
    ),
    StudyCategory(
        name="🐧 Linux",
        role_key="linux",
        role_names=("🐧 Linux", "Linux"),
        topic="Terminal, Bash, administracao Linux, servidores e produtividade.",
        roadmap="Terminal -> Filesystem -> Permissoes -> Bash -> Processos -> Redes -> Servidores.",
        resources="Linux Journey, The Linux Command Line, OverTheWire e Ubuntu docs.",
        channels=("💬・linux-chat", "📢・linux-news", "📚・linux-recursos", "📝・linux-anotacoes", "💻・linux-projetos", "❓・linux-duvidas", "💻・terminal", "⚙️・bash", "🚀・linux-roadmap"),
    ),
    StudyCategory(
        name="📦 Git & GitHub",
        role_key="git",
        role_names=("📦 Git/GitHub", "📦 Git & GitHub", "Git/GitHub", "Git & GitHub"),
        topic="Git, GitHub, branches, pull requests, code review e colaboracao.",
        roadmap="Init/clone -> Commits -> Branches -> Pull Requests -> Rebase -> Workflows -> Open source.",
        resources="Git Book, GitHub Docs, Learn Git Branching e projetos colaborativos.",
        channels=("💬・git-chat", "📢・git-news", "📚・git-recursos", "📝・git-anotacoes", "💻・git-projetos", "❓・git-duvidas", "🌿・branches", "🔀・pull-requests", "🚀・git-roadmap"),
    ),
)


class StudyChannelsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="setup_study_channels", description="Cria categorias e canais de estudo do DevVerse.")
    @admin_check()
    async def setup_study_channels(self, interaction: discord.Interaction) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use este comando dentro de um servidor.", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        started = time.perf_counter()
        stats = {
            "categories_created": 0,
            "categories_reused": 0,
            "channels_created": 0,
            "channels_reused": 0,
            "items_changed": 0,
        }
        errors: list[str] = []
        audit = AuditReport(title="Setup de canais de estudo", actor=f"{interaction.user} ({interaction.user.id})")
        audit_channel = await ensure_audit_channel(interaction.guild)
        if audit_channel:
            audit.reused.append(f"Canal privado de auditoria: #{audit_channel.name}")
        for definition in STUDY_CATEGORIES:
            try:
                category, category_action = await self._ensure_category(interaction.guild, definition)
                created_category = category_action == "created"
                stats["categories_created" if created_category else "categories_reused"] += 1
                if created_category:
                    audit.added.append(f"Categoria {definition.name}")
                elif category_action == "changed":
                    stats["items_changed"] += 1
                    audit.changed.append(f"Permissoes da categoria {definition.name}")
                else:
                    audit.reused.append(f"Categoria {definition.name}")
                first_channel: discord.TextChannel | None = None
                for channel_name in definition.channels:
                    channel, channel_action = await self._ensure_text_channel(interaction.guild, category, channel_name)
                    created_channel = channel_action == "created"
                    if first_channel is None:
                        first_channel = channel
                    stats["channels_created" if created_channel else "channels_reused"] += 1
                    if created_channel:
                        audit.added.append(f"Canal #{channel.name}")
                    elif channel_action == "changed":
                        stats["items_changed"] += 1
                        audit.changed.append(f"Canal #{channel.name} movido/sincronizado")
                    else:
                        audit.reused.append(f"Canal #{channel.name}")
                if first_channel:
                    intro_action = await self._ensure_pinned_intro(first_channel, definition)
                    if intro_action == "created":
                        audit.added.append(f"Mensagem fixa em #{first_channel.name}")
                    elif intro_action == "changed":
                        stats["items_changed"] += 1
                        audit.changed.append(f"Mensagem fixa em #{first_channel.name}")
                    else:
                        audit.reused.append(f"Mensagem fixa em #{first_channel.name}")
            except discord.Forbidden:
                message = f"Sem permissao em {definition.name}"
                errors.append(message)
                audit.errors.append(message)
            except discord.HTTPException as exc:
                message = f"{definition.name}: {exc}"
                errors.append(message)
                audit.errors.append(message)

        elapsed = time.perf_counter() - started
        description = "\n".join(
            [
                f"✅ Categorias criadas: {stats['categories_created']}",
                f"✅ Categorias reutilizadas: {stats['categories_reused']}",
                f"✅ Canais criados: {stats['channels_created']}",
                f"✅ Canais reutilizados: {stats['channels_reused']}",
                f"❌ Erros encontrados: {len(errors)}",
                f"Alterados/sincronizados: {stats['items_changed']}",
                "Removidos: 0",
                f"Tempo de execucao: {elapsed:.2f}s",
            ]
        )
        if errors:
            description += "\n\n" + "\n".join(errors[:10])
        audit.summary = (
            f"Categorias previstas: {len(STUDY_CATEGORIES)} | "
            f"Canais previstos: {sum(len(category.channels) for category in STUDY_CATEGORIES)} | "
            f"Tempo: {elapsed:.2f}s"
        )
        await send_audit_report(interaction.guild, audit)
        await interaction.followup.send(embed=make_embed("Setup de estudos concluido", description), ephemeral=True)

    async def _ensure_category(self, guild: discord.Guild, definition: StudyCategory) -> tuple[discord.CategoryChannel, str]:
        existing = discord.utils.get(guild.categories, name=definition.name)
        role = self._resolve_category_role(guild, definition)
        overwrites = self._category_overwrites(guild, role)
        if existing:
            if self._overwrites_differ(existing.overwrites, overwrites):
                await existing.edit(overwrites=overwrites, reason="DevVerse setup_study_channels permissions")
                return existing, "changed"
            return existing, "reused"
        category = await guild.create_category(definition.name, overwrites=overwrites, reason="DevVerse setup_study_channels")
        return category, "created"

    async def _ensure_text_channel(
        self,
        guild: discord.Guild,
        category: discord.CategoryChannel,
        name: str,
    ) -> tuple[discord.TextChannel, str]:
        existing = discord.utils.get(guild.text_channels, name=name)
        if existing:
            if existing.category_id != category.id:
                await existing.edit(category=category, sync_permissions=True, reason="DevVerse setup_study_channels organize")
                return existing, "changed"
            return existing, "reused"
        channel = await guild.create_text_channel(name, category=category, reason="DevVerse setup_study_channels")
        return channel, "created"

    def _category_overwrites(
        self,
        guild: discord.Guild,
        role: discord.Role | None,
    ) -> dict[discord.Role, discord.PermissionOverwrite]:
        overwrites: dict[discord.Role, discord.PermissionOverwrite] = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
        }
        visitor_role = resolve_role(guild, "visitor")
        if visitor_role:
            overwrites[visitor_role] = discord.PermissionOverwrite(view_channel=False)
        if role:
            overwrites[role] = discord.PermissionOverwrite(
                view_channel=True,
                read_message_history=True,
                send_messages=True,
                attach_files=True,
                use_application_commands=True,
            )
        return overwrites

    def _resolve_category_role(self, guild: discord.Guild, definition: StudyCategory) -> discord.Role | None:
        role = resolve_role(guild, definition.role_key)
        if role:
            return role
        for name in definition.role_names:
            role = discord.utils.get(guild.roles, name=name)
            if role:
                return role
        return None

    async def _ensure_pinned_intro(self, channel: discord.TextChannel, definition: StudyCategory) -> str:
        title = f"Guia de estudo - {definition.name}"
        async for message in channel.history(limit=30):
            if message.author == channel.guild.me and message.embeds and message.embeds[0].title == title:
                if not message.pinned:
                    await message.pin(reason="DevVerse setup_study_channels")
                    return "changed"
                return "reused"
        embed = make_embed(
            title,
            "\n".join(
                [
                    f"O que estudar: {definition.topic}",
                    "",
                    f"Roadmap recomendado: {definition.roadmap}",
                    "",
                    f"Recursos uteis: {definition.resources}",
                    "",
                    "Como usar os canais: use chat para conversar, recursos para materiais, projetos para entregas, duvidas para ajuda e roadmap para evolucao.",
                    "",
                    "Comandos relacionados: /roadmap, /resource, /task, /pomodoro, /monitor status.",
                ]
            ),
        )
        message = await channel.send(embed=embed)
        await message.pin(reason="DevVerse setup_study_channels")
        return "created"

    def _overwrites_differ(
        self,
        current: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
        expected: dict[discord.abc.Snowflake, discord.PermissionOverwrite],
    ) -> bool:
        for target, overwrite in expected.items():
            if current.get(target) != overwrite:
                return True
        return False


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(StudyChannelsCog(bot))
