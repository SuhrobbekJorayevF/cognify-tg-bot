"""Telegram kanal bilan barcha aloqalar shu yerda."""

import logging

from config import CHANNEL_ID
from services.formatting import (
    arena_card_text,
    channel_record_text,
    question_card_text,
)

logger = logging.getLogger(__name__)

# Kanal holati — startup'da tekshiriladi, admin panel ko'rsatadi
CHANNEL_STATUS: dict = {"ok": None, "detail": "tekshirilmagan"}


def channel_target() -> int | None:
    """CHANNEL_ID ni tekshiradi va int qaytaradi. Noto'g'ri bo'lsa None."""
    raw = (CHANNEL_ID or "").strip()
    if not raw:
        logger.error("CHANNEL_ID o'rnatilmagan — kanal xabarlari yuborilmaydi!")
        return None
    try:
        chat_id = int(raw)
    except ValueError:
        logger.error("CHANNEL_ID noto'g'ri format: %r — butun son bo'lishi kerak (-100...)", raw)
        return None
    if not (str(chat_id).startswith("-100") and len(str(chat_id)) >= 13):
        logger.warning("CHANNEL_ID g'alati format: %s (ideal: -100...)", chat_id)
    return chat_id


async def send_text(bot, text: str) -> int | None:
    target = channel_target()
    if not target:
        return None
    try:
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("Kanalga xabar yuborishda xatolik!")
        return None


async def _safe_edit(bot, chat_id: int, message_id: int, text: str) -> bool:
    try:
        await bot.edit_message_text(
            text, chat_id=chat_id, message_id=message_id, parse_mode="HTML"
        )
        return True
    except Exception:
        logger.exception("Kanal xabarini tahrirlashda xatolik (msg_id=%s)", message_id)
        return False


async def sync_user_card(bot, user: dict, is_new: bool = False, event: str | None = None) -> int | None:
    """User kartasini yaratadi/yangilaydi. Kanal xabar ID sini qaytaradi."""
    target = channel_target()
    if not target:
        return None
    if event is None:
        event = "🆕 YANGI USER" if is_new else "✏️ USER YANGILANDI"
    text = channel_record_text(user, event)
    if not is_new and user.get("msg_id"):
        if await _safe_edit(bot, target, user["msg_id"], text):
            return user["msg_id"]
        # eski karta o'chib ketgan — yangisini yuboramiz
        logger.warning("User kartasi topilmadi (msg_id=%s) — yangi karta yuboriladi", user["msg_id"])
    try:
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("User kartasini kanalga yuborishda xatolik")
        return None


async def sync_arena_card(bot, arena: dict) -> int | None:
    target = channel_target()
    if not target:
        return None
    text = arena_card_text(arena)
    if arena.get("msg_id"):
        if await _safe_edit(bot, target, arena["msg_id"], text):
            return arena["msg_id"]
        logger.warning("Arena kartasi topilmadi (msg_id=%s) — yangisi yuboriladi", arena["msg_id"])
    try:
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("Arena kartasini kanalga yuborishda xatolik")
        return None


async def post_question_card(bot, arena: dict, q: dict, index: int) -> int | None:
    target = channel_target()
    if not target:
        return None
    text = question_card_text(arena, q, index)
    try:
        msg = await bot.send_message(chat_id=target, text=text, parse_mode="HTML")
        return msg.message_id
    except Exception:
        logger.exception("Savol kartasini kanalga yuborishda xatolik")
        return None


async def delete_message(bot, msg_id) -> None:
    target = channel_target()
    if not target or not msg_id:
        return
    try:
        await bot.delete_message(chat_id=target, message_id=msg_id)
    except Exception:
        logger.exception("Kanal xabarini o'chirish bajarilmadi (msg_id=%s)", msg_id)


async def copy_to_channel(bot, from_chat_id: int, message_id: int, caption: str) -> int | None:
    """User yuborgan ovozli xabar/faylni kanalga nusxalaydi."""
    target = channel_target()
    if not target:
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


async def verify_channel(bot) -> bool:
    """Startup'da bir marta — kanal bor va bot admin ekanini tekshiradi."""
    target = channel_target()
    if not target:
        CHANNEL_STATUS.update(ok=False, detail="CHANNEL_ID o'rnatilmagan")
        return False
    try:
        chat = await bot.get_chat(target)
        me = await bot.get_me()
        member = await bot.get_chat_member(target, me.id)
        status = getattr(member, "status", "?")
        logger.info("Kanal topildi: %s (turi: %s, bot statusi: %s)", chat.title, chat.type, status)
        if status not in ("administrator", "creator"):
            CHANNEL_STATUS.update(ok=False, detail=f"Bot kanalda admin emas (status: {status})")
            logger.error("Bot kanalda ADMIN EMAS! Kartalar yuborilmaydi. Status: %s", status)
            return False
        CHANNEL_STATUS.update(ok=True, detail=f"OK ({chat.title})")
        return True
    except Exception:
        CHANNEL_STATUS.update(
            ok=False,
            detail="CHANNEL_ID noto'g'ri yoki bot kanalda yo'q",
        )
        logger.exception(
            "Kanal tekshiruvi muvaffaqiyatsiz! CHANNEL_ID=%s noto'g'ri yoki bot kanalda yo'q.", target
        )
        return False
