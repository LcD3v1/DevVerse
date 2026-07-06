from __future__ import annotations

from fastapi import APIRouter

from ..database import fetchall


router = APIRouter(tags=["tasks"])


@router.get("/tasks/{user_id}")
async def get_tasks(user_id: int) -> dict[str, object]:
    tasks = await fetchall(
        """
        SELECT
            id,
            guild_id,
            title,
            description,
            assigned_to,
            created_by,
            due_date,
            status,
            priority,
            created_at
        FROM tasks
        WHERE assigned_to = ? OR created_by = ?
        ORDER BY
            CASE status
                WHEN 'aberta' THEN 0
                WHEN 'em progresso' THEN 1
                WHEN 'concluida' THEN 2
                ELSE 3
            END,
            created_at DESC
        """,
        (user_id, user_id),
    )
    return {"user_id": user_id, "tasks": tasks}
