# ard-filter-django-unisoft

Django training project: **bank cards** admin workflow, **Excel import**, **CSV export**, **Telegram bot** for lookups and notifications, plus management commands for bulk messaging.

## Features

- **Models**: `Card` with `card_number`, `expire`, `phone`, `status` (`active` / `inactive` / `expired`), `balance`, optional `telegram_chat_id` for outbound Telegram messages.
- **Normalization helpers** (`app/models.py`): `format_card`, `format_phone`, `format_expire`, `card_mask`, `phone_mask`.
- **Admin**: masked list display, filters (status, expire, phone present / absent, balance bands), custom import view for `.xlsx`.
- **Services** (`app/services.py`): Excel import with row-level validation, CSV export, `prepare_message`, real **`send_message`** via Telegram Bot API when configured.
- **Commands**:
  - `python manage.py export_cards [--status] [--card-number] [--phone] [--output]`
  - `python manage.py send_messages [--status] [--dry-run|--send] [--chat-id]`
- **Telegram bot** (`bot/bot.py`, aiogram 3): `/start`, `/help`, `/link <16-digit PAN>`, plain PAN lookup for active cards, `/echo` smoke test.

## Requirements

- Python 3.12+ (tested with Django 6.x)
- Dependencies: see `requirements.txt` (`Django`, `pandas`, `openpyxl`, `aiogram`, `python-dotenv`)

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux / macOS

pip install -r requirements.txt
copy env.example .env           # then edit .env — do NOT commit secrets
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Environment variables

Create a **local** `.env` in the project root (same folder as `manage.py`). The app loads it automatically via **`python-dotenv`** when you run `manage.py`, `bot/bot.py`, or WSGI/ASGI (so you usually do not need to `export` variables manually).

Never commit real tokens to git (`.env` is gitignored).

If the bot still says the token is missing: put `.env` next to `manage.py` (not inside `bot/`). Use the exact name `TELEGRAM_BOT_TOKEN` (no spaces around `=`). Save `.env` as **UTF-8** (Notepad “UTF-8” or “UTF-8 with BOM” both work). Do **not** import `core.settings` at the top of `bot/bot.py` before `load_dotenv` — that loads Django before `.env` is applied. On Windows, remove an empty user/system `TELEGRAM_BOT_TOKEN` if present; `.env` uses `override=True` so a filled `.env` wins.

| Variable | Purpose |
|----------|---------|
| `TELEGRAM_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather). Alias: `BOT_TOKEN`. |
| `TELEGRAM_DEFAULT_CHAT_ID` | Optional fallback chat id when a card has no `telegram_chat_id`. |

Example (PowerShell):

```powershell
$env:TELEGRAM_BOT_TOKEN = "<paste your token only here locally>"
$env:TELEGRAM_DEFAULT_CHAT_ID = "123456789"
```

## Sample Excel

Generate a starter spreadsheet:

```bash
python create_sample.py
```

Then use **Admin → Cards → Import** (or your custom import URL) to load the file.

## Telegram bot

From the repository root:

```bash
python bot/bot.py
```

1. Open the bot in Telegram and send `/start`.
2. Link this chat to a card: `/link 8600123456789012` (PAN as stored after normalization).
3. **Bulk messages** from Django (after linking, or with `--chat-id` / `TELEGRAM_DEFAULT_CHAT_ID`):

```bash
python manage.py send_messages --dry-run --status active
python manage.py send_messages --send --status active --chat-id YOUR_CHAT_ID
```

## Security notes

- Rotate any bot token that was shared in chat, tickets, or screenshots; use `.env` only on machines you control.
- Change `SECRET_KEY` and set `DEBUG=False` before production deployment.

## Branch **Bositxon**

This branch carries the full card admin + import/export + Telegram integration described above.
