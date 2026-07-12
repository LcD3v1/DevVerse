from __future__ import annotations

import unittest

from bot.services.monitor.models import MonitorItem


class DeduplicationTests(unittest.TestCase):
    def test_monitor_item_can_carry_deduplication_keys(self) -> None:
        item = MonitorItem(
            type="job",
            title="Backend",
            url="https://example.com/a",
            source="linkedin",
            metadata={"source": "linkedin", "external_id": "abc", "unique_hash": "linkedin:abc:https://example.com/a"},
        )
        self.assertEqual("linkedin", item.metadata["source"])
        self.assertEqual("abc", item.metadata["external_id"])
        self.assertIn(item.url, item.metadata["unique_hash"])


if __name__ == "__main__":
    unittest.main()
