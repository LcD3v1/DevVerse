from __future__ import annotations

import unittest
import asyncio

import discord

from bot.main import COGS, DevVerseBot


class StartupTests(unittest.TestCase):
    def test_members_intent_is_enabled(self) -> None:
        bot = DevVerseBot()
        try:
            self.assertTrue(bot.intents.guilds)
            self.assertTrue(bot.intents.members)
            self.assertTrue(bot.intents.message_content)
        finally:
            asyncio.run(bot.close())

    def test_diagnostics_cog_is_registered_for_startup(self) -> None:
        self.assertIn("bot.cogs.diagnostics", COGS)

    def test_discord_dependency_is_available(self) -> None:
        self.assertTrue(discord.__version__)


if __name__ == "__main__":
    unittest.main()
