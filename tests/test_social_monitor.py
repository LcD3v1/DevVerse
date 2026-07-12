from __future__ import annotations

import unittest

from bot.config import DEFAULT_INSTAGRAM_RSS_TEMPLATE, settings
from bot.services.monitor.social_monitor import SocialMonitor


class SocialMonitorStaticTests(unittest.TestCase):
    def test_social_monitor_class_exists(self) -> None:
        self.assertTrue(SocialMonitor)

    def test_instagram_rss_template_has_username_placeholder(self) -> None:
        template = settings.instagram_rss_template or DEFAULT_INSTAGRAM_RSS_TEMPLATE
        self.assertIn("{username}", template)


if __name__ == "__main__":
    unittest.main()
