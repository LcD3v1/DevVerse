from __future__ import annotations

import unittest

from bot.permissions import ADMIN_ROLE_NAMES, MENTOR_ROLE_NAMES


class PermissionStaticTests(unittest.TestCase):
    def test_admin_and_mentor_roles_are_declared(self) -> None:
        self.assertTrue(ADMIN_ROLE_NAMES)
        self.assertTrue(MENTOR_ROLE_NAMES)


if __name__ == "__main__":
    unittest.main()
