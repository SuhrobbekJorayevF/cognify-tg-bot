import os
from datetime import datetime, timedelta, timezone

# --- Asosiy sozlamalar (Render'da barchasini Environment'ga qo'ying) ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")  # masalan: -1001234567890
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()  # sizning Telegram ID ingiz
DATABASE_URL = os.getenv("DATABASE_URL")  # postgresql://user:pass@... (Neon)
PORT = int(os.getenv("PORT", "10000"))  # Render o'zi PORT beradi

TASHKENT_TZ = timezone(timedelta(hours=5))  # UTC+5


def now_str() -> str:
    return datetime.now(TASHKENT_TZ).strftime("%d.%m.%Y %H:%M:%S")
