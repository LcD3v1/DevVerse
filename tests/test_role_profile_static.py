from __future__ import annotations

import unittest

from bot.views.onboarding import ONBOARDING_GROUPS, OnboardingPanelView, OnboardingView


class RoleProfileStaticTests(unittest.TestCase):
    def test_select_menus_respect_discord_limit(self) -> None:
        for group in ONBOARDING_GROUPS.values():
            self.assertLessEqual(len(group["options"]), 25)

    def test_required_profile_groups_exist(self) -> None:
        for key in ("profile", "level", "specialties", "languages"):
            self.assertIn(key, ONBOARDING_GROUPS)

    def test_persistent_views_have_no_timeout(self) -> None:
        self.assertIsNone(OnboardingView().timeout)
        self.assertIsNone(OnboardingPanelView().timeout)

    def test_interactive_components_have_fixed_custom_ids(self) -> None:
        view = OnboardingView()
        custom_ids = [item.custom_id for item in view.children if getattr(item, "custom_id", None)]
        self.assertTrue(custom_ids)
        self.assertTrue(all(custom_id.startswith("devverse_") for custom_id in custom_ids))


if __name__ == "__main__":
    unittest.main()

