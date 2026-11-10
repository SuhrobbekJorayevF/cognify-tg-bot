"""DB ulanishi va so'rovlar.

Neon (serverless Postgres) scale-to-zero bo'lgani uchun har bir so'rovda alohida ulanish ochamiz — 10–30 foydalanuvchi uchun bu arzimaydi va
uyg'onish (cold start) uchun ham chidamli.
"""

import logging
from pathlib import Path

import psycopg2
import psycopg2.extras

from config import DATABASE_URL

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")


def connect():
    if not DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL topilmadi! Environment variable sifatida "
            "DATABASE_URL ni o'rnating (masalan: postgresql://user:pass@host/db?sslmode=require)."
        )
    return psycopg2.connect(DATABASE_URL, connect_timeout=20)


def query(sql: str, params: tuple = (), *, fetch: str = "all"):
    """fetch: 'all' | 'one' | 'none'"""
    with connect() as conn:  # muvaffaqiyatda COMMIT, xatoda ROLLBACK
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            if fetch == "all":
                return [dict(row) for row in cur.fetchall()]
            if fetch == "one":
                row = cur.fetchone()
                return dict(row) if row else None
            return None


def init_db() -> None:
    logger.info("DB sxemasi tekshirilmoqda...")
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    with connect() as conn:
        with conn.cursor() as cur:
            cur.execute(schema)
            # Mavjud bazalarda default ni FALSE qilamiz (idempotent)
            cur.execute("ALTER TABLE arenas ALTER COLUMN active SET DEFAULT FALSE")
    logger.info("DB tayyor.")
