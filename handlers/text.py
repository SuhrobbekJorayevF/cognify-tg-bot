"""Matn xabarlarini qayta ishlash — login, admin wizardlari, arena yaratish."""

import hashlib

from telegram import Update
from telegram.ext import ContextTypes

from config import now_str
from db import arenas as db_arenas
from db import questions as db_questions
from db import users as db_users
from handlers.common import full_name_of, is_admin, recognize
from keyboards import (
    ADMIN_KEYBOARD,
    BACK_TO_USERS,
    CANCEL_KEYBOARD,
    REG_CONFIRM_KEYBOARD,
    arena_manage_keyboard,
    main_keyboard,
)
from services import channel as channel_service
from services.formatting import Q_CODE, Q_MCQ, Q_VOICE, esc, user_detail_text
from handlers.arena_user import restore_attempt
import re

USERNAME_RE = re.compile(r"^[a-z0-9_]{3,32}$")


def normalize_username(raw: str) -> str:
    return raw.strip().lower().lstrip("@")


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    text = (update.message.text or "").strip()
    state = context.user_data.get("state")
    known = recognize(user.id)
    admin = is_admin(user)

    # --- Arena davom etmoqda bo'lsa, bosilgan matnni himoyalaymiz ---
    if known and not admin:
        sess = db_arenas.get_session(known["id"])
        if sess:
            restore_attempt(context, known["id"])
            if context.user_data.get("state") in ("awaiting_voice", "awaiting_code"):
                await update.message.reply_text(
                    "⚠️ Bu savolga faqat "
                    + ("ovozli xabar" if context.user_data["state"] == "awaiting_voice" else ".py fayl")
                    + " kutiladi. Iltimos, shuni yuboring."
                )
                return
            # state yo'q — MCQ savoli ko'rsatilmoqda
            if context.user_data.get("attempt"):
                await update.message.reply_text(
                    "👆 Avval yuqoridagi tugmalardan javob tanlang.\n"
                    "/cancel ishlamaydi — arena davom etmoqda."
                )
                return

    # ============ TASDIQLASH ============
    if state == "login_username":
        if not text:
            await update.message.reply_text("Loginingizni kiriting:")
            return
        context.user_data["pending_username"] = normalize_username(text)
        context.user_data["state"] = "login_password"
        await update.message.reply_text("🔑 Parolni kiriting:", reply_markup=CANCEL_KEYBOARD)
        return

    if state == "login_password":
        try:
            await update.message.delete()
        except Exception:
            pass
        username = context.user_data.get("pending_username", "")
        target = db_users.get_by_username(username)
        if not target or target.get("deleted") or target["password_hash"] != hash_password(text):
            context.user_data.clear()
            context.user_data["state"] = "login_username"
            await update.message.reply_text(
                "❌ Login yoki parol noto'g'ri.\n\nQaytadan loginingizni kiriting:",
                reply_markup=CANCEL_KEYBOARD,
            )
            return

        bound = target.get("bound_tg_id")
        if bound is not None and bound != user.id:
            context.user_data.clear()
            await update.message.reply_text(
                "⛔ Bu hisob boshqa Telegram akkauntga bog'langan.\n"
                "Admin bilan bog'laning.",
                reply_markup=REG_CONFIRM_KEYBOARD,
            )
            return

        if bound is None:
            target = db_users.bind_user(target["id"], user.id, user.username)
            msg_id = await channel_service.sync_user_card(
                context.bot, target, is_new=False, event="🔗 TELEGRAM BIRIKTIRILDI"
            )
            if msg_id:
                db_users.update_user(target["id"], msg_id=msg_id)
            msg = "✅ Hisobingiz Telegram ID'ingizga bog'landi! Bundan keyin avtomatik tanilasiz."
        else:
            msg = "✅ Qaytib keldingiz!"

        context.user_data.clear()
        await update.message.reply_text(
            f"{msg}\n\n👤 {esc(target['full_name'])}",
            parse_mode="HTML",
            reply_markup=main_keyboard(admin),
        )
        return

    # ============ Ovozli/fayl kutilayotgan holatlar ============
    if state in ("awaiting_voice", "awaiting_code"):
        await update.message.reply_text(
            "⚠️ Bu savolga faqat " + ("ovozli xabar" if state == "awaiting_voice" else ".py fayl")
            + " kutiladi. Iltimos, shuni yuboring."
        )
        return

    # ============ ADMIN: arena yaratish ============
    if state == "arena_title":
        if not admin:
            context.user_data.clear()
            return
        if len(text) < 2:
            await update.message.reply_text("Nom juda qisqa. Qaytadan:")
            return
        context.user_data["new_arena"] = {"title": text}
        context.user_data["state"] = "arena_desc"
        await update.message.reply_text(
            "Arena haqida qisqa tavsif kiriting (ixtiyoriy — o'tkazish uchun «-» yuboring):",
            reply_markup=CANCEL_KEYBOARD,
        )
        return

    if state == "arena_desc":
        if not admin:
            context.user_data.clear()
            return
        title = context.user_data["new_arena"]["title"]
        description = "" if text == "-" else text
        arena = db_arenas.create_arena(title, description)
        msg_id = await channel_service.sync_arena_card(context.bot, arena)
        if msg_id:
            db_arenas.update_arena(arena["id"], msg_id=msg_id)
        context.user_data.clear()
        await update.message.reply_text(
            f"✅ <b>Arena yaratildi!</b>\n\n🏟 #{arena['id']} — {esc(arena['title'])}\n"
            f"📝 {esc(description or '—')}\n\n"
            "Endi ichiga savollar qo'shing, so'ngra ochiq qiling 🔓\n"
            "(hozircha arena <b>yopiq</b> — hech kim ko'ra olmaydi).",
            parse_mode="HTML",
            reply_markup=arena_manage_keyboard(arena["id"], arena.get("active", False)),
        )
        return

    # ============ ADMIN: savol yaratish wizard ============
    if state == "q_text":
        if not admin:
            context.user_data.clear()
            return
        if len(text) < 3:
            await update.message.reply_text("Savol matni juda qisqa. Qaytadan:")
            return
        pending = context.user_data.get("pending_q")
        arena_id = context.user_data.get("pending_arena")
        if not pending or not arena_id:
            context.user_data.clear()
            await update.message.reply_text("Xatolik — bekor qilib qayta urining.")
            return
        pending["text"] = text
        if pending["type"] == Q_MCQ:
            context.user_data["state"] = "q_opt_1"
            await update.message.reply_text(
                "Variant A ni kiriting:", reply_markup=CANCEL_KEYBOARD
            )
        else:
            arena = db_arenas.get_arena(arena_id)
            if not arena:
                context.user_data.clear()
                await update.message.reply_text("Arena topilmadi.")
                return
            question = db_questions.add_question(
                arena_id, pending["type"], text
            )
            index = len(arena["questions"])
            msg_id = await channel_service.post_question_card(context.bot, arena, question, index)
            if msg_id:
                db_questions.set_question_msg_id(question["id"], msg_id)
            fresh = db_arenas.get_arena(arena_id)
            msg_id_arena = await channel_service.sync_arena_card(context.bot, fresh)
            if msg_id_arena:
                db_arenas.update_arena(arena_id, msg_id=msg_id_arena)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ Savol #{index + 1} qo'shildi va kanalga saqlandi!",
                reply_markup=arena_manage_keyboard(arena_id, fresh.get("active", False)),
            )
        return

    if state in ("q_opt_1", "q_opt_2", "q_opt_3", "q_opt_4"):
        if not admin:
            context.user_data.clear()
            return
        pending = context.user_data.get("pending_q")
        if not pending:
            context.user_data.clear()
            await update.message.reply_text("Xatolik — bekor qilib qayta urining.")
            return
        pending.setdefault("options", []).append(text)
        step = int(state[-1])
        letters = ["A", "B", "C", "D"]
        if step < 4:
            context.user_data["state"] = f"q_opt_{step + 1}"
            await update.message.reply_text(
                f"Variant {letters[step]} ni kiriting:", reply_markup=CANCEL_KEYBOARD
            )
        else:
            context.user_data["state"] = "q_answer"
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup

            kb = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton(f"{letters[i]}", callback_data=f"oddopt:{i}") for i in range(4)],
                    [InlineKeyboardButton("❌ Bekor qilish", callback_data="cancelop")],
                ]
            )
            opts = "\n".join(
                f"{letters[i]}) {esc(o)}" for i, o in enumerate(pending["options"])
            )
            await update.message.reply_text(
                f"Variantlar:\n{opts}\n\n✅ To'g'ri javobni tanlang:",
                parse_mode="HTML",
                reply_markup=kb,
            )
        return

    # ============ ADMIN: user qo'shish/tahrirlash ============
    if state in ("add_full_name", "add_username", "add_password", "edit_value"):
        if not admin:
            context.user_data.clear()
            await update.message.reply_text("⛔ Faqat admin uchun!")
            return

        if state == "add_full_name":
            if len(text) < 2:
                await update.message.reply_text("Ism juda qisqa. Qaytadan kiriting:")
                return
            context.user_data["new_user"] = {"full_name": text}
            context.user_data["state"] = "add_username"
            await update.message.reply_text(
                "2/3 — Login kiriting (masalan: ali_uz):",
                reply_markup=CANCEL_KEYBOARD,
            )
            return

        if state == "add_username":
            username = normalize_username(text)
            if not USERNAME_RE.match(username):
                await update.message.reply_text(
                    "❌ Login faqat a-z, 0-9 va _ dan iborat, 3–32 belgi bo'lsin. Qaytadan:"
                )
                return
            if db_users.get_by_username(username):
                await update.message.reply_text("❌ Bu login band. Boshqa login:")
                return
            context.user_data["new_user"]["username"] = username
            context.user_data["state"] = "add_password"
            await update.message.reply_text(
                "3/3 — Parol kiriting (kamida 4 belgi):", reply_markup=CANCEL_KEYBOARD
            )
            return

        if state == "add_password":
            try:
                await update.message.delete()
            except Exception:
                pass
            if len(text) < 4:
                await update.message.reply_text("❌ Parol kamida 4 belgi bo'lsin. Qaytadan:")
                return
            new_user = context.user_data.pop("new_user")
            context.user_data.pop("state", None)
            record = db_users.create_user(
                new_user["full_name"],
                new_user["username"],
                hash_password(text),
            )
            msg_id = await channel_service.sync_user_card(context.bot, record, is_new=True)
            if msg_id:
                db_users.update_user(record["id"], msg_id=msg_id)
            await update.message.reply_text(
                f"✅ <b>User ro'yxatga olindi!</b>\n\n"
                f"🆔 ID: {record['id']}\n"
                f"👤 Ism: {esc(record['full_name'])}\n"
                f"🔐 Login: @{esc(record['username'])}\n\n"
                "User botga kirib «Ro'yxatdan o'tishni tasdiqlash» orqali "
                "shu login/parol bilan tasdiqlaydi.",
                parse_mode="HTML",
                reply_markup=ADMIN_KEYBOARD,
            )
            return

        if state == "edit_value":
            pending_edit = context.user_data.get("edit")
            if not pending_edit:
                context.user_data.clear()
                await update.message.reply_text("Xatolik — qaytadan urinib ko'ring.")
                return
            uid, field = pending_edit["uid"], pending_edit["field"]
            target = db_users.get_by_id(uid)
            if not target:
                context.user_data.clear()
                await update.message.reply_text("User topilmadi.")
                return

            if field == "name":
                if len(text) < 2:
                    await update.message.reply_text("Ism juda qisqa. Qaytadan:")
                    return
                target = db_users.update_user(uid, full_name=text)
            elif field == "username":
                username = normalize_username(text)
                if not USERNAME_RE.match(username):
                    await update.message.reply_text("❌ Login faqat a-z, 0-9, _ (3–32 belgi). Qaytadan:")
                    return
                existing = db_users.get_by_username(username)
                if existing and existing["id"] != uid:
                    await update.message.reply_text("❌ Bu login band. Boshqa login:")
                    return
                target = db_users.update_user(uid, username=username)
            elif field == "password":
                try:
                    await update.message.delete()
                except Exception:
                    pass
                if len(text) < 4:
                    await update.message.reply_text("❌ Parol kamida 4 belgi. Qaytadan:")
                    return
                target = db_users.update_user(uid, password_hash=hash_password(text))

            msg_id = await channel_service.sync_user_card(
                context.bot, target, is_new=False, event="✏️ USER YANGILANDI"
            )
            if msg_id:
                db_users.update_user(uid, msg_id=msg_id)
            context.user_data.clear()
            await update.message.reply_text(
                f"✅ #{target['id']} yangilandi.\n\n" + user_detail_text(db_users.get_by_id(uid)),
                parse_mode="HTML",
                reply_markup=BACK_TO_USERS,
            )
            return

    # ============ State yo'q ============
    if known or admin:
        await update.message.reply_text(
            "Menyu yoki /start ni tanlang.", reply_markup=main_keyboard(admin)
        )
    else:
        await update.message.reply_text(
            "Avval tasdiqlashdan o'ting:", reply_markup=REG_CONFIRM_KEYBOARD
        )
