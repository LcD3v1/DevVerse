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
            CREATE TABLE IF NOT EXISTS github_links (
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                repo_url TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (guild_id, user_id, repo_url)
            );
            """
        )
        await self.conn.commit()

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
