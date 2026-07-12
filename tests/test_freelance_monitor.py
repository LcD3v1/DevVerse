from __future__ import annotations

import unittest

from bot.services.monitor.freelance_monitor import FreelanceMonitor
from bot.services.monitor.providers.freelance import fiverr_provider, freelancer_provider, upwork_provider


class FreelanceMonitorStaticTests(unittest.TestCase):
    def test_freelance_monitor_class_exists(self) -> None:
        self.assertTrue(FreelanceMonitor)

    def test_freelance_providers_are_importable(self) -> None:
        self.assertTrue(hasattr(upwork_provider, "UpworkFreelanceProvider"))
        self.assertTrue(hasattr(freelancer_provider, "FreelancerProvider"))
        self.assertTrue(hasattr(fiverr_provider, "FiverrFreelanceProvider"))


if __name__ == "__main__":
    unittest.main()
