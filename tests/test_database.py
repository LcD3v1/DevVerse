from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from bot.database import Database


class DatabaseTests(unittest.IsolatedAsyncioTestCase):
    async def test_database_setup_creates_expected_tables_and_indexes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "devverse-test.sqlite3")
            await db.connect()
            try:
                await db.setup()
                rows = await db.fetchall("SELECT name FROM sqlite_master WHERE type = 'table'")
                tables = {row["name"] for row in rows}
                for table in {
                    "guild_settings",
                    "user_profiles",
                    "monitors",
                    "sent_notifications",
                    "moderation_logs",
                    "monitor_logs",
                }:
                    self.assertIn(table, tables)
            finally:
                await db.close()

    async def test_user_profiles_deduplication_index(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            db = Database(Path(directory) / "devverse-test.sqlite3")
            await db.connect()
            try:
                await db.setup()
                await db.execute(
                    "INSERT OR IGNORE INTO user_profiles (guild_id, user_id, category, role_id) VALUES (?, ?, ?, ?)",
                    (1, 2, "area", 3),
                )
                await db.execute(
                    "INSERT OR IGNORE INTO user_profiles (guild_id, user_id, category, role_id) VALUES (?, ?, ?, ?)",
                    (1, 2, "area", 3),
                )
                rows = await db.fetchall("SELECT * FROM user_profiles WHERE guild_id = ? AND user_id = ?", (1, 2))
                self.assertEqual(1, len(rows))
            finally:
                await db.close()


if __name__ == "__main__":
    unittest.main()
