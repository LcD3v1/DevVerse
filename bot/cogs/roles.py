from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.permissions import admin_check
from bot.templates import ROLE_PANEL_GROUPS
from bot.utils import make_embed
from bot.views.role_menu import RolePanelView


class RolesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="rolepanel", description="Cria o painel de autoatribuição de cargos.")
    @admin_check()
    async def rolepanel(self, interaction: discord.Interaction) -> None:
        embed = make_embed("Painel de Cargos", "Escolha suas especialidades, linguagens, frameworks, sistemas, objetivos e status.")
        await interaction.response.send_message(embed=embed, view=RolePanelView(ROLE_PANEL_GROUPS))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(RolesCog(bot))
