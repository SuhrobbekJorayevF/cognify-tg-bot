"""Natijalar va javob submissionlari (kelajakda statistika uchun)."""

from config import now_str
from db.connection import query


def add_result(user_id: int | None, kind: str, ref: str, correct: int, total: int, percent: int) -> None:
    query(
        "INSERT INTO test_results (user_id, kind, ref, correct, total, percent, created) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s)",
        (user_id, kind, ref, correct, total, percent, now_str()),
        fetch="none",
    )


def add_arena_submission(
    user_id: int | None, arena_id: int, question_id: int, kind: str, file_id: str
) -> None:
    query(
        "INSERT INTO arena_submissions (user_id, arena_id, question_id, kind, file_id, created) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (user_id, arena_id, question_id, kind, file_id, now_str()),
        fetch="none",
    )
