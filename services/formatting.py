"""Xabar matnlari va formatlash yordamchilari."""

import html

from config import now_str  # noqa: F401  (qayta eksport qilinadi)

LETTERS = ["A", "B", "C", "D"]
Q_MCQ = "mcq"
Q_VOICE = "voice"
Q_CODE = "code"
Q_TYPE_TITLES = {
    Q_MCQ: "🔤 Savol-javob",
    Q_VOICE: "🎤 Ta'rifla (ovozli)",
    Q_CODE: "💻 Kod yozish (.py)",
}


def esc(s) -> str:
    return html.escape(str(s), quote=False)


def channel_record_text(user: dict, event: str) -> str:
    updated = user.get("updated") or user.get("created", "-")
    bound_id = user.get("bound_tg_id")
    if bound_id:
        tg_un = f" (@{esc(user['tg_username'])})" if user.get("tg_username") else ""
        bound_line = f"🔗 Telegram: <code>{bound_id}</code>{tg_un}\n"
        bound_line += f"📅 Bog'langan: {esc(user.get('bound_at') or '—')}\n"
    else:
        bound_line = "🔗 Telegram: hali bog'lanmagan\n"
    status = "🗑 O'chirilgan" if user.get("deleted") else "✅ Faol"
    return (
        f"{event} #{user['id']}\n\n"
        f"👤 Ism: {esc(user['full_name'])}\n"
        f"🔐 Login: @{esc(user['username'])}\n"
        f"🔑 Parol (sha256): <code>{user['password_hash']}</code>\n"
        f"🆔 User ID: {user['id']}\n"
        f"📅 Ro'yxatga olingan: {esc(user['created'])}\n"
        f"✏️ Oxirgi yangilanish: {esc(updated)}\n"
        f"{bound_line}"
        f"📌 Holat: {status}"
    )


def user_detail_text(user: dict) -> str:
    bound_id = user.get("bound_tg_id")
    if bound_id:
        tg_un = f" (@{esc(user['tg_username'])})" if user.get("tg_username") else ""
        bound_line = f"🔗 Telegram: <code>{bound_id}</code>{tg_un}\n"
        bound_line += f"📅 Bog'langan: {esc(user.get('bound_at') or '—')}\n"
    else:
        bound_line = "🔗 Telegram: <b>hali bog'lanmagan</b>\n"
    return (
        f"👤 <b>#{user['id']} — {esc(user['full_name'])}</b>\n\n"
        f"🔐 Login: @{esc(user['username'])}\n"
        f"🔑 Parol: •••••• (sha256 saqlangan)\n"
        f"📅 Ro'yxatga olingan: {esc(user['created'])}\n"
        f"✏️ Oxirgi yangilanish: {esc(user.get('updated') or '—')}\n"
        f"{bound_line}"
    )


def users_list_text(users: list[dict]) -> str:
    if not users:
        return "👥 Hozircha userlar yo'q. «➕ Yangi user qo'shish» tugmasi orqali qo'shing."
    lines = [f"👥 <b>Userlar ro'yxati</b> (jami: {len(users)})\n"]
    for u in users:
        mark = "🔗" if u.get("bound_tg_id") else "⚪"
        lines.append(
            f"{mark} #{u['id']} @{esc(u['username'])} — {esc(u['full_name'])} "
            f"({esc(u['created'][:10])})"
        )
    lines.append("\n🔗 — Telegram'ga bog'langan, ⚪ — hali tasdiqlanmagan")
    return "\n".join(lines)


def arena_summary_text(arena: dict) -> str:
    qcount = arena.get("question_count", len(arena.get("questions", [])))
    active = arena.get("active", False)
    status = "🔓 Ochiq" if active else "🔒 Yopiq"
    return (
        f"🏟 <b>Arena #{arena['id']}: {esc(arena['title'])}</b>\n\n"
        f"📝 {esc(arena.get('description') or '—')}\n"
        f"❓ Savollar soni: {qcount}\n"
        f"📌 Holat: {status}\n"
        f"📅 Yaratilgan: {esc(arena['created'])}"
    )


def arena_card_text(arena: dict) -> str:
    questions = arena.get("questions", [])
    return "\n".join(
        [
            f"🏟 <b>CODING ARENA #{arena['id']}: {esc(arena['title'])}</b>",
            "",
            f"📝 Tavsif: {esc(arena.get('description') or '—')}",
            f"❓ Savollar soni: {len(questions)}",
            f"📅 Yaratilgan: {esc(arena['created'])}",
            f"📌 Holat: {'🔓 Ochiq' if arena.get('active', False) else '🔒 Yopiq'}",
            "",
            "Savollar alohida kartalarda (har birida to'g'ri javob bilan) 👇",
        ]
    )


def question_card_text(arena: dict, q: dict, index: int) -> str:
    head = f"{Q_TYPE_TITLES.get(q['type'], q['type'])} — SAVOL #{index + 1}\n"
    head += f"🏟 Arena #{arena['id']}: {esc(arena['title'])}\n\n"
    body = f"❓ {esc(q['text'])}\n"
    if q["type"] == Q_MCQ:
        for i, opt in enumerate(q.get("options") or []):
            body += f"{LETTERS[i]}) {esc(opt)}\n"
        answer = q.get("answer")
        body += f"\n✅ To'g'ri javob: {LETTERS[answer] if answer is not None else '?'}"
    elif q["type"] == Q_VOICE:
        body += "\n🎤 Javob: ovozli xabar (admin eshitib tekshiradi)"
    elif q["type"] == Q_CODE:
        body += "\n💻 Javob: .py fayl (admin tekshiradi)"
    return head + body


def answer_caption(arena_title: str, q_index: int, q_id: int, kind: str, known: dict | None, user) -> str:
    login = f"@{known['username']}" if known else "?"
    full_name = " ".join(
        part for part in [user.first_name, user.last_name] if part
    ) or "Noma'lum"
    return (
        f"{kind} | 🏟 {arena_title[:40]} | ❓ Savol #{q_index + 1} (id {q_id})\n"
        f"👤 {full_name} | 🔐 {login} | 🆔 {user.id}\n"
        f"🕐 {now_str()}"
    )
