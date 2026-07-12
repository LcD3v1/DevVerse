from __future__ import annotations

import unittest

from bot.services.monitor.monitor_manager import MonitorRunStats
from bot.services.monitor.providers import indeed_provider, linkedin_provider, public_jobs_provider


class JobsMonitorStaticTests(unittest.TestCase):
    def test_job_providers_are_available(self) -> None:
        self.assertTrue(hasattr(linkedin_provider, "LinkedInJobsProvider"))
        self.assertTrue(hasattr(indeed_provider, "IndeedJobsProvider"))
        self.assertTrue(hasattr(public_jobs_provider, "PublicJobsProvider"))

    def test_monitor_stats_counter_contract(self) -> None:
        stats = MonitorRunStats(found=9, new=9, sent=9, duplicates=0, errors=0)
        self.assertEqual(9, stats.found)
        self.assertEqual(stats.new, stats.sent + stats.duplicates)


if __name__ == "__main__":
    unittest.main()
