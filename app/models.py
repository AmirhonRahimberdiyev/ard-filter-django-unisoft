from django.db import models
from django.utils import timezone
import re


class Card(models.Model):
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('expired', 'Expired'),
    ]

    card_number = models.CharField(max_length=19, unique=True)
    expire = models.CharField(max_length=10, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    telegram_chat_id = models.BigIntegerField(
        null=True,
        blank=True,
        help_text='Telegram chat id linked with /link for this card (optional).',
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'cards'

    def __str__(self):
        return self.card_number

    @property
    def masked_card_number(self):
        return card_mask(self.card_number)

    @property
    def masked_phone(self):
        return phone_mask(self.phone) if self.phone else ""


def card_mask(card_number: str) -> str:
    digits = re.sub(r'\D', '', card_number)
    if len(digits) >= 4:
        return f"**** **** **** {digits[-4:]}"
    return "****"


def phone_mask(phone: str) -> str:
    digits = re.sub(r'\D', '', phone)
    if len(digits) == 12 and digits.startswith('998'):
        return f"+{digits[:3]} {digits[3:5]} {digits[5:8]} {digits[8:10]} {digits[10:]}"
    elif len(digits) == 9:
        return f"{digits[:2]} {digits[2:5]} {digits[5:7]} {digits[7:]}"
    return phone


def format_card(raw_card: str) -> str:
    digits = re.sub(r'\D', '', raw_card)
    if len(digits) == 16:
        return " ".join(digits[i:i + 4] for i in range(0, 16, 4))
    return raw_card


def format_phone(raw_phone: str) -> str:
    if not raw_phone:
        return None
    digits = re.sub(r'\D', '', raw_phone)
    if len(digits) == 9:
        return f"998{digits}"
    elif len(digits) == 12 and digits.startswith('998'):
        return digits
    elif len(digits) == 10 and digits.startswith('98'):
        return f"8{digits}"
    return raw_phone


def format_expire(raw_expire: str) -> str:
    if not raw_expire:
        return None
    cleaned = raw_expire.replace('.', '-').replace('/', '-')
    parts = [p for p in cleaned.split('-') if p]
    if len(parts) != 2:
        return raw_expire
    a, b = parts
    try:
        if len(a) == 4 and len(b) <= 2:
            year, month = a, b
        elif len(b) == 4 and len(a) <= 2:
            month, year = a, b
        else:
            month, year = a, b
        if len(year) == 2:
            yi = int(year)
            mo = int(month)
            year = f'20{year}' if yi < 50 else f'19{year}'
            month = str(mo)
        else:
            int(month)
        return f'{year}-{month.zfill(2)}'
    except (ValueError, TypeError):
        return raw_expire
class TransferState(models.TextChoices):
    CREATED = "created", "Created"
    CONFIRMED = "confirmed", "Confirmed"
    CANCELLED = "cancelled", "Cancelled"


class Transfer(models.Model):
    class Currency(models.TextChoices):
        UZS='uzs',"uzs"
        USD='usd',"usd"
        RUB='rub','rub'
    ext_id = models.CharField(max_length=255, unique=True)
    sender_card_number = models.CharField(max_length=32)
    receiver_card_number = models.CharField(max_length=32)
    sender_card_expiry = models.CharField(max_length=5)
    sender_phone = models.CharField(max_length=32, blank=True, null=True)
    receiver_phone = models.CharField(max_length=32, blank=True, null=True)
    sending_amount = models.DecimalField(max_digits=18, decimal_places=2)
    currency = models.CharField(max_length=16,choices=Currency.choices,default=Currency.UZS)
    receiving_amount = models.DecimalField(max_digits=18, decimal_places=2)
    state = models.CharField(
        max_length=16,
        choices=TransferState.choices,
        default=TransferState.CREATED,
    )
    try_count = models.PositiveSmallIntegerField(default=0)
    otp = models.CharField(max_length=6, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(blank=True, null=True)
    cancelled_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("ext_id",)),
            models.Index(fields=("sender_card_number",)),
            models.Index(fields=("receiver_card_number",)),
            models.Index(fields=("state",)),
            models.Index(fields=("created_at",)),
        ]

    def mark_confirmed(self):
        self.state = TransferState.CONFIRMED
        self.confirmed_at = timezone.now()

    def mark_cancelled(self):
        self.state = TransferState.CANCELLED
        self.cancelled_at = timezone.now()

    def __str__(self):
        return f"{self.ext_id} [{self.state}]"


class Error(models.Model):
    code = models.IntegerField(unique=True)
    en = models.CharField(max_length=255)
    ru = models.CharField(max_length=255)
    uz = models.CharField(max_length=255)

    class Meta:
        ordering = ("code",)

    def __str__(self):
        return f"{self.code}: {self.en}"
