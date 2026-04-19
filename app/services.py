import io
import json
import logging
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation
from typing import BinaryIO, Union

from django.conf import settings

from app.models import Card, card_mask, format_card, format_expire, format_phone

logger = logging.getLogger(__name__)

FileOrPath = Union[str, BinaryIO, io.BufferedReader]


def format_uzs_balance(balance) -> str:
    try:
        d = Decimal(str(balance))
    except (InvalidOperation, TypeError, ValueError):
        d = Decimal('0')
    return f'{d:,.2f}'


def prepare_message(
    card_number: str,
    balance,
    lang: str = 'UZ',
    *,
    mask_card: bool = False,
) -> str:
    display = card_mask(card_number) if mask_card else card_number
    bal = format_uzs_balance(balance)
    if lang == 'UZ':
        return (
            f'Sizning kartangiz {display} aktiv va foydalanishga {bal} UZS mavjud!'
        )
    return f'Ваша карта {display} активна и доступно {bal} UZS!'


def send_message(message: str, chat_id: int | None = None) -> bool:
    """
    Send a Telegram message when TELEGRAM_BOT_TOKEN and chat_id are set;
    otherwise log only (simulation).
    """
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', '') or ''
    if not token or chat_id is None:
        logger.info('[telegram/simulated] chat_id=%s: %s', chat_id, message)
        return False

    url = f'https://api.telegram.org/bot{token}/sendMessage'
    payload = json.dumps({'chat_id': chat_id, 'text': message}).encode('utf-8')
    req = urllib.request.Request(
        url,
        data=payload,
        headers={'Content-Type': 'application/json'},
        method='POST',
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode('utf-8'))
        if not body.get('ok'):
            logger.error('Telegram API error: %s', body)
            return False
        logger.info('Telegram message delivered chat_id=%s', chat_id)
        return True
    except urllib.error.HTTPError as e:
        err = e.read().decode('utf-8', errors='replace')
        logger.error('Telegram HTTPError %s: %s', e.code, err)
        return False
    except urllib.error.URLError as e:
        logger.error('Telegram URLError: %s', e)
        return False


def import_cards_from_excel(file: FileOrPath) -> dict:
    import pandas as pd
    from django.db import IntegrityError

    df = pd.read_excel(file)
    imported = 0
    errors = []
    max_balance = Decimal('1200000000')

    for idx, row in df.iterrows():
        try:
            raw_card = str(row.get('card_number', '')).strip()
            raw_expire = str(row.get('expire', '')).strip()
            raw_phone = str(row.get('phone', '')).strip()
            status = str(row.get('status', 'active')).strip().lower()
            balance_raw = str(row.get('balance', '0')).strip()

            if not raw_card or raw_card == 'nan':
                errors.append(f'Row {idx + 2}: Card number is required')
                continue

            card_number = format_card(raw_card)
            if len(card_number.replace(' ', '')) != 16:
                errors.append(f'Row {idx + 2}: Invalid card number format')
                continue

            expire = (
                format_expire(raw_expire)
                if raw_expire and raw_expire != 'nan'
                else None
            )

            phone = (
                format_phone(raw_phone)
                if raw_phone and raw_phone != 'nan'
                else None
            )

            if status not in ['active', 'inactive', 'expired']:
                errors.append(f'Row {idx + 2}: Invalid status {status!r}')
                continue

            balance_str = balance_raw.replace(',', '').replace(' ', '')
            try:
                balance = Decimal(balance_str)
            except (InvalidOperation, ValueError):
                errors.append(f'Row {idx + 2}: Invalid balance')
                continue

            if balance < 0 or balance > max_balance:
                errors.append(
                    f'Row {idx + 2}: Balance must be between 0 and 1.2 billion UZS'
                )
                continue

            Card.objects.update_or_create(
                card_number=card_number,
                defaults={
                    'expire': expire,
                    'phone': phone,
                    'status': status,
                    'balance': balance,
                },
            )
            imported += 1

        except IntegrityError as e:
            errors.append(f'Row {idx + 2}: Integrity error - {e!s}')
        except Exception as e:
            errors.append(f'Row {idx + 2}: {e!s}')

    return {'imported': imported, 'errors': errors}


def export_cards_to_csv(
    file_path: str,
    status: str | None = None,
    card_number: str | None = None,
    phone: str | None = None,
):
    import csv

    queryset = Card.objects.all()

    if status:
        queryset = queryset.filter(status=status)
    if card_number:
        queryset = queryset.filter(card_number__icontains=card_number)
    if phone:
        queryset = queryset.filter(phone__icontains=phone)

    with open(file_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(
            ['card_number', 'expire', 'phone', 'status', 'balance', 'telegram_chat_id']
        )

        for card in queryset:
            writer.writerow(
                [
                    card.card_number,
                    card.expire or '',
                    card.phone or '',
                    card.status,
                    str(card.balance),
                    card.telegram_chat_id or '',
                ]
            )

    return queryset.count()


def send_messages_to_cards(
    status: str | None = None,
    *,
    dry_run: bool = True,
    default_chat_id: int | None = None,
) -> dict:
    queryset = Card.objects.all()
    if status:
        queryset = queryset.filter(status=status)

    default_chat_id = default_chat_id or getattr(
        settings, 'TELEGRAM_DEFAULT_CHAT_ID', None
    )

    sent = 0
    failed = 0
    results = []

    for card in queryset:
        message = prepare_message(card.card_number, card.balance)
        chat_id = card.telegram_chat_id or default_chat_id

        if dry_run:
            logger.info('[dry-run] chat_id=%s card=%s', chat_id, card.card_number)
            success = True
        else:
            success = send_message(message, chat_id)

        if success:
            sent += 1
            results.append({'card': card.card_number, 'message': message, 'chat_id': chat_id})
        else:
            failed += 1
            results.append(
                {
                    'card': card.card_number,
                    'message': message,
                    'chat_id': chat_id,
                    'error': 'no chat_id or send failed',
                }
            )

    return {'sent': sent, 'failed': failed, 'results': results}
