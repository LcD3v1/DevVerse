from __future__ import annotations

import unittest

from bot.views.onboarding import EXTRA_ONBOARDING_GROUPS, PRIMARY_ONBOARDING_GROUPS


class RoleUpdateStaticTests(unittest.TestCase):
    def test_primary_and_extra_groups_do_not_overlap(self) -> None:
        self.assertFalse(set(PRIMARY_ONBOARDING_GROUPS).intersection(EXTRA_ONBOARDING_GROUPS))


if __name__ == "__main__":
    unittest.main()
