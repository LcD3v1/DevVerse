from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.templates import RESOURCES
from bot.utils import make_embed


class ResourcesCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="resource", description="Retorna recursos gratuitos por tema.")
    async def resource(self, interaction: discord.Interaction, tema: str) -> None:
        key = tema.lower().strip()
        resources = RESOURCES.get(key)
        if not resources:
            options = ", ".join(sorted(RESOURCES))
            await interaction.response.send_message(embed=make_embed("Tema não encontrado", f"Tente um destes temas: {options}"), ephemeral=True)
            return
        await interaction.response.send_message(embed=make_embed(f"Recursos: {tema}", "\n".join(f"- {item}" for item in resources)))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(ResourcesCog(bot))
