"""
Telegram bot: card lookup and linking chat_id for outbound notifications.

Run from project root (after migrate):
  set TELEGRAM_BOT_TOKEN=...
  python bot/bot.py
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django

django.setup()

from aiogram import Bot, Dispatcher
from aiogram.filters import Command, CommandObject
from aiogram.types import Message
from asgiref.sync import sync_to_async
from django.conf import settings

from app.models import Card, card_mask, format_card
from app.services import prepare_message, send_message

TOKEN = (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()
if not TOKEN:
    raise RuntimeError(
        'Set TELEGRAM_BOT_TOKEN (or BOT_TOKEN) in the environment before starting the bot.'
    )

bot = Bot(token=TOKEN)
dp = Dispatcher()


def _digits_16(text: str) -> str | None:
    digits = ''.join(c for c in (text or '') if c.isdigit())
    return digits if len(digits) == 16 else None


@sync_to_async
def _get_card(formatted: str) -> Card | None:
    return Card.objects.filter(card_number=formatted).first()


@sync_to_async
def _link_card(formatted: str, chat_id: int) -> tuple[bool, str]:
    n = Card.objects.filter(card_number=formatted).update(telegram_chat_id=chat_id)
    if not n:
        return False, 'Karta topilmadi.'
    return (
        True,
        "Karta bog'landi. Bildirishnomalar endi shu Telegram chatiga yuboriladi.",
    )


@dp.message(Command('start'))
async def start_handler(message: Message):
    await message.answer(
        'Salom!\n'
        '/help — komandalar\n'
        "/link <16 raqam> — kartani ushbu chatga bog'lash\n"
        '16 raqamli PAN yuboring — faol kartalar uchun xabar.\n'
    )


@dp.message(Command('help'))
async def help_handler(message: Message):
    await start_handler(message)


@dp.message(Command('link'))
async def link_handler(message: Message, command: CommandObject):
    raw = command.args or ''
    digits = ''.join(c for c in raw if c.isdigit())
    if len(digits) != 16:
        await message.answer('Foydalanish: /link 8600123456789012')
        return
    formatted = format_card(digits)
    ok, text = await _link_card(formatted, message.chat.id)
    await message.answer(text)


@dp.message(Command('echo'))
async def echo_handler(message: Message, command: CommandObject):
    """Smoke test: sends a real Telegram message to this chat."""
    msg = (command.args or 'test').strip() or 'test'
    ok = await asyncio.to_thread(send_message, msg, message.chat.id)
    await message.answer('Yuborildi.' if ok else 'Yuborishda xatolik (loglarni tekshiring).')


@dp.message()
async def card_lookup_handler(message: Message):
    text = (message.text or '').strip()
    if text.startswith('/'):
        await message.answer('Noma\'lum komanda. /help')
        return

    digits = _digits_16(text)
    if not digits:
        await message.answer("Karta uchun 16 ta raqam yuboring (bo'shliqsiz ham bo'ladi).")
        return

    formatted = format_card(digits)
    card = await _get_card(formatted)
    if not card:
        await message.answer('Karta topilmadi.')
        return

    masked = card_mask(card.card_number)
    if card.status != 'active':
        await message.answer(f'{masked}\nHolat: {card.status}')
        return

    await message.answer(
        prepare_message(card.card_number, card.balance, mask_card=True)
    )


async def main():
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
