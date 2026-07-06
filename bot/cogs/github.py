from __future__ import annotations

import discord
from discord import app_commands
from discord.ext import commands

from bot.utils import make_embed


class GitHubCog(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot

    @app_commands.command(name="github_link", description="Salva o repositório GitHub de um projeto.")
    async def github_link(self, interaction: discord.Interaction, repo_url: str) -> None:
        if not interaction.guild:
            await interaction.response.send_message("Use dentro de um servidor.", ephemeral=True)
            return
        if not repo_url.startswith(("https://github.com/", "http://github.com/")):
            await interaction.response.send_message("Envie uma URL do GitHub válida.", ephemeral=True)
            return
        await self.bot.db.execute("INSERT OR IGNORE INTO github_links (guild_id, user_id, repo_url) VALUES (?, ?, ?)", (interaction.guild.id, interaction.user.id, repo_url))
        await interaction.response.send_message(embed=make_embed("Repositório salvo", repo_url))


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(GitHubCog(bot))
