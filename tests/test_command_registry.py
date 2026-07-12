from __future__ import annotations

import unittest

from bot.main import COGS


class CommandRegistryStaticTests(unittest.TestCase):
    def test_expected_command_cogs_are_enabled(self) -> None:
        expected = {
            "bot.cogs.setup",
            "bot.cogs.roles",
            "bot.cogs.monitor",
            "bot.cogs.moderation",
            "bot.cogs.help",
            "bot.cogs.diagnostics",
        }
        self.assertTrue(expected.issubset(set(COGS)))

    def test_no_duplicate_cog_registration(self) -> None:
        self.assertEqual(len(COGS), len(set(COGS)))


if __name__ == "__main__":
    unittest.main()
