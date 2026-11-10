"""Arenalar jadvali CRUD (savollar bilan birga yuklanadi)."""

from config import now_str
from db.connection import query


def create_arena(title: str, description: str) -> dict:
    ts = now_str()
    return query(
        "INSERT INTO arenas (title, description, created, updated) "
        "VALUES (%s, %s, %s, %s) RETURNING *",
        (title, description, ts, ts),
        fetch="one",
    )


def list_arenas(active_only: bool = False) -> list[dict]:
    if active_only:
        return query(
            "SELECT a.*, (SELECT COUNT(*) FROM questions q WHERE q.arena_id = a.id) "
            "AS question_count FROM arenas a WHERE a.active = TRUE ORDER BY a.id"
        )
    return query(
        "SELECT a.*, (SELECT COUNT(*) FROM questions q WHERE q.arena_id = a.id) "
        "AS question_count FROM arenas a ORDER BY a.id"
    )


def set_active(arena_id: int, active: bool) -> dict | None:
    ts = now_str()
    return query(
        "UPDATE arenas SET active = %s, updated = %s WHERE id = %s RETURNING *",
        (active, ts, arena_id),
        fetch="one",
    )


def get_arena(arena_id: int, with_questions: bool = True) -> dict | None:
    arena = query("SELECT * FROM arenas WHERE id = %s", (arena_id,), fetch="one")
    if not arena:
        return None
    if with_questions:
        arena["questions"] = query(
            "SELECT * FROM questions WHERE arena_id = %s ORDER BY position, id",
            (arena_id,),
        )
    return arena


def list_arena_questions(arena_id: int) -> list[dict]:
    return query(
        "SELECT * FROM questions WHERE arena_id = %s ORDER BY position, id",
        (arena_id,),
    )


def get_arena_attempts(arena_id: int) -> list[dict]:
    return query(
        "SELECT * FROM arena_attempts WHERE arena_id = %s", (arena_id,)
    )


def has_attempt(arena_id: int, user_id: int) -> bool:
    row = query(
        "SELECT 1 FROM arena_attempts WHERE arena_id = %s AND user_id = %s",
        (arena_id, user_id),
        fetch="one",
    )
    return row is not None


def add_attempt(arena_id: int, user_id: int) -> None:
    query(
        "INSERT INTO arena_attempts (arena_id, user_id, created) "
        "VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (arena_id, user_id, now_str()),
        fetch="none",
    )


def delete_arena(arena_id: int) -> None:
    # questions va arena_sessions jadvallarida ON DELETE CASCADE bor
    query("DELETE FROM arenas WHERE id = %s", (arena_id,), fetch="none")


# --- tugallanmagan arena sessiyalari (restart'dan tiklash uchun) ---

def create_session(user_id: int, arena_id: int, mcq_total: int) -> None:
    ts = now_str()
    query(
        "INSERT INTO arena_sessions (user_id, arena_id, q_index, mcq_total, created, updated) "
        "VALUES (%s, %s, 0, %s, %s, %s) "
        "ON CONFLICT (user_id) DO UPDATE SET arena_id = EXCLUDED.arena_id, q_index = 0, "
        "mcq_total = EXCLUDED.mcq_total, mcq_correct = 0, voice_count = 0, code_count = 0, "
        "awaiting = NULL, created = EXCLUDED.created, updated = EXCLUDED.updated",
        (user_id, arena_id, mcq_total, ts, ts),
        fetch="none",
    )


def get_session(user_id: int) -> dict | None:
    return query("SELECT * FROM arena_sessions WHERE user_id = %s", (user_id,), fetch="one")


def update_session(user_id: int, **fields) -> None:
    allowed = {"q_index", "mcq_total", "mcq_correct", "voice_count", "code_count", "awaiting"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    if not fields:
        return
    fields["updated"] = now_str()
    assignments = ", ".join(f"{k} = %s" for k in fields)
    params = tuple(fields.values()) + (user_id,)
    query(f"UPDATE arena_sessions SET {assignments} WHERE user_id = %s", params, fetch="none")


def delete_session(user_id: int) -> None:
    query("DELETE FROM arena_sessions WHERE user_id = %s", (user_id,), fetch="none")


def update_arena(arena_id: int, **fields) -> dict | None:
    allowed = {"title", "description", "msg_id", "active"}
    fields = {k: v for k, v in fields.items() if k in allowed}
    fields["updated"] = now_str()
    assignments = ", ".join(f"{k} = %s" for k in fields)
    params = tuple(fields.values()) + (arena_id,)
    return query(
        f"UPDATE arenas SET {assignments} WHERE id = %s RETURNING *", params, fetch="one"
    )
