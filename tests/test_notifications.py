from __future__ import annotations

import unittest

from bot.services.monitor.notification_service import NotificationService


class NotificationStaticTests(unittest.TestCase):
    def test_notification_service_exists(self) -> None:
        self.assertTrue(NotificationService)


if __name__ == "__main__":
    unittest.main()
