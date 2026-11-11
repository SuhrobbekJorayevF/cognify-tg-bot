"""Admin panel — FOYDALANUVCHILARNI boshqarish."""

import hashlib

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from db import users as db_users
from keyboards import (
    ADMIN_KEYBOARD,
    BACK_TO_USERS,
    CANCEL_KEYBOARD,
    USERSMENU_KEYBOARD,
    edit_field_keyboard,
    user_pick_keyboard,
)
from services import channel as channel_service
from services.channel import CHANNEL_STATUS
from services.formatting import esc, user_detail_text, users_list_text

LETTERS_ALL = ["A", "B", "C", "D"]


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def handle_users_menu(query, context) -> None:
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(
        "👥 <b>Userlar boshqaruvi</b>\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=USERSMENU_KEYBOARD,
    )


async def handle_admin(query, context) -> None:
    await query.answer()
    context.user_data.clear()
    ok = CHANNEL_STATUS.get("ok")
    if ok is True:
        channel_line = f"📡 Kanal: ✅ ulangan ({esc(CHANNEL_STATUS.get('detail', 'OK'))})"
    elif ok is False:
        channel_line = f"📡 Kanal: ❌ {esc(CHANNEL_STATUS.get('detail', 'xato'))}\n(hech qanday karta/natija yuborilmayapti!)"
    else:
        channel_line = "📡 Kanal: ⏳ tekshirilmagan"
    await query.edit_message_text(
        f"🔐 <b>Admin panel</b>\n\n{channel_line}\n\nKerakli amalni tanlang:",
        parse_mode="HTML",
        reply_markup=ADMIN_KEYBOARD,
    )


async def handle_list(query, context) -> None:
    await query.answer()
    users = db_users.list_users()
    await query.edit_message_text(
        users_list_text(users), parse_mode="HTML", reply_markup=BACK_TO_USERS
    )


async def handle_adduser(query, context) -> None:
    await query.answer()
    context.user_data.clear()
    context.user_data["state"] = "add_full_name"
    await query.edit_message_text(
        "➕ <b>Yangi user</b>\n\n1/3 — Ism familiyani kiriting:",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_edituser(query, context) -> None:
    await query.answer()
    users = db_users.list_users()
    if not users:
        await query.edit_message_text(
            "Tahrirlash uchun hali user yo'q.", reply_markup=BACK_TO_USERS
        )
        return
    await query.edit_message_text(
        "✏️ Qaysi userni tahrirlaysiz?\n🔗 — bog'langan, ⚪ — hali emas",
        reply_markup=user_pick_keyboard(users, "epick"),
    )


async def handle_deluser(query, context) -> None:
    await query.answer()
    users = db_users.list_users()
    if not users:
        await query.edit_message_text(
            "O'chirish uchun hali user yo'q.", reply_markup=BACK_TO_USERS
        )
        return
    await query.edit_message_text(
        "🗑 Qaysi userni o'chirasiz?",
        reply_markup=user_pick_keyboard(users, "dpick"),
    )


async def handle_epick(query, context, data: str) -> None:
    uid = int(data.split(":", 1)[1])
    target = db_users.get_by_id(uid)
    if not target or target.get("deleted"):
        await query.answer("User topilmadi.", show_alert=True)
        return
    await query.answer()
    await query.edit_message_text(
        user_detail_text(target) + "\nNimani o'zgartiramiz?",
        parse_mode="HTML",
        reply_markup=edit_field_keyboard(uid),
    )


async def handle_efield(query, context, data: str) -> None:
    _, uid_s, field = data.split(":")
    uid = int(uid_s)
    target = db_users.get_by_id(uid)
    if not target or target.get("deleted"):
        await query.answer("User topilmadi.", show_alert=True)
        return
    field_names = {
        "name": "yangi ism familiyani",
        "username": "yangi login (username)ni",
        "password": "yangi parolni",
    }
    await query.answer()
    context.user_data.clear()
    context.user_data["state"] = "edit_value"
    context.user_data["edit"] = {"uid": uid, "field": field}
    await query.edit_message_text(
        f"✏️ #{uid} @{esc(target['username'])} uchun {field_names[field]} kiriting:",
        parse_mode="HTML",
        reply_markup=CANCEL_KEYBOARD,
    )


async def handle_unbind(query, context, data: str) -> None:
    uid = int(data.split(":", 1)[1])
    target = db_users.get_by_id(uid)
    if not target or target.get("deleted"):
        await query.answer("User topilmadi.", show_alert=True)
        return
    if not target.get("bound_tg_id"):
        await query.answer("Bu user hali hech kimga bog'lanmagan.", show_alert=True)
        return
    target = db_users.reset_binding(uid)
    msg_id = await channel_service.sync_user_card(
        context.bot, target, is_new=False, event="🔓 BOG'LASH TIKLANDI"
    )
    if msg_id:
        db_users.update_user(uid, msg_id=msg_id)
    await query.answer("🔓 Bog'lash tiklandi.", show_alert=True)
    await query.edit_message_text(
        user_detail_text(db_users.get_by_id(uid)),
        parse_mode="HTML",
        reply_markup=BACK_TO_USERS,
    )


async def handle_dpick(query, context, data: str) -> None:
    uid = int(data.split(":", 1)[1])
    target = db_users.get_by_id(uid)
    if not target or target.get("deleted"):
        await query.answer("User topilmadi.", show_alert=True)
        return
    await query.answer()
    del_kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🗑 Ha, o'chirilsin", callback_data=f"dyes:{uid}")],
            [InlineKeyboardButton("⬅️ Userlar boshqaruvi", callback_data="usersmenu")],
        ]
    )
    await query.edit_message_text(
        user_detail_text(target) + "\n⚠️ Rostdan o'chirilsinmi?",
        parse_mode="HTML",
        reply_markup=del_kb,
    )


async def handle_dyes(query, context, data: str) -> None:
    uid = int(data.split(":", 1)[1])
    target = db_users.get_by_id(uid)
    if not target:
        await query.answer("User topilmadi.", show_alert=True)
        return
    await channel_service.delete_message(context.bot, target.get("msg_id"))
    db_users.delete_user(uid)
    await query.answer("O'chirildi.")
    await query.edit_message_text(
        f"🗑 #{uid} @{esc(target['username'])} o'chirildi.",
        parse_mode="HTML",
        reply_markup=BACK_TO_USERS,
    )
