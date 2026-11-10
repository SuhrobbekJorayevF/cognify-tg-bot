-- Cognify Telegram Bot — DB sxemasi
-- Bot ishga tushganda avtomatik qo'llaniladi (CREATE ... IF NOT EXISTS)

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    full_name     TEXT NOT NULL,
    username      TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created       TEXT NOT NULL,
    updated       TEXT NOT NULL,
    msg_id        BIGINT,
    bound_tg_id   BIGINT UNIQUE,
    tg_username   TEXT,
    bound_at      TEXT,
    deleted       BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS arenas (
    id          SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL,
    msg_id      BIGINT,
    active      BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS questions (
    id       SERIAL PRIMARY KEY,
    arena_id INTEGER NOT NULL REFERENCES arenas(id) ON DELETE CASCADE,
    position INTEGER NOT NULL,
    type     TEXT NOT NULL CHECK (type IN ('mcq', 'voice', 'code')),
    text     TEXT NOT NULL,
    options  JSONB,
    answer   INTEGER,
    created  TEXT NOT NULL,
    msg_id   BIGINT
);

CREATE INDEX IF NOT EXISTS idx_questions_arena ON questions(arena_id);

CREATE TABLE IF NOT EXISTS test_results (
    id      SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
    kind    TEXT NOT NULL DEFAULT 'test',  -- 'test' | 'arena'
    ref     TEXT NOT NULL,                 -- test nomi yoki 'arena#<id>'
    correct INTEGER NOT NULL,
    total   INTEGER NOT NULL,
    percent INTEGER NOT NULL,
    created TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arena_submissions (
    id          SERIAL PRIMARY KEY,
    user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
    arena_id    INTEGER REFERENCES arenas(id) ON DELETE CASCADE,
    question_id INTEGER REFERENCES questions(id) ON DELETE CASCADE,
    kind        TEXT NOT NULL,             -- 'voice' | 'code'
    file_id     TEXT NOT NULL,
    created     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS arena_attempts (
    arena_id INTEGER NOT NULL REFERENCES arenas(id) ON DELETE CASCADE,
    user_id  INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created  TEXT NOT NULL,
    PRIMARY KEY (arena_id, user_id)
);

-- Userning tugallanmagan arena urinishi (bot restart'idan keyin ham davom etadi)
CREATE TABLE IF NOT EXISTS arena_sessions (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    arena_id    INTEGER NOT NULL REFERENCES arenas(id) ON DELETE CASCADE,
    q_index     INTEGER NOT NULL DEFAULT 0,
    mcq_total   INTEGER NOT NULL DEFAULT 0,
    mcq_correct INTEGER NOT NULL DEFAULT 0,
    voice_count INTEGER NOT NULL DEFAULT 0,
    code_count  INTEGER NOT NULL DEFAULT 0,
    awaiting    TEXT,  -- 'awaiting_voice' | 'awaiting_code' | NULL
    created     TEXT NOT NULL,
    updated     TEXT NOT NULL
);
