from __future__ import annotations

import unittest

from bot.cogs import moderation


class ModerationStaticTests(unittest.TestCase):
    def test_moderation_cog_exists(self) -> None:
        self.assertTrue(hasattr(moderation, "ModerationCog"))

    def test_clear_confirmation_view_exists(self) -> None:
        self.assertTrue(hasattr(moderation, "ClearConfirmView"))


if __name__ == "__main__":
    unittest.main()
