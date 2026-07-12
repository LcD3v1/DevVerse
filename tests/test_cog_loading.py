from __future__ import annotations

import importlib
import unittest

from bot.config import settings
from bot.main import COGS


class CogLoadingTests(unittest.TestCase):
    def test_all_enabled_cogs_are_importable(self) -> None:
        failures: list[str] = []
        for cog in COGS:
            if cog.endswith(".github") and not settings.enable_github:
                continue
            try:
                importlib.import_module(cog)
            except Exception as exc:  # pragma: no cover - failure message is the useful assertion output
                failures.append(f"{cog}: {exc.__class__.__name__}: {exc}")
        self.assertEqual([], failures)


if __name__ == "__main__":
    unittest.main()
