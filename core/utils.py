import re
from datetime import datetime


def card_mask(card_number):
    """Mask card number: 8600 **** **** 9012"""
    if not card_number:
        return ""
    digits = re.sub(r'\D', '', str(card_number))
    if len(digits) >= 16:
        return f"{digits[:4]} **** **** {digits[12:]}"
    return card_number


def phone_mask(phone):
    """Mask phone: +998 (99) ***-03-03"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 12:
        return f"+{digits[:3]} ({digits[3:5]}) ***-{digits[10:]}"
    return phone


def format_card(raw_card):
    """Format card number to 8600 1234 5678 9012"""
    if not raw_card:
        return ""
    digits = re.sub(r'\D', '', str(raw_card))
    if len(digits) != 16:
        return ""
    return " ".join([digits[i:i+4] for i in range(0, 16, 4)])


def format_phone(raw_phone):
    """Format phone to +998 99 123 45 67"""
    if not raw_phone:
        return ""
    val = str(raw_phone).strip()
    if val.lower() in ('(empty)', 'none', 'null', '', 'nan'):
        return ""
    digits = re.sub(r'\D', '', val)
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) == 12:
        return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"
    return raw_phone


def clean_phone_number(phone):
    """Clean phone to digits only"""
    if not phone:
        return None
    val = str(phone).strip()
    if val.lower() in ('(empty)', 'none', 'null', '', 'nan'):
        return None
    digits = re.sub(r'\D', '', val)
    if len(digits) == 9:
        return "998" + digits
    if len(digits) == 12:
        return digits
    return None


def clean_card_number(card):
    """Clean card to 16 digits"""
    if not card:
        return None
    digits = re.sub(r'\D', '', str(card))
    if len(digits) == 16:
        return digits
    return None


def parse_expiry_date(value):
    """Parse various date formats to date object"""
    if not value or str(value).strip() == '':
        return None

    val = str(value).strip()
    formats = [
        '%m/%y', '%m.%y', '%m-%y',
        '%Y-%m-%d', '%Y-%m',
        '%m/%Y', '%m.%Y', '%m-%Y',
    ]

    for fmt in formats:
        try:
            date_obj = datetime.strptime(val, fmt)
            if date_obj.year < 2000:
                if date_obj.year < 50:
                    date_obj = date_obj.replace(year=date_obj.year + 2000)
                else:
                    date_obj = date_obj.replace(year=date_obj.year + 1900)
            return date_obj.date()
        except ValueError:
            continue
    return None


def format_balance(balance):
    """Format balance: 1 250 400.00"""
    if balance is None:
        return "0.00"
    return "{:,.2f}".format(float(balance)).replace(",", " ")


def prepare_message(card_number, balance, lang="UZ"):
    """Prepare message template for card"""
    if lang == "UZ":
        return f"Sizning kartangiz {format_card(card_number)} aktiv va foydalanishga {format_balance(balance)} UZS mavjud!"
    return f"Ваша карта {format_card(card_number)} активна и доступно {format_balance(balance)} UZS!"


def send_message(message, chat_id=None):
    """Simulate sending message (log to console)"""
    print(f"[TELEGRAM] Sending to chat_id={chat_id}: {message}")
    return True