import re
from datetime import datetime
from import_export import resources, fields, widgets
from .models import Card
from .utils import format_card, format_phone, clean_phone_number, clean_card_number, parse_expiry_date


class CleanDecimalWidget(widgets.DecimalWidget):
    def clean(self, value, row=None, **kwargs):
        if value is None or value == '':
            return None
        if isinstance(value, str):
            value = value.replace(',', '').replace(' ', '').replace('\xa0', '')
        return super().clean(value, row=row, **kwargs)


class CardResource(resources.ModelResource):
    id = fields.Field(column_name='id', attribute='id', readonly=True)

    class Meta:
        model = Card
        fields = ('id', 'card_number', 'expiry_date', 'phone', 'status', 'balance')
        import_id_fields = ['card_number']
        skip_unchanged = False
        report_skipped = True

    def get_or_init_instance(self, instance_loader, row):
        card_num = clean_card_number(row.get('card_number', ''))
        if card_num:
            try:
                instance = Card.objects.get(card_number=card_num)
                return instance, False
            except Card.DoesNotExist:
                pass
        return self._meta.model(), True

    def get_or_init_row_instance(self, row, import_validation_errors=None):
        instance, new = self.get_or_init_instance(
            self._meta.resource_instance,
            row
        )
        return instance, new

    def filter_import_data(self, dataset, **kwargs):
        """Filter out invalid rows before import"""
        valid_rows = []
        for row in dataset:
            card_num = clean_card_number(row.get('card_number', ''))
            if card_num:
                valid_rows.append(row)
        return dataset

    def before_import(self, dataset, **kwargs):
        if dataset.headers:
            cleaned_headers = []
            for h in dataset.headers:
                header = str(h).strip()
                header = header.replace('\ufeff', '')
                header = header.replace('\n', '').replace('\r', '')
                cleaned_headers.append(header)
            dataset.headers = cleaned_headers

    def before_import_row(self, row, **kwargs):
        row['card_number'] = clean_card_number(row.get('card_number', ''))
        
        exp = row.get('expiry_date', '')
        if exp:
            row['expiry_date'] = parse_expiry_date(exp)
        
        row['phone'] = clean_phone_number(row.get('phone', ''))
        
        status = str(row.get('status', 'active')).lower().strip()
        if status in ('(empty)', 'none', 'null', '', 'nan'):
            status = 'active'
        row['status'] = status
        
        bal = row.get('balance', 0)
        if bal:
            val = str(bal).replace(',', '').replace(' ', '').replace('\xa0', '')
            if 'E' in val.upper():
                try:
                    val = "{:.2f}".format(float(val))
                except:
                    pass
            row['balance'] = val

    def skip_row(self, instance, original, row, import_validation_errors=None, **kwargs):
        if not row.get('card_number'):
            return True
        return super().skip_row(instance, original, row, import_validation_errors, **kwargs)

    def dehydrate_card_number(self, card):
        return format_card(card.card_number)

    def dehydrate_expiry_date(self, card):
        if card.expiry_date:
            return card.expiry_date.strftime('%m/%y')
        return ''

    def dehydrate_phone(self, card):
        return format_phone(card.phone) if card.phone else ""

    def dehydrate_status(self, card):
        return str(card.status).upper() if card.status else 'ACTIVE'

    def dehydrate_balance(self, card):
        if card.balance is not None:
            return "{:,.2f}".format(float(card.balance)).replace(",", " ")
        return "0.00"