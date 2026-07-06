from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import aiosqlite


BASE_DIR = Path(__file__).resolve().parents[2]
DATABASE_PATH = BASE_DIR / os.getenv("DATABASE_PATH", "data/database.sqlite3")


def row_to_dict(row: aiosqlite.Row | None) -> dict[str, Any] | None:
    if row is None:
        return None
    return dict(row)


async def fetchone(sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cursor:
            return row_to_dict(await cursor.fetchone())


async def fetchall(sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    async with aiosqlite.connect(DATABASE_PATH) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute(sql, params) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


def calculate_level(xp: int) -> int:
    return max(1, (xp // 500) + 1)
