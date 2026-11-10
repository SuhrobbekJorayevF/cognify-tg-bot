# Cognify Telegram Test Boti

Test yechish + **Coding Arena** boti. Real foydalanish uchun: Neon (bepul Postgres) + Render (bepul Web Service). Userlar admin tomonidan ro'yxatga olinadi, birinchi kirishda Telegram ID'si hisobga biriktiriladi, keyingi safar avtomatik taniladi.

`python-telegram-bot` 22.x asosida.

## Imkoniyatlar

**User:**
- `/start` → bog'langan bo'lsa avtomatik taniladi; bo'lmasa «✅ Ro'yxatdan o'tishni tasdiqlash» tugmasi
- 🏟️ **Kod Arenasi** — admin yaratgan arenalarni yechadi (3 tur savol: A/B/C/D avto-tekshiruv, ta'rifla → ovozli, kod yozish → .py fayl)
- Arena natijasi kanalga ma'lumot bilan yuboriladi (ism, TG ID, login, ball, vaqt)

**Admin (faqat `ADMIN_ID` egasi):**
- 🔐 Admin panel — userlar (ro'yxat/qo'shish/tahrirlash/o'chirish/**bog'lashni tiklash**)
- 🏟️ **Coding Arena boshqaruvi** — arena yaratish/o'chirish/ochish-yopish (🔒 default yopiq), savol qo'shish/o'chirish (3 tur),
  barcha arena/savollar **to'liq kanalga sinxronlanadi** (savol-javoblari bilan)
- Arena ochiq/yopiqligi admin paneldagi tugma bilan; kanalga `🔓 ARENA OCHILDI` / `🔒 ARENA YOPILDI` yoziladi

## Muhit o'zgaruvchilari (Render Environment)

| Nom | Ma'nosi |
|---|---|
| `BOT_TOKEN` | @BotFather tokeningiz |
| `CHANNEL_ID` | Xususiy kanal ID (`-100...`) |
| `ADMIN_ID` | Sizning Telegram ID ingiz |
| `DATABASE_URL` | Neon Postgres connection string |
| `PORT` | Ixtiyoriy — Render o'zi beradi |

### DATABASE_URL olish (Neon — bepul)

1. https://neon.tech → **Sign up** (GitHub/email) — bepul, karta shart emas
2. **Create Project** → Region: `AWS eu-central-1` yoki yaqin
3. Dashboard → **Connection string** → `postgresql://...` ni nusxalang (`sslmode=require` bilan)
4. That's it — bu `DATABASE_URL`

## Render'ga deploy

1. Loyihani GitHub'ga push qiling
2. [render.com](https://render.com) → **New +** → **Web Service** → repoingiz
3. **Build:** `pip install -r requirements.txt` · **Start:** `python bot.py` · **Plan:** Free
4. **Environment** → yuqoridagi 4 ta o'zgaruvchi: `BOT_TOKEN`, `CHANNEL_ID`, `ADMIN_ID`, `DATABASE_URL`
5. **Save** → avtomatik deploy

### 24/7 ishlashi uchun (Render Free uxlab qolmasin)

Render Free instance 15 daqiqa trafiksiz qolsa uxlaydi. Botga UptimeRobot bilan **bepul ping** yuboring:
1. https://uptimerobot.com → ro'yxatdan o'ting (bepul)
2. **Add New Monitor** → Type: **HTTP(s)** → URL: `https://SIZNING-SERVIS.onrender.com/` → Monitoring Interval: **5 minutes**
3. Save — bot tunu kun turadi

### Lokal ishga tushirish

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt

$env:BOT_TOKEN = "..."
$env:CHANNEL_ID = "-1001234567890"
$env:ADMIN_ID = "123456789"
$env:DATABASE_URL = "postgresql://..."
python bot.py
```

## Loyiha tuzilishi

```
bot.py                  # kirish nuqtasi — env tekshirish, health server, run_polling
config.py               # sozlamalar (env) — BOT_TOKEN, DATABASE_URL, PORT, ...

db/                     # DB qatlami — faqat SQL, Telegram yo'q
  schema.sql            # jadvallar (users, arenas, questions, test_results, arena_submissions)
  connection.py         # ulanish + init_db() (CREATE IF NOT EXISTS)
  users.py              # user CRUD, bog'lash/tiklash
  arenas.py             # arena CRUD (savollar bilan)
  questions.py          # savol CRUD (mcq/voice/code)
  results.py            # test natijalari + javob submissionlari (kelajakda statistika)

handlers/               # Telegram handlerlar — faqat mantiq, SQL yo'q
  start.py              # /start /help /cancel + tasdiqlash oqimi
  buttons.py            # barcha tugmalar uchun yagona dispatcher
  text.py               # matnlar: login, admin wizardlari, arena yaratish
  admin_users.py        # userlarni boshqarish
  arena_admin.py        # arenalarni boshqarish, savol yaratish
  arena_user.py         # user arena yechadi (ovozli/.py ham shu yerda)

keyboards.py            # barcha inline klaviaturalar
texts.py                # sozlamali matnlar
services/
  channel.py            # kanal: kartalar, nusxalar, o'chirish
  formatting.py         # matn generatsiya va yordamchilar
```

Qoidalar: `handlers/` SQL yozmaydi · `db/` Telegram bilmaydi · `services/channel.py` — kanalning yagona joyi.

## Muhim eslatmalar

- Kanal **yozish** uchun ishlaydi (API kanal tarixini o'qiy olmaydi) — DB emas, log sifatida. Barcha ma'lumotlar Postgres'da saqlanadi.
- `arena_submissions` jadvalida ovozli/kod javoblarning `file_id`si saqlanadi — kelajakda admin panel ichida javoblarni ko'rsatish/baholash qo'shish mumkin.
- Arena o'chirishda kanaldan ham barcha kartalar o'chiriladi (kaskad).
- Bot faqat bitta joyda ishlasin (lokal yoki Render, ikkalasi emas — `409 Conflict`).
