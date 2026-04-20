"""
Telegram-бот: проверка карты и привязка chat_id для рассылок.

Запуск из корня проекта (после migrate), токен в .env:
  python bot/bot.py
"""
from __future__ import annotations

import asyncio
import html
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from dotenv import load_dotenv

# load_dotenv до django.setup() / core.settings
_ENV_PATH = BASE_DIR / '.env'
_DOTENV_LOADED = load_dotenv(_ENV_PATH, override=True, encoding='utf-8-sig')

import os

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')

import django

django.setup()

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandObject
from aiogram.types import BotCommand, KeyboardButton, Message, ReplyKeyboardMarkup
from asgiref.sync import sync_to_async
from django.conf import settings
from django.db.models import Q

from app.models import Card, card_mask, format_card
from app.services import prepare_message, send_message

TOKEN = (getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or '').strip()
if not TOKEN:
    raise RuntimeError(
        'Missing TELEGRAM_BOT_TOKEN. Expected a line like TELEGRAM_BOT_TOKEN=123456:ABC... '
        f'in "{_ENV_PATH}" (file exists: {_ENV_PATH.exists()}, dotenv loaded: {_DOTENV_LOADED}). '
        'Remove any empty TELEGRAM_BOT_TOKEN from Windows environment variables if set.'
    )

bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML),
)
dp = Dispatcher()

STATUS_RU = {
    'active': 'активна',
    'inactive': 'неактивна',
    'expired': 'просрочена',
}


def main_reply_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text='📋 Справка'),
                KeyboardButton(text='🔗 Привязать карту'),
            ],
            [KeyboardButton(text='ℹ️ Формат номера')],
        ],
        resize_keyboard=True,
        input_field_placeholder='16 цифр номера карты…',
    )


def _digits_16(text: str) -> str | None:
    digits = ''.join(c for c in (text or '') if c.isdigit())
    return digits if len(digits) == 16 else None


@sync_to_async
def _get_card(formatted: str, digits: str) -> Card | None:
    # Support cards saved either as "8600 1234 ..." or "86001234..."
    return Card.objects.filter(
        Q(card_number=formatted) | Q(card_number=digits)
    ).first()


@sync_to_async
def _link_card(formatted: str, digits: str, chat_id: int) -> tuple[bool, str]:
    n = Card.objects.filter(
        Q(card_number=formatted) | Q(card_number=digits)
    ).update(telegram_chat_id=chat_id)
    if not n:
        return False, 'Карта с таким номером не найдена в базе.'
    return (
        True,
        '✅ <b>Карта привязана.</b>\n'
        'Уведомления по этой карте будут приходить в этот чат.',
    )


def _help_text() -> str:
    return (
        '<b>📌 Что умеет бот</b>\n\n'
        '• Отправьте <b>16 цифр</b> номера карты — бот покажет статус '
        '(для статуса «активна» — баланс).\n'
        '• <code>/link 8600123456789012</code> — привязать карту к этому чату '
        'для рассылок из админки.\n'
        '• <code>/echo текст</code> — проверка отправки сообщения в этот чат.\n\n'
        '<b>Команды:</b> /start — главное меню, /help — эта справка.'
    )


@dp.message(Command('start'))
async def start_handler(message: Message):
    await message.answer(
        '<b>👋 Добро пожаловать.</b>\n\n'
        'Бот для проверки банковских карт из учебной базы.\n'
        'Выберите действие кнопкой ниже или отправьте номер карты (16 цифр).',
        reply_markup=main_reply_keyboard(),
    )


@dp.message(Command('help'))
async def help_handler(message: Message):
    await message.answer(_help_text(), reply_markup=main_reply_keyboard())


@dp.message(F.text.in_({'📋 Справка', 'Справка'}))
async def button_help(message: Message):
    await help_handler(message)


@dp.message(F.text == '🔗 Привязать карту')
async def button_link_help(message: Message):
    await message.answer(
        '<b>Привязка карты</b>\n\n'
        'Отправьте команду в таком виде (16 цифр подряд):\n'
        '<code>/link 8600123456789012</code>\n\n'
        'После привязки сюда смогут приходить служебные сообщения по этой карте.',
        reply_markup=main_reply_keyboard(),
    )


@dp.message(F.text == 'ℹ️ Формат номера')
async def button_format(message: Message):
    await message.answer(
        '<b>Формат номера карты</b>\n\n'
        'Нужны ровно <b>16 цифр</b>. Можно с пробелами или без — например:\n'
        '<code>8600 1234 5678 9012</code>\n'
        'или\n<code>8600123456789012</code>',
        reply_markup=main_reply_keyboard(),
    )


@dp.message(Command('link'))
async def link_handler(message: Message, command: CommandObject):
    raw = command.args or ''
    digits = ''.join(c for c in raw if c.isdigit())
    if len(digits) != 16:
        await message.answer(
            '❌ Укажите 16 цифр после команды.\n'
            'Пример: <code>/link 8600123456789012</code>',
            reply_markup=main_reply_keyboard(),
        )
        return
    formatted = format_card(digits)
    _ok, text = await _link_card(formatted, digits, message.chat.id)
    await message.answer(text, reply_markup=main_reply_keyboard())


@dp.message(Command('echo'))
async def echo_handler(message: Message, command: CommandObject):
    msg = (command.args or 'тест').strip() or 'тест'
    ok = await asyncio.to_thread(send_message, msg, message.chat.id)
    await message.answer(
        '✅ Тестовое сообщение отправлено.' if ok else '❌ Ошибка отправки (см. логи сервера).',
        reply_markup=main_reply_keyboard(),
    )


@dp.message()
async def card_lookup_handler(message: Message):
    text = (message.text or '').strip()
    if text.startswith('/'):
        await message.answer(
            '❓ Неизвестная команда. Откройте <b>📋 Справка</b> или отправьте <code>/help</code>.',
            reply_markup=main_reply_keyboard(),
        )
        return

    digits = _digits_16(text)
    if not digits:
        await message.answer(
            '❌ Нужен номер карты: ровно <b>16 цифр</b>.\n'
            'Нажмите <b>ℹ️ Формат номера</b> для примера.',
            reply_markup=main_reply_keyboard(),
        )
        return

    formatted = format_card(digits)
    card = await _get_card(formatted, digits)
    if not card:
        await message.answer(
            '🔍 Карта с таким номером <b>не найдена</b> в базе.',
            reply_markup=main_reply_keyboard(),
        )
        return

    masked = html.escape(card_mask(card.card_number))
    if card.status != 'active':
        st = STATUS_RU.get(card.status, card.status)
        exp = html.escape(card.expire or '—')
        await message.answer(
            f'<b>Карта</b> <code>{masked}</code>\n'
            f'<b>Статус:</b> {html.escape(st)}\n'
            f'<b>Срок (в базе):</b> {exp}',
            reply_markup=main_reply_keyboard(),
        )
        return

    body = html.escape(
        prepare_message(card.card_number, card.balance, lang='RU', mask_card=True)
    )
    await message.answer(
        f'<b>✅ Карта активна</b>\n\n{body}',
        reply_markup=main_reply_keyboard(),
    )


async def main():
    await bot.set_my_commands(
        [
            BotCommand(command='start', description='Главное меню'),
            BotCommand(command='help', description='Справка по боту'),
            BotCommand(command='link', description='Привязать карту к чату'),
            BotCommand(command='echo', description='Тест отправки в чат'),
        ]
    )
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
