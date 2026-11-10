"""Userlar jadvali CRUD."""

from config import now_str
from db.connection import query

_UPDATABLE = {
    "full_name",
    "username",
    "password_hash",
    "msg_id",
    "bound_tg_id",
    "tg_username",
    "bound_at",
    "deleted",
}


def create_user(full_name: str, username: str, password_hash: str) -> dict:
    ts = now_str()
    return query(
        "INSERT INTO users (full_name, username, password_hash, created, updated) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING *",
        (full_name, username, password_hash, ts, ts),
        fetch="one",
    )


def get_by_username(username: str) -> dict | None:
    return query("SELECT * FROM users WHERE username = %s", (username,), fetch="one")


def get_by_id(user_id: int) -> dict | None:
    return query("SELECT * FROM users WHERE id = %s", (user_id,), fetch="one")


def get_by_bound_tg(tg_id: int) -> dict | None:
    return query(
        "SELECT * FROM users WHERE bound_tg_id = %s AND deleted = FALSE",
        (tg_id,),
        fetch="one",
    )


def list_users() -> list[dict]:
    return query("SELECT * FROM users WHERE deleted = FALSE ORDER BY id")


def update_user(user_id: int, **fields) -> dict | None:
    fields = {k: v for k, v in fields.items() if k in _UPDATABLE}
    fields["updated"] = now_str()
    assignments = ", ".join(f"{k} = %s" for k in fields)
    params = tuple(fields.values()) + (user_id,)
    return query(
        f"UPDATE users SET {assignments} WHERE id = %s RETURNING *", params, fetch="one"
    )


def delete_user(user_id: int) -> None:
    query("DELETE FROM users WHERE id = %s", (user_id,), fetch="none")


def bind_user(user_id: int, tg_id: int, tg_username: str | None) -> dict | None:
    return update_user(
        user_id,
        bound_tg_id=tg_id,
        tg_username=tg_username,
        bound_at=now_str(),
    )


def reset_binding(user_id: int) -> dict | None:
    return update_user(user_id, bound_tg_id=None, tg_username=None, bound_at=None)
