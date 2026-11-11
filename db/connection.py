"""DB ulanish pooli va so'rovlar.

Neon (serverless) scale-to-zero bo'lgani uchun bir martalik ulanish ochib,
uni qayta-qayta ishlatamiz — har so'rovda yangi ulanish ochgan holda
"cold start" kechikishidan qochish uchun.
"""

import logging
from pathlib import Path

import psycopg2
import psycopg2.extras
import psycopg2.pool

from config import DATABASE_URL

logger = logging.getLogger(__name__)

_SCHEMA_PATH = Path(__file__).with_name("schema.sql")
_pool: psycopg2.pool.ThreadedConnectionPool | None = None


def get_pool() -> psycopg2.pool.ThreadedConnectionPool:
    global _pool
    if _pool is None or _pool.closed:
        if not DATABASE_URL:
            raise RuntimeError(
                "DATABASE_URL topilmadi! Environment variable sifatida "
                "DATABASE_URL ni o'rnating (masalan: postgresql://user:pass@host/db?sslmode=require)."
            )
        _pool = psycopg2.pool.ThreadedConnectionPool(1, 5, DATABASE_URL, connect_timeout=20)
    return _pool


def query(sql: str, params: tuple = (), *, fetch: str = "all"):
    """fetch: 'all' | 'one' | 'none'"""
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn:  # muvaffaqiyatda COMMIT, xatoda ROLLBACK
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(sql, params)
                if fetch == "all":
                    return [dict(row) for row in cur.fetchall()]
                if fetch == "one":
                    row = cur.fetchone()
                    return dict(row) if row else None
                return None
    finally:
        # Har doim poolga qaytarish — xatoda pool o'zi rollback qiladi
        try:
            pool.putconn(conn)
        except Exception:
            pass


def init_db() -> None:
    logger.info("DB sxemasi tekshirilmoqda...")
    schema = _SCHEMA_PATH.read_text(encoding="utf-8")
    pool = get_pool()
    conn = pool.getconn()
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(schema)
                cur.execute("ALTER TABLE arenas ALTER COLUMN active SET DEFAULT FALSE")
    finally:
        pool.putconn(conn)
    logger.info("DB tayyor.")


def close_pool() -> None:
    global _pool
    if _pool and not _pool.closed:
        _pool.closeall()
    _pool = None
