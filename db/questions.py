"""Savollar jadvali CRUD."""

import psycopg2.extras

from config import now_str
from db.connection import query

Q_TYPES = ("mcq", "voice", "code")


def add_question(
    arena_id: int,
    qtype: str,
    text: str,
    options: list[str] | None = None,
    answer: int | None = None,
) -> dict:
    if qtype not in Q_TYPES:
        raise ValueError(f"Noma'lum savol turi: {qtype}")
    row = query(
        "SELECT COALESCE(MAX(position), 0) + 1 AS pos FROM questions WHERE arena_id = %s",
        (arena_id,),
        fetch="one",
    )
    position = row["pos"]
    created = now_str()
    return query(
        "INSERT INTO questions (arena_id, position, type, text, options, answer, created) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *",
        (
            arena_id,
            position,
            qtype,
            text,
            psycopg2.extras.Json(options) if options is not None else None,
            answer,
            created,
        ),
        fetch="one",
    )


def get_question(question_id: int) -> dict | None:
    return query("SELECT * FROM questions WHERE id = %s", (question_id,), fetch="one")


def set_question_msg_id(question_id: int, msg_id: int) -> None:
    query(
        "UPDATE questions SET msg_id = %s WHERE id = %s",
        (msg_id, question_id),
        fetch="none",
    )


def delete_question(question_id: int) -> None:
    query("DELETE FROM questions WHERE id = %s", (question_id,), fetch="none")
