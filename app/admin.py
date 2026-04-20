import io

from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django import forms
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.db.models import Q

from app.models import Card, card_mask, format_card, format_expire, format_phone, phone_mask
from app.services import import_cards_from_excel


class ImportForm(forms.Form):
    excel_file = forms.FileField(label='Excel File (.xlsx)')


class PhonePresentFilter(admin.SimpleListFilter):
    title = 'phone'
    parameter_name = 'phone_present'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Has phone'),
            ('no', 'Empty phone'),
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == 'yes':
            return queryset.exclude(Q(phone__isnull=True) | Q(phone=''))
        if v == 'no':
            return queryset.filter(Q(phone__isnull=True) | Q(phone=''))
        return queryset


class BalanceBandFilter(admin.SimpleListFilter):
    title = 'balance band'
    parameter_name = 'balance_band'

    def lookups(self, request, model_admin):
        return (
            ('low', '0 – 9,999.99'),
            ('mid', '10,000 – 999,999.99'),
            ('high', '1,000,000+'),
        )

    def queryset(self, request, queryset):
        v = self.value()
        if v == 'low':
            return queryset.filter(balance__lt=10000)
        if v == 'mid':
            return queryset.filter(balance__gte=10000, balance__lt=1000000)
        if v == 'high':
            return queryset.filter(balance__gte=1000000)
        return queryset


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = (
        'masked_card_number',
        'masked_phone',
        'status',
        'expire',
        'balance',
        'telegram_chat_id',
        'created_at',
    )
    list_filter = ('status', 'expire', PhonePresentFilter, BalanceBandFilter)
    search_fields = ('card_number', 'phone')
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)

    change_list_template = 'admin/card_change_list.html'

    def masked_card_number(self, obj):
        return card_mask(obj.card_number)
    masked_card_number.short_description = 'Card Number'

    def masked_phone(self, obj):
        return phone_mask(obj.phone) if obj.phone else '-'
    masked_phone.short_description = 'Phone'

    def get_urls(self):
        urls = super().get_urls()
        return [
            path('import/', self.import_excel, name='import_excel'),
        ] + urls

    def save_model(self, request, obj, form, change):
        # Normalize manually entered admin data so bot/filters work consistently.
        if obj.card_number:
            obj.card_number = format_card(str(obj.card_number).strip())
        if obj.phone:
            obj.phone = format_phone(str(obj.phone).strip())
        if obj.expire:
            obj.expire = format_expire(str(obj.expire).strip())
        super().save_model(request, obj, form, change)

    def import_excel(self, request):
        if request.method == 'POST':
            form = ImportForm(request.POST, request.FILES)
            if form.is_valid():
                result = import_cards_from_excel(
                    io.BytesIO(request.FILES['excel_file'].read())
                )
                messages.success(request, f"Imported {result['imported']} cards.")
                if result['errors']:
                    for err in result['errors'][:10]:
                        messages.error(request, err)
                return HttpResponseRedirect('../')
        else:
            form = ImportForm()

        return render(request, 'admin/import_form.html', {'form': form})