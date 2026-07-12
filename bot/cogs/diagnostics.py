from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.diagnostics import collect_diagnostics
from bot.permissions import admin_check
from bot.utils import make_embed


class DiagnosticsCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="diagnostico", description="Mostra a saude tecnica do DevVerse Assistant.")
    @admin_check()
    async def diagnostico(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        report = await collect_diagnostics(bot=self.bot)
        lines = []
        for item in report.items[:22]:
            icon = {"ok": "OK", "aviso": "AVISO", "erro": "ERRO", "critico": "CRITICO"}.get(item.status, item.status.upper())
            detail = f" - {item.detail}" if item.detail else ""
            lines.append(f"{icon} | {item.name}{detail}")
        title = "Diagnostico DevVerse"
        status = "Status geral: OK" if report.ok else "Status geral: ATENCAO"
        await interaction.followup.send(embed=make_embed(title, status + "\n\n" + "\n".join(lines)), ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(DiagnosticsCog(bot))
