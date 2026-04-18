import re
from django.contrib import admin
from django import forms
from import_export.admin import ImportExportModelAdmin
from .models import Card
from .resources import CardResource


def card_mask(card_number):
    """Mask card number: 8600 **** **** 9012"""
    if not card_number:
        return ""
    digits = re.sub(r'\D', '', str(card_number))
    if len(digits) >= 16:
        return f"{digits[:4]} **** **** {digits[12:]}"
    return card_number


def phone_mask(phone):
    """Mask phone: 99 973 ***03"""
    if not phone:
        return ""
    digits = re.sub(r'\D', '', str(phone))
    if len(digits) == 12:
        return f"+{digits[:3]} ({digits[3:5]}) ***-{digits[10:]}"
    return phone


class CardAdminForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = '__all__'

    def clean_card_number(self):
        card = self.cleaned_data.get('card_number')
        if card:
            digits = re.sub(r'\D', '', str(card))
            if len(digits) != 16:
                raise forms.ValidationError("Card number must be 16 digits")
        return card

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            digits = re.sub(r'\D', '', str(phone))
            if len(digits) not in (9, 12):
                raise forms.ValidationError("Invalid phone format")
        return phone


@admin.register(Card)
class CardAdmin(ImportExportModelAdmin):
    resource_class = CardResource
    form = CardAdminForm
    list_display = ('id', 'formatted_card', 'formatted_balance', 'status', 'formatted_expiry', 'formatted_phone')
    list_filter = (
        'status',
        'expiry_date',
    )
    search_fields = ('card_number', 'phone')
    readonly_fields = ('id',)
    list_per_page = 25

    def formatted_card(self, obj):
        return card_mask(obj.card_number)
    formatted_card.short_description = 'Card Number'

    def formatted_phone(self, obj):
        if not obj.phone:
            return "(empty)"
        return phone_mask(obj.phone)
    formatted_phone.short_description = 'Phone'

    def formatted_expiry(self, obj):
        if obj.expiry_date:
            return obj.expiry_date.strftime('%m/%y')
        return "-"
    formatted_expiry.short_description = 'Expire'

    def formatted_balance(self, obj):
        return f"{obj.balance:,.2f} UZS" if obj.balance else "0.00 UZS"
    formatted_balance.short_description = 'Balance'