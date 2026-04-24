import logging
import random
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import Optional

from django.apps import apps
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from app.models import Error as ErrorMessage
from app.models import Transfer, TransferState

logger = logging.getLogger(__name__)

ALLOWED_CURRENCIES = {643, 840}
OTP_EXPIRY_MINUTES = 5
EXCHANGE_RATES = {
    643: Decimal("150.00"),
    840: Decimal("12800.00"),
    860: Decimal("1.00"),
}
DEFAULT_LANGUAGE = "en"


class TransferServiceError(Exception):
    def __init__(self, code, message=None):
        self.code = code
        self.message = message or resolve_error_message(code)
        super().__init__(self.message)


@dataclass
class CardAdapter:
    card: object
    number_field: str
    expiry_field: Optional[str]
    balance_field: Optional[str]
    active_field: Optional[str]
    phone_field: Optional[str]

    @property
    def number(self):
        return getattr(self.card, self.number_field)

    @property
    def phone(self):
        if not self.phone_field:
            return ""
        return getattr(self.card, self.phone_field, "") or ""

    @property
    def balance(self):
        if not self.balance_field:
            return None
        value = getattr(self.card, self.balance_field, None)
        if value is None:
            return None
        return Decimal(str(value))

    def save(self):
        self.card.save()

    def is_active(self):
        if not self.active_field:
            return True

        value = getattr(self.card, self.active_field, None)
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in {"active", "enabled", "true", "1"}
        if isinstance(value, (int, float, Decimal)):
            return bool(value)
        return bool(value)

    def expiry_matches(self, expiry):
        if not self.expiry_field:
            return True
        value = getattr(self.card, self.expiry_field, None)
        return normalize_expiry(value) == normalize_expiry(expiry)

    def apply_balance_delta(self, delta):
        if not self.balance_field:
            return
        current = self.balance or Decimal("0")
        setattr(self.card, self.balance_field, current + delta)


def generate_otp(length=6):
    lower_bound = 10 ** (length - 1)
    upper_bound = (10**length) - 1
    return str(random.randint(lower_bound, upper_bound))


def send_telegram_message(phone, message, chat_id=123456):
    if not phone:
        logger.warning("Telegram message skipped because phone is missing")
        return False

    logger.info(
        "Simulated Telegram message",
        extra={"phone": phone, "chat_id": chat_id, "message": message},
    )
    return True


def validate_card(card_number):
    digits = "".join(ch for ch in str(card_number) if ch.isdigit())
    if not digits:
        return False

    checksum = 0
    reverse_digits = digits[::-1]
    for index, value in enumerate(reverse_digits):
        number = int(value)
        if index % 2 == 1:
            number *= 2
            if number > 9:
                number -= 9
        checksum += number
    return checksum % 10 == 0


def calculate_exchange(amount, currency):
    decimal_amount = Decimal(str(amount))
    rate = EXCHANGE_RATES.get(int(currency))
    if rate is None:
        raise TransferServiceError(32707)
    return (decimal_amount * rate).quantize(Decimal("0.01"))


def get_transfer_by_ext_id(ext_id):
    try:
        return Transfer.objects.get(ext_id=ext_id)
    except Transfer.DoesNotExist as exc:
        raise TransferServiceError(-32004, "Transfer not found") from exc


def resolve_error_message(code, language=DEFAULT_LANGUAGE, **context):
    if code == 32712 and "left_try_count" in context:
        return f"Incorrect OTP. Attempts left: {context['left_try_count']}"

    error = ErrorMessage.objects.filter(code=code).first()
    if not error:
        return context.get("default", "Unknown error occurred")

    template = getattr(error, language, "") or error.en
    return template.format(**context) if context else template


def normalize_expiry(value):
    if value is None:
        return None
    if isinstance(value, (date, datetime)):
        return value.strftime("%m/%y")

    raw = str(value).strip()
    if not raw:
        return None

    digits = "".join(ch for ch in raw if ch.isdigit())
    if len(digits) == 4:
        return f"{digits[:2]}/{digits[2:]}"
    if len(digits) == 6:
        return f"{digits[2:4]}/{digits[4:]}"
    if "/" in raw and len(raw.split("/", 1)[0]) == 2:
        left, right = raw.split("/", 1)
        return f"{left.zfill(2)}/{right[-2:]}"
    return raw


def validate_expiry_format(expiry):
    normalized = normalize_expiry(expiry)
    if not normalized or len(normalized) != 5 or normalized[2] != "/":
        return False

    month = normalized[:2]
    year = normalized[-2:]
    if not month.isdigit() or not year.isdigit():
        return False

    month_number = int(month)
    return 1 <= month_number <= 12


def build_date_range(start_date, end_date):
    filters = {}

    if start_date:
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        filters["created_at__gte"] = ensure_timezone(datetime.combine(start, time.min))
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        filters["created_at__lte"] = ensure_timezone(datetime.combine(end, time.max))

    return filters


def ensure_timezone(value):
    current_time = timezone.now()
    if timezone.is_aware(current_time) and timezone.is_naive(value):
        return timezone.make_aware(value)
    return value


def get_card_model():
    return apps.get_model("app", "Card")


def get_card_adapter(card_number):
    model = get_card_model()
    field_names = {field.name for field in model._meta.fields}
    number_field = first_existing(field_names, ("card_number", "number", "pan"))
    if not number_field:
        raise TransferServiceError(-32010, "Card model number field is not configured")

    card = model.objects.filter(**{number_field: card_number}).first()
    if not card:
        raise TransferServiceError(32706, "Card not found")

    return CardAdapter(
        card=card,
        number_field=number_field,
        expiry_field=first_existing(field_names, ("expiry", "expiry_date", "expire_date", "expire")),
        balance_field=first_existing(field_names, ("balance", "amount", "saldo")),
        active_field=first_existing(field_names, ("is_active", "active", "status")),
        phone_field=first_existing(field_names, ("phone", "phone_number", "owner_phone")),
    )


def first_existing(field_names, candidates):
    for candidate in candidates:
        if candidate in field_names:
            return candidate
    return None


def ensure_transfer_can_be_modified(transfer):
    if transfer.state != TransferState.CREATED:
        raise TransferServiceError(32713)


@transaction.atomic
def create_transfer(
    ext_id,
    sender_card_number,
    receiver_card_number,
    sender_card_expiry,
    sending_amount,
    currency,
    sender_phone=None,
    receiver_phone=None,
):
    if Transfer.objects.filter(ext_id=ext_id).exists():
        raise TransferServiceError(32701)

    if not validate_card(sender_card_number) or not validate_card(receiver_card_number):
        raise TransferServiceError(32706, "Card number is not valid")

    if not validate_expiry_format(sender_card_expiry):
        raise TransferServiceError(32704)

    currency = int(currency)
    if currency not in ALLOWED_CURRENCIES:
        raise TransferServiceError(32707)

    amount = Decimal(str(sending_amount))
    if amount <= 0:
        raise TransferServiceError(32709)

    sender_card = get_card_adapter(sender_card_number)
    receiver_card = get_card_adapter(receiver_card_number)

    if not sender_card.expiry_matches(sender_card_expiry):
        raise TransferServiceError(32704)

    if not sender_card.is_active() or not receiver_card.is_active():
        raise TransferServiceError(32705)

    if sender_card.balance is not None and sender_card.balance < amount:
        raise TransferServiceError(32702)

    sender_phone = sender_phone or sender_card.phone
    receiver_phone = receiver_phone or receiver_card.phone
    if not sender_phone:
        raise TransferServiceError(32703)

    receiving_amount = calculate_exchange(amount, currency)
    otp = generate_otp()

    sent = send_telegram_message(sender_phone, f"Your OTP code is {otp}")
    if not sent:
        raise TransferServiceError(32703)

    transfer = Transfer.objects.create(
        ext_id=ext_id,
        sender_card_number=sender_card_number,
        receiver_card_number=receiver_card_number,
        sender_card_expiry=normalize_expiry(sender_card_expiry) or sender_card_expiry,
        sender_phone=sender_phone,
        receiver_phone=receiver_phone,
        sending_amount=amount,
        currency=currency,
        receiving_amount=receiving_amount,
        state=TransferState.CREATED,
        otp=otp,
    )
    logger.info("Transfer created", extra={"ext_id": ext_id})
    return transfer


@transaction.atomic
def confirm_transfer(ext_id, otp):
    transfer = get_transfer_by_ext_id(ext_id)
    ensure_transfer_can_be_modified(transfer)

    expiry_time = transfer.created_at + timedelta(minutes=OTP_EXPIRY_MINUTES)
    if timezone.now() > expiry_time:
        transfer.mark_cancelled()
        transfer.save(update_fields=("state", "cancelled_at", "updated_at"))
        raise TransferServiceError(32710)

    if transfer.otp != str(otp):
        transfer.try_count += 1
        update_fields = ("try_count", "updated_at")

        if transfer.try_count >= 3:
            transfer.mark_cancelled()
            transfer.save(update_fields=("try_count", "state", "cancelled_at", "updated_at"))
            raise TransferServiceError(32711)

        transfer.save(update_fields=update_fields)
        raise TransferServiceError(
            32712,
            resolve_error_message(32712, left_try_count=3 - transfer.try_count),
        )

    sender_card = get_card_adapter(transfer.sender_card_number)
    receiver_card = get_card_adapter(transfer.receiver_card_number)
    amount = Decimal(str(transfer.sending_amount))
    receiving_amount = Decimal(str(transfer.receiving_amount))

    if sender_card.balance is not None and sender_card.balance < amount:
        raise TransferServiceError(32702)

    sender_card.apply_balance_delta(-amount)
    receiver_card.apply_balance_delta(receiving_amount)
    sender_card.save()
    receiver_card.save()

    transfer.mark_confirmed()
    transfer.save(update_fields=("state", "confirmed_at", "updated_at"))
    logger.info("Transfer confirmed", extra={"ext_id": transfer.ext_id})
    return transfer


@transaction.atomic
def cancel_transfer(ext_id):
    transfer = get_transfer_by_ext_id(ext_id)
    ensure_transfer_can_be_modified(transfer)
    transfer.mark_cancelled()
    transfer.save(update_fields=("state", "cancelled_at", "updated_at"))
    logger.info("Transfer cancelled", extra={"ext_id": transfer.ext_id})
    return transfer


def get_transfer_state(ext_id):
    return get_transfer_by_ext_id(ext_id)


def get_transfer_history(card_number=None, start_date=None, end_date=None, status=None):
    queryset = Transfer.objects.all()

    if card_number:
        queryset = queryset.filter(
            Q(sender_card_number=card_number) | Q(receiver_card_number=card_number)
        )

    if status:
        queryset = queryset.filter(state=status)

    date_filters = build_date_range(start_date, end_date)
    if date_filters:
        queryset = queryset.filter(**date_filters)

    return queryset.order_by("-created_at")
