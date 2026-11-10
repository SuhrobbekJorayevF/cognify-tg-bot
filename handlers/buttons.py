"""Tugma bosishlarining yagona kirish nuqtasi."""

from telegram import Update
from telegram.ext import ContextTypes

from db import arenas as db_arenas
from handlers import admin_users, arena_admin, arena_user
from handlers.common import is_admin, recognize
from keyboards import CANCEL_KEYBOARD, REG_CONFIRM_KEYBOARD, main_keyboard

ADMIN_ONLY_PREFIXES = (
    "epick:", "efield:", "dpick:", "dyes:", "unbind:",
    "arena_view:", "arena_del:", "arena_delyes:", "arena_toggle:",
    "aq_add:", "aq_list:", "aq_del:", "aq_delitem:", "aq_delyes:",
    "qtype:", "oddopt:",
)
ADMIN_ONLY_EXACT = {
    "admin", "usersmenu", "list", "adduser", "edituser", "deluser",
    "arena_admin", "arena_new", "arena_admin_list",
}
PROTECTED_PREFIXES = ("astart:", "aans:")
PROTECTED_EXACT = {"menu", "arena_user"}


async def _show_main_menu(query, admin: bool) -> None:
    await query.edit_message_text("🏠 Bosh menyu:", reply_markup=main_keyboard(admin))


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = query.from_user
    data = query.data

    admin = is_admin(user)
    known = recognize(user.id)
    authed = bool(known) or admin

    # --- Arena davom etayotgan bo'lsa, navigatsiyani bloklaymiz ---
    if known and not admin:
        sess = db_arenas.get_session(known["id"])
        if sess:
            same_arena = data.startswith("astart:") and int(data.split(":", 1)[1]) == sess["arena_id"]
            nav = data in ("menu", "cancelop") or data.startswith("astart:")
            if nav and not same_arena:
                await query.answer(
                    "⚠️ Arena davom etmoqda — avval uni tugating!",
                    show_alert=True,
                )
                return

    admin_only = data in ADMIN_ONLY_EXACT or data.startswith(ADMIN_ONLY_PREFIXES)
    if admin_only and not admin:
        await query.answer("⛔ Faqat admin uchun!", show_alert=True)
        return

    if not admin_only:
        protected = data in PROTECTED_EXACT or data.startswith(PROTECTED_PREFIXES)
        if protected and not authed:
            await query.answer("Avval tasdiqlashdan o'ting: /start", show_alert=True)
            return

    # --- Ro'yxatdan o'tishni tasdiqlash ---
    if data == "reg":
        await query.answer()
        context.user_data.clear()
        context.user_data["state"] = "login_username"
        await query.edit_message_text(
            "🔐 <b>Ro'yxatdan o'tishni tasdiqlash</b>\n\nUsername (login) kiriting:",
            parse_mode="HTML",
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    # --- Umumiy ---
    if data == "menu":
        await query.answer()
        context.user_data.clear()
        await _show_main_menu(query, admin)
        return

    if data == "cancelop":
        await query.answer("Bekor qilindi.")
        context.user_data.clear()
        if authed:
            await _show_main_menu(query, admin)
        else:
            await query.edit_message_text("Bekor qilindi.", reply_markup=REG_CONFIRM_KEYBOARD)
        return

    # --- Admin panel / userlar ---
    if data == "admin":
        await admin_users.handle_admin(query, context)
        return
    if data == "usersmenu":
        await admin_users.handle_users_menu(query, context)
        return
    if data == "list":
        await admin_users.handle_list(query, context)
        return
    if data == "adduser":
        await admin_users.handle_adduser(query, context)
        return
    if data == "edituser":
        await admin_users.handle_edituser(query, context)
        return
    if data == "deluser":
        await admin_users.handle_deluser(query, context)
        return
    if data.startswith("epick:"):
        await admin_users.handle_epick(query, context, data)
        return
    if data.startswith("efield:"):
        await admin_users.handle_efield(query, context, data)
        return
    if data.startswith("unbind:"):
        await admin_users.handle_unbind(query, context, data)
        return
    if data.startswith("dpick:"):
        await admin_users.handle_dpick(query, context, data)
        return
    if data.startswith("dyes:"):
        await admin_users.handle_dyes(query, context, data)
        return

    # --- Coding Arena — admin ---
    if data == "arena_admin":
        await arena_admin.handle_arena_admin(query, context)
        return
    if data == "arena_new":
        await arena_admin.handle_arena_new(query, context)
        return
    if data == "arena_admin_list":
        await arena_admin.handle_arena_admin_list(query, context)
        return
    if data.startswith("arena_view:"):
        await arena_admin.handle_arena_view(query, context, data)
        return
    if data.startswith("arena_del:"):
        await arena_admin.handle_arena_del(query, context, data)
        return
    if data.startswith("arena_toggle:"):
        await arena_admin.handle_arena_toggle(query, context, data)
        return
    if data.startswith("arena_delyes:"):
        await arena_admin.handle_arena_delyes(query, context, data)
        return
    if data.startswith("aq_add:"):
        await arena_admin.handle_aq_add(query, context, data)
        return
    if data.startswith("qtype:"):
        await arena_admin.handle_qtype(query, context, data)
        return
    if data.startswith("oddopt:"):
        await arena_admin.handle_mcq_answer(query, context, data)
        return
    if data.startswith("aq_list:"):
        await arena_admin.handle_aq_list(query, context, data)
        return
    if data.startswith("aq_del:"):
        await arena_admin.handle_aq_del(query, context, data)
        return
    if data.startswith("aq_delitem:"):
        await arena_admin.handle_aq_delitem(query, context, data)
        return
    if data.startswith("aq_delyes:"):
        await arena_admin.handle_aq_delyes(query, context, data)
        return

    # --- Coding Arena — user ---
    if data == "arena_user":
        await arena_user.handle_arena_user(query, context, admin)
        return
    if data.startswith("astart:"):
        await arena_user.handle_arena_start(query, context, data)
        return
    if data.startswith("aans:"):
        await arena_user.handle_arena_answer(query, context, data, user)
        return

    await query.answer()
