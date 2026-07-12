from __future__ import annotations

import importlib.util
import unittest


class ApiStaticTests(unittest.TestCase):
    def test_dashboard_backend_entrypoint_exists(self) -> None:
        self.assertIsNotNone(importlib.util.find_spec("dashboard.backend.main"))


if __name__ == "__main__":
    unittest.main()
