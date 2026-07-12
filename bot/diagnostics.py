from __future__ import annotations

import asyncio
import importlib
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import settings
from .database import Database


@dataclass(slots=True)
class DiagnosticItem:
    name: str
    status: str
    detail: str = ""


@dataclass(slots=True)
class DiagnosticReport:
    ok: bool
    items: list[DiagnosticItem] = field(default_factory=list)

    def add(self, name: str, status: str, detail: str = "") -> None:
        self.items.append(DiagnosticItem(name=name, status=status, detail=detail))
        if status in {"erro", "critico"}:
            self.ok = False


REQUIRED_DEPENDENCIES = ("discord", "aiosqlite", "httpx", "dotenv")
OPTIONAL_DEPENDENCIES = ("fastapi", "uvicorn")
REQUIRED_ENV = ("DISCORD_TOKEN",)
OPTIONAL_ENV = (
    "GUILD_ID",
    "AI_PROVIDER",
    "AI_GATEWAY_URL",
    "OLLAMA_HOST",
    "DATABASE_PATH",
    "MONITOR_ENABLED",
    "INSTAGRAM_PROVIDER",
    "APIFY_TOKEN",
    "RSS_BRIDGE_URL",
)
PERSISTENT_VIEWS = (
    "OnboardingView(PRIMARY_ONBOARDING_GROUPS)",
    "OnboardingView(EXTRA_ONBOARDING_GROUPS)",
    "OnboardingPanelView",
    "RolePanelView",
)
MONITOR_PROVIDERS = (
    "linkedin",
    "indeed",
    "public_jobs",
    "hackathons",
    "freelance",
    "social",
)


async def collect_diagnostics(bot: Any | None = None, cogs: list[str] | None = None) -> DiagnosticReport:
    report = DiagnosticReport(ok=True)
    report.add("Python", "ok", platform.python_version())
    report.add("Sistema", "ok", platform.platform())
    _check_dependencies(report)
    _check_environment(report)
    _check_intents(report, bot)
    await _check_database(report)
    _check_cogs(report, cogs)
    _check_commands(report, bot)
    _check_views(report)
    _check_providers(report)
    _check_ai(report)
    return report


def _check_dependencies(report: DiagnosticReport) -> None:
    for dependency in REQUIRED_DEPENDENCIES:
        try:
            importlib.import_module(dependency)
            report.add(f"Dependencia {dependency}", "ok")
        except Exception as exc:
            report.add(f"Dependencia {dependency}", "erro", exc.__class__.__name__)
    for dependency in OPTIONAL_DEPENDENCIES:
        try:
            importlib.import_module(dependency)
            report.add(f"Dependencia opcional {dependency}", "ok")
        except Exception:
            report.add(f"Dependencia opcional {dependency}", "aviso", "nao instalada")


def _check_environment(report: DiagnosticReport) -> None:
    report.add(".env", "ok" if Path(".env").exists() else "aviso", "arquivo local encontrado" if Path(".env").exists() else "arquivo local ausente")
    values = {
        "DISCORD_TOKEN": settings.token,
        "GUILD_ID": str(settings.guild_id or ""),
        "AI_PROVIDER": settings.ai_provider,
        "AI_GATEWAY_URL": settings.ai_gateway_url,
        "OLLAMA_HOST": settings.ollama_host,
        "DATABASE_PATH": str(settings.database_path),
        "MONITOR_ENABLED": str(settings.monitor_enabled),
        "INSTAGRAM_PROVIDER": settings.instagram_provider,
        "APIFY_TOKEN": settings.apify_token,
        "RSS_BRIDGE_URL": settings.rss_bridge_url,
    }
    for key in REQUIRED_ENV:
        report.add(f"Env {key}", "ok" if values.get(key) else "critico", "configurado" if values.get(key) else "ausente")
    for key in OPTIONAL_ENV:
        report.add(f"Env {key}", "ok" if values.get(key) else "aviso", "configurado" if values.get(key) else "ausente")


def _check_intents(report: DiagnosticReport, bot: Any | None) -> None:
    if bot is None:
        report.add("Intents", "aviso", "verificacao completa exige bot em execucao")
        return
    intents = bot.intents
    report.add("Intent guilds", "ok" if intents.guilds else "erro")
    report.add("Intent members", "ok" if intents.members else "erro", "SERVER MEMBERS INTENT precisa estar ativo no portal Discord")
    report.add("Intent message_content", "ok" if intents.message_content else "aviso")


async def _check_database(report: DiagnosticReport) -> None:
    db = Database(settings.database_path)
    try:
        await db.connect()
        await db.setup()
        rows = await db.fetchall("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
        report.add("Banco SQLite", "ok", f"{len(rows)} tabelas prontas")
    except Exception as exc:
        report.add("Banco SQLite", "erro", exc.__class__.__name__)
    finally:
        await db.close()


def _check_cogs(report: DiagnosticReport, cogs: list[str] | None) -> None:
    if not cogs:
        report.add("Cogs", "aviso", "lista de cogs nao informada")
        return
    for cog in cogs:
        if cog.endswith(".github") and not settings.enable_github:
            report.add(f"Cog {cog}", "aviso", "desativado por ENABLE_GITHUB=false")
            continue
        try:
            importlib.import_module(cog)
            report.add(f"Cog {cog}", "ok")
        except Exception as exc:
            report.add(f"Cog {cog}", "erro", exc.__class__.__name__)


def _check_commands(report: DiagnosticReport, bot: Any | None) -> None:
    if bot is None:
        report.add("Comandos", "aviso", "registro completo exige bot em execucao")
        return
    commands = bot.tree.get_commands()
    report.add("Comandos", "ok" if commands else "aviso", f"{len(commands)} comandos/grupos carregados localmente")


def _check_views(report: DiagnosticReport) -> None:
    report.add("Persistent views", "ok", ", ".join(PERSISTENT_VIEWS))


def _check_providers(report: DiagnosticReport) -> None:
    for provider in MONITOR_PROVIDERS:
        report.add(f"Provider {provider}", "ok")
    if settings.instagram_provider == "disabled":
        report.add("Instagram", "aviso", "monitorado, porem nenhum provider esta configurado")


def _check_ai(report: DiagnosticReport) -> None:
    if settings.ai_provider == "gateway":
        report.add("IA", "ok" if settings.ai_gateway_url else "aviso", "gateway configurado" if settings.ai_gateway_url else "AI_GATEWAY_URL ausente")
    elif settings.ai_provider == "ollama":
        detail = "Ollama local pode ficar offline na ShardCloud se apontar para localhost"
        report.add("IA", "aviso" if "localhost" in settings.ollama_host or "127.0.0.1" in settings.ollama_host else "ok", detail)
    else:
        report.add("IA", "aviso", f"provider desconhecido: {settings.ai_provider}")


def format_report(report: DiagnosticReport) -> str:
    lines = ["DevVerse Diagnostics", f"Status geral: {'OK' if report.ok else 'ATENCAO'}", ""]
    for item in report.items:
        detail = f" - {item.detail}" if item.detail else ""
        lines.append(f"[{item.status.upper()}] {item.name}{detail}")
    return "\n".join(lines)


async def _run_cli() -> int:
    from .main import COGS

    report = await collect_diagnostics(cogs=COGS)
    print(format_report(report))
    return 0 if report.ok else 1


def main() -> None:
    raise SystemExit(asyncio.run(_run_cli()))


if __name__ == "__main__":
    main()
