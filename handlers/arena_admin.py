"""Coding Arena — ADMIN tomoni (arena/savol yaratish va boshqarish)."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import arenas as db_arenas
from db import questions as db_questions
from keyboards import (
    ARENA_ADMIN_KEYBOARD,
    CANCEL_KEYBOARD,
    QTYPE_KEYBOARD,
    arena_manage_keyboard,
    arena_pick_keyboard,
    question_pick_keyboard,
)
from services import channel as channel_service
from services.formatting import Q_MCQ, esc, now_str


async def show_arena_list_edit(query, arena_id: int | None = None, arena: dict | None = None, reply_markup=None) -> None:
    if arena is None:
        arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.edit_message_text("Arena topilmadi.", reply_markup=ARENA_ADMIN_KEYBOARD)
        return
    arena_id = arena["id"]
    view = {
        "id": arena["id"],
        "title": arena["title"],
        "description": arena.get("description", ""),
        "created": arena["created"],
        "question_count": len(arena.get("questions", [])),
        "active": arena.get("active", False),
    }
    from services.formatting import arena_summary_text

    await query.edit_message_text(
        arena_summary_text(view),
        parse_mode="HTML",
        reply_markup=reply_markup or arena_manage_keyboard(arena_id, arena.get("active", False)),
    )


async def handle_arena_admin(query, context) -> None:
    await query.answer()
    context.user_data.clear()
    arenas = db_arenas.list_arenas()
    await query.edit_message_text(
        "🏟️ <b>Coding Arena boshqaruvi</b>\n\n"
        f"Mavjud arenalar: {len(arenas)} ta\n\n"
        "Yangi arena yarating yoki mavjudini boshqaring.\n"
        "⚠️ Arena va savollari to'liq kanalga saqlanadi (savol-javoblari bilan).",
        parse_mode="HTML",
        reply_markup=ARENA_ADMIN_KEYBOARD,
    )


async def handle_arena_new(query, context) -> None:
    await query.answer()
    context.user_data.clear()
    context.user_data["state"] = "arena_title"
    await query.edit_message_text(
        "🏟 <b>Yangi arena</b>\n\nArena nomini kiriting (masalan: «Python Season 1»):",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_arena_admin_list(query, context) -> None:
    await query.answer()
    arenas = db_arenas.list_arenas()
    if not arenas:
        await query.edit_message_text(
            "Hali arena yo'q. «➕ Yangi arena yaratish» ni bosing.",
            reply_markup=ARENA_ADMIN_KEYBOARD,
        )
        return
    await query.edit_message_text(
        "📋 <b>Mavjud arenalar</b> — boshqarish uchun tanlang:",
        parse_mode="HTML",
        reply_markup=arena_pick_keyboard(arenas, "arena_view"),
    )


async def handle_arena_view(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    await query.answer()
    await show_arena_list_edit(query, arena_id)


async def handle_arena_del(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    await query.answer()
    del_kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑 Ha, o'chirilsin (kanaldan ham)", callback_data=f"arena_delyes:{arena_id}")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"arena_view:{arena_id}")],
        ]
    )
    from services.formatting import arena_summary_text

    await query.edit_message_text(
        arena_summary_text(arena)
        + f"\n\n⚠️ Arena va undagi {len(arena['questions'])} ta savol kanaldan ham o'chiriladi. Davom etasizmi?",
        parse_mode="HTML",
        reply_markup=del_kb,
    )


async def handle_arena_delyes(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena allaqachon o'chirilgan.", show_alert=True)
        return
    for q in arena["questions"]:
        await channel_service.delete_message(context.bot, q.get("msg_id"))
    await channel_service.delete_message(context.bot, arena.get("msg_id"))
    db_arenas.delete_arena(arena_id)
    await query.answer("🗑 Arena o'chirildi.")
    await query.edit_message_text(
        f"🗑 Arena #{arena_id} «{esc(arena['title'])}» va savollari kanaldan o'chirildi.",
        parse_mode="HTML",
        reply_markup=ARENA_ADMIN_KEYBOARD,
    )


async def handle_arena_toggle(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)  # savollar bilan yuklanadi (bir marta)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    new_state = not arena.get("active", False)
    updated = db_arenas.set_active(arena_id, new_state)
    fresh = dict(arena, active=new_state, updated=updated.get("updated", arena.get("updated")))
    event = "🔓 ARENA OCHILDI" if new_state else "🔒 ARENA YOPILDI"

    msg_id = await channel_service.sync_arena_card(context.bot, fresh)
    if msg_id and msg_id != fresh.get("msg_id"):
        db_arenas.update_arena(arena_id, msg_id=msg_id)
    # Ochilish/yopilish audit yozuvi kanalga
    await channel_service.send_text(
        context.bot, f"{event}\n🏟 #{fresh['id']} — {esc(fresh['title'])}\n🕐 {now_str()}"
    )
    await query.answer("🔓 Arena ochildi" if new_state else "🔒 Arena yopildi")
    await show_arena_list_edit(query, arena=fresh)


async def handle_aq_add(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id, with_questions=False)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    await query.answer()
    context.user_data.clear()
    context.user_data["state"] = "q_type"
    context.user_data["pending_arena"] = arena_id
    await query.edit_message_text(
        f"➕ <b>Arena «{esc(arena['title'])}» ga yangi savol</b>\n\nSavol turini tanlang:",
        parse_mode="HTML",
        reply_markup=QTYPE_KEYBOARD,
    )


async def handle_qtype(query, context, data: str) -> None:
    qtype = data.split(":", 1)[1]
    if qtype not in ("mcq", "voice", "code"):
        await query.answer("Noma'lum tur.", show_alert=True)
        return
    arena_id = context.user_data.get("pending_arena")
    if not arena_id:
        await query.answer("Xatolik — bekor qilib qayta urining.", show_alert=True)
        return
    await query.answer()
    context.user_data["pending_q"] = {"type": qtype}
    context.user_data["state"] = "q_text"
    labels = {"mcq": "🔤 Savol-javob", "voice": "🎤 Ta'rifla (ovozli)", "code": "💻 Kod yozish (.py)"}
    await query.edit_message_text(
        f"{labels[qtype]}\n\n❓ Savol matnini kiriting:",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_mcq_answer(query, context, data: str) -> None:
    answer = int(data.split(":", 1)[1])
    pending = context.user_data.get("pending_q")
    arena_id = context.user_data.get("pending_arena")
    if not pending or pending.get("type") != Q_MCQ or not arena_id:
        await query.answer("Xatolik — bekor qilib qayta urining.", show_alert=True)
        return
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return

    question = db_questions.add_question(
        arena_id, Q_MCQ, pending["text"], pending["options"], answer
    )
    index = len(arena["questions"])
    msg_id = await channel_service.post_question_card(context.bot, arena, question, index)
    if msg_id:
        db_questions.set_question_msg_id(question["id"], msg_id)
    fresh = db_arenas.get_arena(arena_id)
    msg_id_arena = await channel_service.sync_arena_card(context.bot, fresh)
    if msg_id_arena:
        db_arenas.update_arena(arena_id, msg_id=msg_id_arena)
    context.user_data.clear()
    await query.answer("✅ Savol qo'shildi!")
    from services.formatting import LETTERS

    await query.edit_message_text(
        f"✅ Savol #{index + 1} qo'shildi va kanalga saqlandi!\n\n"
        f"🔤 {esc(question['text'][:200])}\n"
        f"✅ To'g'ri javob: {LETTERS[answer]}) {esc(question['options'][answer])}",
        parse_mode="HTML",
        reply_markup=arena_manage_keyboard(arena_id, arena.get("active", False)),
    )


async def handle_aq_list(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena:
        await query.answer("Arena topilmadi.", show_alert=True)
        return
    await query.answer()
    if not arena["questions"]:
        text = f"🏟 {esc(arena['title'])}\n\nHali savollar yo'q. «➕ Savol qo'shish» ni bosing."
    else:
        from services.formatting import Q_TYPE_TITLES

        lines = [f"📄 <b>Savollar</b> — Arena #{arena['id']} {esc(arena['title'])}\n"]
        for i, q in enumerate(arena["questions"]):
            t = Q_TYPE_TITLES.get(q["type"], q["type"])
            lines.append(f"{i + 1}. [{t}] {esc(q['text'][:80])}")
        text = "\n".join(lines)
    await query.edit_message_text(
        text, parse_mode="HTML", reply_markup=arena_manage_keyboard(arena_id, arena.get("active", False))
    )


async def handle_aq_del(query, context, data: str) -> None:
    arena_id = int(data.split(":", 1)[1])
    arena = db_arenas.get_arena(arena_id)
    if not arena or not arena["questions"]:
        await query.answer("O'chirish uchun savol yo'q.", show_alert=True)
        return
    await query.answer()
    await query.edit_message_text(
        "🗑 Qaysi savolni o'chirasiz?",
        reply_markup=question_pick_keyboard(arena, "aq_delitem"),
    )


async def handle_aq_delitem(query, context, data: str) -> None:
    _, arena_id_s, qid_s = data.split(":")
    arena_id, qid = int(arena_id_s), int(qid_s)
    question = db_questions.get_question(qid)
    if not question or question["arena_id"] != arena_id:
        await query.answer("Savol topilmadi.", show_alert=True)
        return
    await query.answer()
    from services.formatting import Q_TYPE_TITLES

    del_kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑 Ha, o'chirilsin", callback_data=f"aq_delyes:{arena_id}:{qid}")],
            [InlineKeyboardButton("⬅️ Orqaga", callback_data=f"arena_view:{arena_id}")],
        ]
    )
    await query.edit_message_text(
        f"🗑 Savol o'chirilsinmi?\n\n{Q_TYPE_TITLES.get(question['type'], question['type'])}: "
        f"{esc(question['text'][:300])}",
        parse_mode="HTML",
        reply_markup=del_kb,
    )


async def handle_aq_delyes(query, context, data: str) -> None:
    _, arena_id_s, qid_s = data.split(":")
    arena_id, qid = int(arena_id_s), int(qid_s)
    question = db_questions.get_question(qid)
    if not question:
        await query.answer("Savol allaqachon o'chirilgan.", show_alert=True)
        return
    arena = db_arenas.get_arena(arena_id)
    await channel_service.delete_message(context.bot, question.get("msg_id"))
    db_questions.delete_question(qid)
    fresh = db_arenas.get_arena(arena_id)
    msg_id_arena = await channel_service.sync_arena_card(context.bot, fresh)
    if msg_id_arena:
        db_arenas.update_arena(arena_id, msg_id=msg_id_arena)
    await query.answer("🗑 Savol o'chirildi.")
    remaining = len(fresh["questions"]) if fresh else "?"
    await query.edit_message_text(
        f"🗑 Savol o'chirildi. Qolgan savollar: {remaining} ta",
        reply_markup=arena_manage_keyboard(arena_id, arena.get("active", False)),
    )
