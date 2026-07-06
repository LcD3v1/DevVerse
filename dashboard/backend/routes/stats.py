from __future__ import annotations

from fastapi import APIRouter

from ..database import fetchone


router = APIRouter(tags=["stats"])


@router.get("/stats/server")
async def get_server_stats() -> dict[str, object]:
    users = await fetchone("SELECT COUNT(DISTINCT user_id) AS total FROM users")
    xp = await fetchone("SELECT COALESCE(SUM(xp), 0) AS total FROM users")
    tasks = await fetchone(
        """
        SELECT
            COUNT(*) AS total,
            COALESCE(SUM(CASE WHEN status IN ('concluida', 'concluída', 'done') THEN 1 ELSE 0 END), 0) AS completed
        FROM tasks
        """
    )
    ai = await fetchone("SELECT COUNT(*) AS total FROM ai_logs")
    study = await fetchone("SELECT COALESCE(SUM(focus_minutes), 0) AS total FROM pomodoro_sessions WHERE completed = 1")
    checkins = await fetchone("SELECT COUNT(*) AS total FROM checkins")

    return {
        "users": users["total"] if users else 0,
        "total_xp": xp["total"] if xp else 0,
        "tasks": tasks or {"total": 0, "completed": 0},
        "ai_logs": ai["total"] if ai else 0,
        "completed_focus_minutes": study["total"] if study else 0,
        "checkins": checkins["total"] if checkins else 0,
    }
