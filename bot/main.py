from __future__ import annotations

import asyncio
import logging

import discord
from discord.ext import commands

from .config import settings
from .database import Database
from .utils import make_embed


COGS = [
    "bot.cogs.setup",
    "bot.cogs.roles",
    "bot.cogs.ai_assistant",
    "bot.cogs.pomodoro",
    "bot.cogs.tasks",
    "bot.cogs.study",
    "bot.cogs.profile",
    "bot.cogs.moderation",
    "bot.cogs.resources",
    "bot.cogs.roadmap",
    "bot.cogs.github",
]


class DevVerseBot(commands.Bot):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        intents.guilds = True
        super().__init__(command_prefix=settings.command_prefix, intents=intents)
        self.db = Database(settings.database_path)

    async def setup_hook(self) -> None:
        await self.db.connect()
        await self.db.setup()
        for cog in COGS:
            if cog.endswith(".github") and not settings.enable_github:
                continue
            await self.load_extension(cog)
        if settings.guild_id:
            guild = discord.Object(id=settings.guild_id)
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
        else:
            await self.tree.sync()

    async def close(self) -> None:
        await self.db.close()
        await super().close()

    async def on_ready(self) -> None:
        logging.getLogger("devverse").info("Online como %s", self.user)

    async def on_app_command_error(self, interaction: discord.Interaction, error: Exception) -> None:
        embed = make_embed("Ops, algo deu errado", str(error), discord.Color.red())
        if interaction.response.is_done():
            await interaction.followup.send(embed=embed, ephemeral=True)
        else:
            await interaction.response.send_message(embed=embed, ephemeral=True)


async def runner() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
    if not settings.token:
        raise RuntimeError("Defina DISCORD_TOKEN no arquivo .env.")
    bot = DevVerseBot()

    @bot.tree.command(name="ping", description="Testa se o bot está online.")
    async def ping(interaction: discord.Interaction) -> None:
        await interaction.response.send_message(embed=make_embed("Pong!", "DevVerse Assistant está online."))

    await bot.start(settings.token)


def main() -> None:
    asyncio.run(runner())
