"""Barcha inline klaviaturalar shu yerda."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from services.formatting import LETTERS, Q_TYPE_TITLES

REG_CONFIRM_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton("✅ Ro'yxatdan o'tishni tasdiqlash", callback_data="reg")]]
)

CANCEL_KEYBOARD = InlineKeyboardMarkup(
    [[InlineKeyboardButton("❌ Bekor qilish", callback_data="cancelop")]]
)

BACK_TO_ADMIN = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Admin panel", callback_data="admin")]]
)

BACK_TO_USERS = InlineKeyboardMarkup(
    [[InlineKeyboardButton("⬅️ Userlar boshqaruvi", callback_data="usersmenu")]]
)

ADMIN_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("🏟️ Coding Arena boshqaruvi", callback_data="arena_admin")],
        [InlineKeyboardButton("👥 Userlar boshqaruvi", callback_data="usersmenu")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")],
    ]
)

USERSMENU_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("👥 Userlar ro'yxati", callback_data="list")],
        [InlineKeyboardButton("➕ Yangi user qo'shish", callback_data="adduser")],
        [
            InlineKeyboardButton("✏️ Tahrirlash", callback_data="edituser"),
            InlineKeyboardButton("🗑 O'chirish", callback_data="deluser"),
        ],
        [InlineKeyboardButton("⬅️ Admin panel", callback_data="admin")],
    ]
)

ARENA_ADMIN_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("➕ Yangi arena yaratish", callback_data="arena_new")],
        [InlineKeyboardButton("📋 Mavjud arenalar", callback_data="arena_admin_list")],
        [InlineKeyboardButton("⬅️ Admin panel", callback_data="admin")],
    ]
)

QTYPE_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("🔤 Savol-javob (A/B/C/D)", callback_data="qtype:mcq")],
        [InlineKeyboardButton("🎤 Ta'rifla (ovozli xabar)", callback_data="qtype:voice")],
        [InlineKeyboardButton("💻 Kod yozish (.py fayl)", callback_data="qtype:code")],
        [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancelop")],
    ]
)

ARENA_FINAL_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("🏟️ Arenaga qaytish", callback_data="arena_user")],
        [InlineKeyboardButton("🏠 Bosh menyu", callback_data="menu")],
    ]
)


def main_keyboard(admin: bool) -> InlineKeyboardMarkup:
    rows = []
    if admin:
        rows.append([InlineKeyboardButton("🔐 Admin panel", callback_data="admin")])
    rows.append([InlineKeyboardButton("🏟️ Kod Arenasi", callback_data="arena_user")])
    return InlineKeyboardMarkup(rows)


def arena_answer_keyboard(options: list[str]) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(f"{LETTERS[i]}) {opt}", callback_data=f"aans:{i}")]
        for i, opt in enumerate(options)
    ]
    return InlineKeyboardMarkup(buttons)


def user_pick_keyboard(users: list[dict], prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for u in sorted(users, key=lambda x: x["id"]):
        bound = "🔗" if u.get("bound_tg_id") else "⚪"
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{bound} #{u['id']} @{u['username']} — {u['full_name'][:22]}",
                    callback_data=f"{prefix}:{u['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️ Userlar boshqaruvi", callback_data="usersmenu")])
    return InlineKeyboardMarkup(buttons)


def arena_pick_keyboard(arenas: list[dict], prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for a in arenas:
        qcount = a.get("question_count", 0)
        mark = "🔓" if a.get("active") else "🔒"
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{mark} #{a['id']} — {a['title'][:32]} ({qcount} savol)",
                    callback_data=f"{prefix}:{a['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data="arena_admin")])
    return InlineKeyboardMarkup(buttons)


def question_pick_keyboard(arena: dict, prefix: str) -> InlineKeyboardMarkup:
    buttons = []
    for i, q in enumerate(arena["questions"]):
        buttons.append(
            [
                InlineKeyboardButton(
                    f"#{i + 1} ({Q_TYPE_TITLES.get(q['type'], q['type'])}) — {q['text'][:35]}",
                    callback_data=f"{prefix}:{arena['id']}:{q['id']}",
                )
            ]
        )
    buttons.append([InlineKeyboardButton("⬅️ Orqaga", callback_data=f"arena_view:{arena['id']}")])
    return InlineKeyboardMarkup(buttons)


def arena_manage_keyboard(arena_id: int, active: bool = True) -> InlineKeyboardMarkup:
    toggle_text = "🔓 Ochiq — yopish uchun bosing" if active else "🔒 Yopiq — ochish uchun bosing"
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton(toggle_text, callback_data=f"arena_toggle:{arena_id}")],
            [InlineKeyboardButton("➕ Savol qo'shish", callback_data=f"aq_add:{arena_id}")],
            [
                InlineKeyboardButton("📄 Savollar", callback_data=f"aq_list:{arena_id}"),
                InlineKeyboardButton("🗑 Savol o'chirish", callback_data=f"aq_del:{arena_id}"),
            ],
            [InlineKeyboardButton("🗑 Arenani o'chirish", callback_data=f"arena_del:{arena_id}")],
            [InlineKeyboardButton("⬅️ Arenalar", callback_data="arena_admin_list")],
        ]
    )


def edit_field_keyboard(uid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Ism", callback_data=f"efield:{uid}:name"),
                InlineKeyboardButton("✏️ Login", callback_data=f"efield:{uid}:username"),
                InlineKeyboardButton("✏️ Parol", callback_data=f"efield:{uid}:password"),
            ],
            [InlineKeyboardButton("🔓 Bog'lashni tiklash", callback_data=f"unbind:{uid}")],
            [InlineKeyboardButton("⬅️ Userlar boshqaruvi", callback_data="usersmenu")],
        ]
    )
