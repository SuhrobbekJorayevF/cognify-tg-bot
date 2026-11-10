"""Coding Arena — FOYDALANUVCHI tomoni (arena yechish).

Urinish holati (user_data) faqat oyna — asosiy saqlash Postgres'dagi
`arena_sessions` jadvalida. Bot restart bo'lsa ham /start dan davom etish mumkin.
"""

from telegram import Update
from telegram.ext import ContextTypes

from db import arenas as db_arenas
from db import results as db_results
from handlers.common import full_name_of, is_admin, recognize
from keyboards import ARENA_FINAL_KEYBOARD, arena_answer_keyboard
from services import channel as channel_service
from services.formatting import Q_MCQ, Q_VOICE, Q_CODE, answer_caption, esc, now_str


# =========================================================
# State (attempt) — user_data <-> arena_sessions jadvali
# =========================================================

def attempt_state(context) -> dict | None:
    return context.user_data.get("attempt")


def _session_to_att(s: dict, user_id: int) -> dict:
    return {
        "arena_id": s["arena_id"],
        "user_id": user_id,
        "index": s["q_index"],
        "mcq_total": s["mcq_total"],
        "mcq_correct": s["mcq_correct"],
        "voice_count": s["voice_count"],
        "code_count": s["code_count"],
    }


def restore_attempt(context, user_id: int) -> dict | None:
    """user_data da attempt bo'lmasa, DB dan tiklaydi (restart'dan keyin)."""
    att = context.user_data.get("attempt")
    if att:
        return att
    s = db_arenas.get_session(user_id)
    if not s:
        return None
    att = _session_to_att(s, user_id)
    context.user_data["attempt"] = att
    awaiting = s.get("awaiting")
    if awaiting:
        context.user_data["state"] = awaiting
    return att


def restore_for_user(context, user) -> dict | None:
    known = recognize(user.id)
    if not known:
        return None
    return restore_attempt(context, known["id"])


def persist_attempt(context) -> None:
    att = context.user_data.get("attempt")
    if not att:
        return
    uid = att.get("user_id")
    if not uid:
        return
    db_arenas.update_session(
        uid,
        q_index=att["index"],
        mcq_total=att["mcq_total"],
        mcq_correct=att["mcq_correct"],
        voice_count=att["voice_count"],
        code_count=att["code_count"],
        awaiting=context.user_data.get("state"),
    )


# =========================================================
# Yordamchi
# =========================================================

async def _edit_or_reply(message, text, **kwargs) -> None:
    """Xabarni tahrirlaydi — matnli bo'lsa edit, media bo'lsa yangi xabar."""
    if getattr(message, "text", None):
        await message.edit_text(text, **kwargs)
    else:
        await message.reply_text(text, **kwargs)


async def show_arena_question(message, context: ContextTypes.DEFAULT_TYPE) -> None:
    att = context.user_data["attempt"]
    arena = db_arenas.get_arena(att["arena_id"])
    if arena is None:
        await _edit_or_reply(
            message, "Arena topilmadi yoki o'chirilgan.", reply_markup=ARENA_FINAL_KEYBOARD
        )
        return
    questions = arena["questions"]
    if att["index"] >= len(questions):
        # arena savollari o'zgardi — tugagani deb hisoblaymiz
        await finish_arena(message, context, None)
        return
    q = questions[att["index"]]
    total = len(questions)
    pos = att["index"] + 1

    base = (
        f"🏟 <b>Arena #{arena['id']}: {esc(arena['title'])}</b>\n"
        f"Savol {pos}/{total}\n\n"
        f"❓ {esc(q['text'])}\n\n"
    )
    if q["type"] == Q_MCQ:
        context.user_data.pop("state", None)
        options = q.get("options") or []
        await _edit_or_reply(
            message,
            base + "👆 Bitta javobni tanlang:",
            parse_mode="HTML",
            reply_markup=arena_answer_keyboard(options),
        )
        persist_attempt(context)
    elif q["type"] == Q_VOICE:
        context.user_data["state"] = "awaiting_voice"
        await _edit_or_reply(
            message,
            base
            + "🎤 Bu — ta'rifla savoli.\n"
            + "Javobingizni <b>ovozli xabar</b> qilib yuboring "
            + "(tekst yozmang, aynan ovozli xabar kutiladi).",
            parse_mode="HTML",
            reply_markup=None,
        )
        persist_attempt(context)
    elif q["type"] == Q_CODE:
        context.user_data["state"] = "awaiting_code"
        await _edit_or_reply(
            message,
            base
            + "💻 Bu — amaliy (practice) savol.\n"
            + "Amaliyotni bajaring va yechimingizni <b>.py fayl</b> qilib shu yerga tashlang.",
            parse_mode="HTML",
            reply_markup=None,
        )
        persist_attempt(context)


async def advance_arena(message, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    att = context.user_data["attempt"]
    att["index"] += 1
    persist_attempt(context)
    arena = db_arenas.get_arena(att["arena_id"])
    if arena and att["index"] < len(arena["questions"]):
        await show_arena_question(message, context)
        return
    await finish_arena(message, context, user)


async def finish_arena(message, context: ContextTypes.DEFAULT_TYPE, user) -> None:
    att = context.user_data.pop("attempt")
    context.user_data.pop("state", None)
    if att.get("user_id"):
        db_arenas.delete_session(att["user_id"])

    arena = db_arenas.get_arena(att["arena_id"], with_questions=False)
    arena_title = arena["title"] if arena else "?"

    mcq_total = att["mcq_total"]
    mcq_correct = att["mcq_correct"]
    summary = (
        "🏁 <b>Arena yakunlandi!</b>\n\n"
        f"🏟 Arena: {esc(arena_title)}\n\n"
        "Rahmat, qatnashganingiz uchun! 🙌\n"
        "Natijalar <b>Cognify</b> asosiy kanalida e'lon qilinadi. 📢"
    )

    await _edit_or_reply(
        message, summary, parse_mode="HTML", reply_markup=ARENA_FINAL_KEYBOARD
    )

    known = recognize(user.id) if user else None
    total_answered = mcq_total + att["voice_count"] + att["code_count"]
    percent = round(mcq_correct / mcq_total * 100) if mcq_total else 0
    db_results.add_result(
        known["id"] if known else None,
        "arena",
        f"arena#{att['arena_id']} {arena_title}",
        mcq_correct,
        mcq_total,
        percent,
    )

    login_line = f"🔐 Login: @{esc(known['username'])}\n" if known else ""
    tg_id = user.id if user else "—"
    full_name = full_name_of(user) if user else "Noma'lum"
    report = (
        "🏟 <b>Arena yechildi</b>\n\n"
        f"🏟 Arena: #{att['arena_id']} {esc(arena_title)}\n"
        f"👤 Ism: {esc(full_name)}\n"
        f"🆔 Telegram ID: <code>{tg_id}</code>\n"
        f"{login_line}"
        f"🔤 MCQ: {mcq_correct}/{mcq_total}\n"
        f"🎤 Ovozli javoblar: {att['voice_count']}\n"
        f"💻 Kod javoblari: {att['code_count']}\n"
        f"📝 Jami javoblar: {total_answered}\n"
        f"🕐 Sana/vaqt: {now_str()} (UTC+5)"
    )
    await channel_service.send_text(context.bot, report)


async def forward_answer_to_channel(context, update: Update, caption: str):
    return await channel_service.copy_to_channel(
        context.bot,
        update.effective_chat.id,
        update.effective_message.message_id,
        caption,
    )


# --- Tugma dispatch yordamchilari ---

async def handle_arena_user(query, context, admin: bool) -> None:
    from keyboards import main_keyboard

    await query.answer()
    context.user_data.pop("state", None)
    arenas = db_arenas.list_arenas(active_only=True)
    if not arenas:
        await query.edit_message_text(
            "🏟️ Hozircha ochiq arena yo'q.\nTez orada ochiladi — kuting! 🔔",
            reply_markup=main_keyboard(admin),
        )
        return
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup

    buttons = [
        [
            InlineKeyboardButton(
                f"🏟 {a['title']} ({a.get('question_count', 0)} savol)",
                callback_data=f"astart:{a['id']}",
            )
        ]
        for a in arenas
    ]
    buttons.append([InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")])
    await query.edit_message_text(
        "🏟️ <b>Kod Arenasi</b>\n\nQaysi arenani yechmoqchisiz?",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(buttons),
    )


async def handle_arena_start(query, context, data: str, user=None) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    if not arena["questions"]:
        await query.answer("Bu arenada hali savollar yo'q.", show_alert=True)
        return
    if user is None:
        user = query.from_user
    admin = is_admin(user)
    known = recognize(user.id)

    if known and not admin:
        uid = known["id"]
        # 1) Yarim qolgan sessiya bormi — davom etishga ruxsat (fast-track)
        s = db_arenas.get_session(uid)
        if s:
            if s["arena_id"] != arena_id:
                await query.answer(
                    "⚠️ Boshqa arena davom etmoqda. Avval uni tugating!",
                    show_alert=True,
                )
                return
            att = restore_attempt(context, uid)
            att["mcq_total"] = sum(1 for q in arena["questions"] if q["type"] == Q_MCQ)
            att["user_id"] = uid
            persist_attempt(context)
            await query.answer("▶️ Davom etayapmiz…")
            await show_arena_question(query.message, context)
            return
        # 2) Oldindan tugaganmi — blok
        if db_arenas.has_attempt(arena_id, uid):
            await query.answer(
                "⛔ Siz bu arenani allaqachon topshirgansiz.\n"
                "Natijalar e'lon qilinadi.",
                show_alert=True,
            )
            return
        # 3) Arena ochiqligini tekshirish (yangi urinish uchun)
        if not arena.get("active", False):
            await query.answer(
                "🔒 Bu arena hozir yopiq.\nOchilishini kuting!",
                show_alert=True,
            )
            return

        # 4) Yangi urinish — attempt shu zahoti sarflanadi
        mcq_total = sum(1 for q in arena["questions"] if q["type"] == Q_MCQ)
        context.user_data["attempt"] = {
            "arena_id": arena_id,
            "user_id": uid,
            "index": 0,
            "mcq_total": mcq_total,
            "mcq_correct": 0,
            "voice_count": 0,
            "code_count": 0,
        }
        context.user_data.pop("state", None)
        db_arenas.create_session(uid, arena_id, mcq_total)
        db_arenas.add_attempt(arena_id, uid)
        persist_attempt(context)
        await query.answer()
        await show_arena_question(query.message, context)
        return

    # Admin (yoki bog'lanmagan) — tezkor, sessiyasiz preview
    await query.answer()
    context.user_data["attempt"] = {
        "arena_id": arena_id,
        "user_id": None,
        "index": 0,
        "mcq_total": sum(1 for q in arena["questions"] if q["type"] == Q_MCQ),
        "mcq_correct": 0,
        "voice_count": 0,
        "code_count": 0,
    }
    context.user_data.pop("state", None)
    await show_arena_question(query.message, context)


async def handle_arena_answer(query, context, data: str, user) -> None:
    known = recognize(user.id)
    att = attempt_state(context)
    if not att and known:
        att = restore_attempt(context, known["id"])
    if not att:
        await query.answer("Urinish topilmadi. /start dan qayta boshlang.", show_alert=True)
        return
    arena = db_arenas.get_arena(att["arena_id"], with_questions=False)
    if arena is None:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    questions = db_arenas.list_arena_questions(arena["id"])
    q = questions[att["index"]] if att["index"] < len(questions) else None
    if not q or q["type"] != Q_MCQ:
        await query.answer("Bu savol variantli javobga ega emas.", show_alert=True)
        return

    chosen = int(data.split(":", 1)[1])
    correct_index = q.get("answer")
    if chosen == correct_index:
        att["mcq_correct"] += 1
    # Foydalanuvchiga javob to'g'ri/noto'g'ri ekani AYTILMAYDI
    await query.answer("✅ Javob qabul qilindi")
    context.user_data.pop("state", None)
    persist_attempt(context)
    await advance_arena(query.message, context, user)


# --- Ovozli xabar / fayl qabul qilish (arena javoblari) ---

async def voice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    known = recognize(user.id)
    if known:
        restore_attempt(context, known["id"])
    state = context.user_data.get("state")
    att = attempt_state(context)
    if state == "awaiting_code":
        await update.message.reply_text(
            "💻 Bu savolga <b>.py fayl</b> kutiladi — ovozli xabar emas.\n"
            "Kodingizni fayl qilib shu yerga yuboring (masalan: solution.py).",
            parse_mode="HTML",
        )
        return
    if state != "awaiting_voice" or not att:
        return

    arena = db_arenas.get_arena(att["arena_id"], with_questions=False)
    if arena is None:
        return
    questions = db_arenas.list_arena_questions(arena["id"])
    q = questions[att["index"]]

    att["voice_count"] += 1
    caption = answer_caption(arena["title"], att["index"], q["id"], "🎤 Ovozli javob", known, user)
    await forward_answer_to_channel(context, update, caption)
    db_results.add_arena_submission(
        known["id"] if known else None, arena["id"], q["id"], "voice", update.message.voice.file_id
    )
    context.user_data.pop("state", None)
    await update.message.reply_text("✅ Ovozli javobingiz qabul qilindi va adminga yuborildi.")
    persist_attempt(context)
    await advance_arena(update.effective_message, context, user)


async def document_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    known = recognize(user.id)
    if known:
        restore_attempt(context, known["id"])
    state = context.user_data.get("state")
    att = attempt_state(context)
    if state == "awaiting_voice":
        await update.message.reply_text(
            "🎤 Bu savolga <b>ovozli xabar</b> kutiladi — fayl emas.\n"
            "Telegramda mikrofon tugmasini bosing va gaping.",
            parse_mode="HTML",
        )
        return
    if state != "awaiting_code" or not att:
        return

    arena = db_arenas.get_arena(att["arena_id"], with_questions=False)
    if arena is None:
        return
    questions = db_arenas.list_arena_questions(arena["id"])
    q = questions[att["index"]]

    doc = update.message.document
    fname = (doc.file_name or "").lower()
    if not fname.endswith(".py"):
        await update.message.reply_text(
            "❌ Iltimos, aynan <b>.py</b> fayl yuboring (masalan: solution.py).",
            parse_mode="HTML",
        )
        return

    att["code_count"] += 1
    caption = answer_caption(arena["title"], att["index"], q["id"], "💻 Kod (.py)", known, user)
    await forward_answer_to_channel(context, update, caption)
    db_results.add_arena_submission(
        known["id"] if known else None, arena["id"], q["id"], "code", doc.file_id
    )
    context.user_data.pop("state", None)
    await update.message.reply_text("✅ Kodingiz qabul qilindi va adminga yuborildi.")
    persist_attempt(context)
    await advance_arena(update.effective_message, context, user)
