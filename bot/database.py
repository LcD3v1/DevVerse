from __future__ import annotations

from pathlib import Path
from typing import Any

import aiosqlite


class Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.conn: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON")

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Cursor:
        assert self.conn
        cursor = await self.conn.execute(sql, params)
        await self.conn.commit()
        return cursor

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> aiosqlite.Row | None:
        assert self.conn
        async with self.conn.execute(sql, params) as cursor:
            return await cursor.fetchone()

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[aiosqlite.Row]:
        assert self.conn
        async with self.conn.execute(sql, params) as cursor:
            return await cursor.fetchall()

    async def setup(self) -> None:
        assert self.conn
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                xp INTEGER NOT NULL DEFAULT 0,
                study_minutes INTEGER NOT NULL DEFAULT 0,
                streak INTEGER NOT NULL DEFAULT 0,
                last_checkin TEXT,
                languages TEXT NOT NULL DEFAULT '',
                area TEXT NOT NULL DEFAULT '',
                challenges_done INTEGER NOT NULL DEFAULT 0,
                last_message_xp TEXT,
                PRIMARY KEY (guild_id, user_id)
            );
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                ai_channel_id INTEGER,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS created_items (
                guild_id INTEGER NOT NULL,
                item_type TEXT NOT NULL,
                item_id INTEGER NOT NULL,
                item_name TEXT NOT NULL,
                PRIMARY KEY (guild_id, item_type, item_id)
            );
            CREATE TABLE IF NOT EXISTS checkins (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                topic TEXT NOT NULL,
                planned_minutes INTEGER NOT NULL,
                difficulty TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                assigned_to INTEGER,
                created_by INTEGER NOT NULL,
                due_date TEXT,
                status TEXT NOT NULL DEFAULT 'aberta',
                priority TEXT NOT NULL DEFAULT 'media',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS pomodoro_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                focus_minutes INTEGER NOT NULL,
                break_minutes INTEGER NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS ai_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                command TEXT NOT NULL,
                prompt TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS achievements (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                achievement TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, achievement)
            );
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS moderation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                moderator_id INTEGER NOT NULL,
                channel_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                amount INTEGER NOT NULL DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS github_links (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                repo_url TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, repo_url)
            );
            CREATE TABLE IF NOT EXISTS monitors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                source TEXT NOT NULL,
                channel_id INTEGER NOT NULL,
                filters TEXT NOT NULL DEFAULT '',
                frequency_minutes INTEGER NOT NULL DEFAULT 60,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                last_check TEXT,
                last_error TEXT,
                last_result_count INTEGER NOT NULL DEFAULT 0,
                UNIQUE(guild_id, type, source)
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                external_id TEXT NOT NULL DEFAULT '',
                unique_hash TEXT NOT NULL DEFAULT '',
                sent_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(type, url)
            );
            CREATE TABLE IF NOT EXISTS sent_notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                external_id TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(type, external_id, url)
            );
            CREATE TABLE IF NOT EXISTS monitor_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                executed_at TEXT DEFAULT CURRENT_TIMESTAMP,
                items_found INTEGER NOT NULL DEFAULT 0,
                errors INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS monitor_item_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT NOT NULL,
                title TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL DEFAULT '',
                channel_id INTEGER,
                status TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                company TEXT NOT NULL DEFAULT '',
                url TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT '',
                external_id TEXT NOT NULL DEFAULT '',
                unique_hash TEXT NOT NULL DEFAULT '',
                date_found TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(url)
            );
            CREATE TABLE IF NOT EXISTS hackathons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                url TEXT NOT NULL,
                date_found TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(url)
            );
            CREATE TABLE IF NOT EXISTS social_posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                platform TEXT NOT NULL,
                creator TEXT NOT NULL,
                url TEXT NOT NULL,
                date_found TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(platform, url)
            );
            CREATE TABLE IF NOT EXISTS content_tags (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content_id INTEGER NOT NULL,
                tag TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        await self._rebuild_user_profiles_if_needed()
        await self._ensure_column("user_profiles", "category", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("user_profiles", "role_id", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("monitors", "last_result_count", "INTEGER NOT NULL DEFAULT 0")
        await self._ensure_column("notifications", "source", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("notifications", "external_id", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("notifications", "unique_hash", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("jobs", "source", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("jobs", "external_id", "TEXT NOT NULL DEFAULT ''")
        await self._ensure_column("jobs", "unique_hash", "TEXT NOT NULL DEFAULT ''")
        await self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_notifications_unique_hash ON notifications(unique_hash) WHERE unique_hash <> ''")
        await self.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_unique_hash ON jobs(unique_hash) WHERE unique_hash <> ''")
        await self.conn.commit()

    async def _ensure_column(self, table: str, column: str, definition: str) -> None:
        assert self.conn
        async with self.conn.execute(f"PRAGMA table_info({table})") as cursor:
            columns = {row["name"] for row in await cursor.fetchall()}
        if column not in columns:
            await self.conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")

    async def _rebuild_user_profiles_if_needed(self) -> None:
        assert self.conn
        async with self.conn.execute("PRAGMA table_info(user_profiles)") as cursor:
            columns = await cursor.fetchall()
        has_id = any(row["name"] == "id" for row in columns)
        if has_id:
            return
        await self.conn.execute("ALTER TABLE user_profiles RENAME TO user_profiles_legacy")
        await self.conn.execute(
            """
            CREATE TABLE user_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                category TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

    async def add_created_item(self, guild_id: int, item_type: str, item_id: int, item_name: str) -> None:
        await self.execute(
            "INSERT OR IGNORE INTO created_items (guild_id, item_type, item_id, item_name) VALUES (?, ?, ?, ?)",
            (guild_id, item_type, item_id, item_name),
        )

    async def add_xp(self, guild_id: int, user_id: int, amount: int) -> None:
        await self.execute(
            """
            INSERT INTO users (guild_id, user_id, xp) VALUES (?, ?, ?)
            ON CONFLICT(guild_id, user_id) DO UPDATE SET xp = xp + excluded.xp
            """,
            (guild_id, user_id, amount),
        )
