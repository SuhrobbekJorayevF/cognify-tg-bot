"""Umumiy yordamchi funksiyalar (handlerlar o'rtasida)."""

from config import ADMIN_ID
from db import users as db_users


def is_admin(user) -> bool:
    return bool(ADMIN_ID) and str(user.id) == ADMIN_ID


def recognize(tg_id: int) -> dict | None:
    """Telegram ID bo'yicha avtomatik tanish."""
    return db_users.get_by_bound_tg(tg_id)


def full_name_of(user) -> str:
    return " ".join(
        part for part in [user.first_name, user.last_name] if part
    ) or "Noma'lum"


def tg_username_of(user) -> str | None:
    return user.username or None
