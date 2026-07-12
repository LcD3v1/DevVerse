from __future__ import annotations

import unittest

from bot.cogs import setup, study_channels


class SetupStaticTests(unittest.TestCase):
    def test_setup_cogs_are_available(self) -> None:
        self.assertTrue(hasattr(setup, "SetupCog"))
        self.assertTrue(hasattr(study_channels, "StudyChannelsCog"))


if __name__ == "__main__":
    unittest.main()
