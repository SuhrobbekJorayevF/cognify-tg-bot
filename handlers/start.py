"""/start, /help, /cancel — kirish nuqtalari."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes

from db import arenas as db_arenas
from keyboards import REG_CONFIRM_KEYBOARD, main_keyboard
from handlers.common import is_admin, recognize
from services.formatting import esc
from texts import HELP_TEXT, WELCOME_GUEST


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.clear()
    user = update.effective_user
    known = recognize(user.id)

    if known:
        sess = None
        if not is_admin(user):
            sess = db_arenas.get_session(known["id"])
        if sess:
            arena = db_arenas.get_arena(sess["arena_id"], with_questions=False)
            title = esc(arena["title"]) if arena else "?"
            await update.message.reply_text(
                f"🏟 Arena davom etmoqda: <b>{title}</b>\n\nDavom eting:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("▶️ Davom etish", callback_data=f"astart:{sess['arena_id']}")]]
                ),
            )
            return
        await update.message.reply_text(
            f"👋 Xush kelibsiz, {esc(known['full_name'])}!\n"
            "Siz Telegram ID orqali avtomatik tanildingiz.",
            parse_mode="HTML",
            reply_markup=main_keyboard(is_admin(user)),
        )
        return

    if is_admin(user):
        await update.message.reply_text(
            "👋 Xush kelibsiz, admin!", reply_markup=main_keyboard(True)
        )
        return

    await update.message.reply_text(WELCOME_GUEST, reply_markup=REG_CONFIRM_KEYBOARD)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(HELP_TEXT)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    known = recognize(user.id)
    if known and not is_admin(user) and db_arenas.get_session(known["id"]):
        await update.message.reply_text(
            "⚠️ Arena davom etmoqda — bekor qilib bo'lmaydi.\n"
            "/start orqali davom eting va oxirigacha tugating."
        )
        return
    context.user_data.clear()
    if known or is_admin(user):
        await update.message.reply_text(
            "Bekor qilindi.", reply_markup=main_keyboard(is_admin(user))
        )
    else:
        await update.message.reply_text("Bekor qilindi.", reply_markup=REG_CONFIRM_KEYBOARD)
