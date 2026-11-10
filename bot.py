"""Cognify Telegram Bot — kirish nuqtasi.

Sozlamalar: config.py (env)
DB: db/ (schema.sql, connection.py, users.py, arenas.py, questions.py, results.py)
Handlerlar: handlers/
"""

import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from telegram import BotCommand
from telegram.ext import ApplicationBuilder

from config import ADMIN_ID, BOT_TOKEN, CHANNEL_ID, DATABASE_URL, PORT
from db import init_db
from handlers import register_handlers

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def run_health_server() -> None:
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write("Bot ishlayapti!".encode("utf-8"))

        def log_message(self, format, *args) -> None:  # noqa: A002
            pass

    server = HTTPServer(("0.0.0.0", PORT), Handler)
    logger.info("Health check server %s-portda ishga tushdi", PORT)
    server.serve_forever()


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN topilmadi! Environment variable sifatida o'rnating.")
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL topilmadi! Environment variable sifatida o'rnating "
            "(masalan: postgresql://user:pass@host/db?sslmode=require)."
        )
    if not CHANNEL_ID:
        logger.warning("CHANNEL_ID o'rnatilmagan — kanal sinxronlash ishlamaydi.")
    if not ADMIN_ID:
        logger.warning("ADMIN_ID o'rnatilmagan — admin panel hech kimga ko'rinmaydi!")

    init_db()

    threading.Thread(target=run_health_server, daemon=True).start()

    async def post_init(application) -> None:
        # "/" menyusida komandalar ko'rinadi — /start birinchi chiqadi
        await application.bot.set_my_commands(
            [
                BotCommand("start", "Botni ishga tushirish"),
                BotCommand("help", "Yordam"),
                BotCommand("cancel", "Bekor qilish"),
            ]
        )
        # Bot tavsifi — "What can this bot do?" bloki
        try:
            await application.bot.set_my_description(
                "🤖 Cognify Coding Arena — Python bo'yicha online musobaqalar uchun rasmiy bot!\n\n"
                "🏟️ KOD ARENA'da ishtirok eting:\n"
                "🔤 A/B/C/D savollari\n"
                "🎤 Ta'riflash savollari — ovozli xabar orqali\n"
                "💻 Amaliy mashqlar — .py fayl yuborish\n\n"
                "/start bosing — ro'yxatdan o'ting va musobaqada qatnashing! 🏆"
            )
            await application.bot.set_my_short_description(
                "Python bo'yicha online musobaqa! /start bosing va KOD ARENA'da qatnashing. 🏆"
            )
            logger.info("Bot tavsifi o'rnatildi")
        except Exception:
            logger.exception("Bot tavsifini o'rnatishda xatolik (davom etayapti)")

    application = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()
    register_handlers(application)

    logger.info("Bot polling rejimida ishga tushdi...")
    application.run_polling()


if __name__ == "__main__":
    main()
