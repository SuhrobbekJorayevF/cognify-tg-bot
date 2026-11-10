"""Hammasi bu yerda ro'yxatdan o'tkaziladi."""

from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters

from handlers import arena_user, start, text
from handlers.buttons import button_handler


def register_handlers(application: Application) -> None:
    application.add_handler(CommandHandler("start", start.start))
    application.add_handler(CommandHandler("help", start.help_command))
    application.add_handler(CommandHandler("cancel", start.cancel))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.VOICE, arena_user.voice_handler))
    application.add_handler(MessageHandler(filters.Document.ALL, arena_user.document_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text.text_handler))
