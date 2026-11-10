"""Telegram kanal bilan barcha aloqalar shu yerda."""

import logging

from config import CHANNEL_ID
from services.formatting import (
    arena_card_text,
    channel_record_text,
    question_card_text,
)

logger = logging.getLogger(__name__)


def _channel_target():
    return int(CHANNEL_ID) if CHANNEL_ID else None


async def send_text(bot, text: str) -> None:
    target = _channel_target()
    if not target:
        logger.warning("CHANNEL_ID o'rnatilmagan — kanal xabari o'tkazib yuborildi.")
        return
    await bot.send_message(chat_id=target, text=text, parse_mode="HTML")


async def sync_user_card(bot, user: dict, is_new: bool = False, event: str | None = None) -> int | None:
    """User kartasini yaratadi/yangilaydi. Kanal xabar ID sini qaytaradi."""
    target = _channel_target()
    if not target:
        logger.warning("CHANNEL_ID o'rnatilmagan — kanal sinxronlash o'tkazib yuborildi.")
        return user.get("msg_id")
    if event is None:
        event = "🆕 YANGI USER" if is_new else "✏️ USER YANGILANDI"
    text = channel_record_text(user, event)
    try:
        if is_new or not user.get("msg_id"):
            msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
            return msg.message_id
        await bot.edit_message_text(
            text, chat_id=target, message_id=user["msg_id"], parse_mode="HTML"
        )
        return user["msg_id"]
    except Exception:
        logger.exception("User kartasini sinxronlashda xatolik")
        return user.get("msg_id")


async def sync_arena_card(bot, arena: dict) -> int | None:
    target = _channel_target()
    if not target:
        logger.warning("CHANNEL_ID o'rnatilmagan — arena sinxronlash o'tkazib yuborildi.")
        return arena.get("msg_id")
    text = arena_card_text(arena)
    try:
        if arena.get("msg_id"):
            await bot.edit_message_text(
                text, chat_id=target, message_id=arena["msg_id"], parse_mode="HTML"
            )
            return arena["msg_id"]
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("Arena kartasini sinxronlashda xatolik")
        return arena.get("msg_id")


async def post_question_card(bot, arena: dict, q: dict, index: int) -> int | None:
    target = _channel_target()
    if not target:
        logger.warning("CHANNEL_ID o'rnatilmagan — savol kartasi yuborilmadi.")
        return None
    text = question_card_text(arena, q, index)
    try:
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("Savol kartasini kanalga yuborishda xatolik")
        return None


async def delete_message(bot, msg_id) -> None:
    target = _channel_target()
    if not target or not msg_id:
        return
    try:
        await bot.delete_message(chat_id=target, message_id=msg_id)
    except Exception:
        logger.exception("Kanal xabarini o'chirish bajarilmadi (msg_id=%s)", msg_id)


async def copy_to_channel(bot, from_chat_id: int, message_id: int, caption: str) -> int | None:
    """User yuborgan ovozli xabar/faylni kanalga nusxalaydi."""
    target = _channel_target()
    if not target:
        logger.warning("CHANNEL_ID o'rnatilmagan — javob nusxalanmadi.")
        return None
    try:
        msg = await bot.copy_message(
            chat_id=target,
            from_chat_id=from_chat_id,
            message_id=message_id,
            caption=caption,
        )
        return msg.message_id
    except Exception:
        logger.exception("Javobni kanalga nusxalashda xatolik")
        return None
