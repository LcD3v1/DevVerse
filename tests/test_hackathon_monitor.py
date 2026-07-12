from __future__ import annotations

import unittest

from bot.services.monitor.hackathon_monitor import HackathonMonitor
from bot.services.monitor.models import MonitorItem


class HackathonMonitorStaticTests(unittest.TestCase):
    def test_hackathon_monitor_class_exists(self) -> None:
        self.assertTrue(HackathonMonitor)

    def test_monitor_item_supports_hackathon_payload(self) -> None:
        item = MonitorItem(type="hackathons", title="Hack Test", url="https://example.com", source="devpost")
        self.assertEqual("hackathons", item.type)
        self.assertEqual("devpost", item.source)


if __name__ == "__main__":
    unittest.main()
