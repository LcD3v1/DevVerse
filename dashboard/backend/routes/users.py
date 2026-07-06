from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..database import calculate_level, fetchall, fetchone


router = APIRouter(tags=["users"])


@router.get("/user/{user_id}")
async def get_user(user_id: int) -> dict[str, object]:
    user = await fetchone(
        """
        SELECT
            user_id,
            SUM(xp) AS xp,
            SUM(study_minutes) AS study_minutes,
            MAX(streak) AS streak,
            MAX(last_checkin) AS last_checkin,
            MAX(languages) AS languages,
            MAX(area) AS area,
            SUM(challenges_done) AS challenges_done
        FROM users
        WHERE user_id = ?
        GROUP BY user_id
        """,
        (user_id,),
    )
    if not user:
        raise HTTPException(status_code=404, detail="Usuario nao encontrado")

    tasks = await fetchall(
        """
        SELECT id, title, description, status, priority, due_date, created_at
        FROM tasks
        WHERE assigned_to = ? OR created_by = ?
        ORDER BY created_at DESC
        LIMIT 20
        """,
        (user_id, user_id),
    )

    xp = int(user["xp"] or 0)
    languages = [item.strip() for item in (user["languages"] or "").split(",") if item.strip()]

    return {
        **user,
        "xp": xp,
        "level": calculate_level(xp),
        "languages": languages,
        "tasks": tasks,
    }


@router.get("/leaderboard")
async def get_leaderboard() -> dict[str, object]:
    xp_ranking = await fetchall(
        """
        SELECT
            user_id,
            SUM(xp) AS xp,
            MAX(streak) AS streak,
            MAX(area) AS area,
            SUM(study_minutes) AS study_minutes
        FROM users
        GROUP BY user_id
        ORDER BY xp DESC
        LIMIT 10
        """
    )
    streak_ranking = await fetchall(
        """
        SELECT user_id, SUM(xp) AS xp, MAX(streak) AS streak
        FROM users
        GROUP BY user_id
        ORDER BY streak DESC, xp DESC
        LIMIT 10
        """
    )
    active_ranking = await fetchall(
        """
        SELECT
            user_id,
            COUNT(*) AS activity_count
        FROM (
            SELECT user_id FROM checkins
            UNION ALL
            SELECT user_id FROM pomodoro_sessions
            UNION ALL
            SELECT user_id FROM ai_logs
        )
        GROUP BY user_id
        ORDER BY activity_count DESC
        LIMIT 10
        """
    )

    for row in xp_ranking:
        row["level"] = calculate_level(int(row["xp"] or 0))

    return {
        "by_xp": xp_ranking,
        "by_streak": streak_ranking,
        "most_active": active_ranking,
    }
