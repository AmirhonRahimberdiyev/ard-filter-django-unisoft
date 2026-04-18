import csv
from django.core.management.base import BaseCommand
from core.models import Card
from core.utils import format_card, format_phone, format_balance


class Command(BaseCommand):
    help = 'Export cards to CSV with optional filters'

    def add_arguments(self, parser):
        parser.add_argument('--status', type=str, help='Filter by status (active, inactive, expired)')
        parser.add_argument('--card-number', type=str, help='Filter by card number (partial)')
        parser.add_argument('--phone', type=str, help='Filter by phone number (partial)')
        parser.add_argument('--output', type=str, default='cards_export.csv', help='Output file path')

    def handle(self, *args, **options):
        queryset = Card.objects.all()

        status = options.get('status')
        if status:
            queryset = queryset.filter(status__iexact=status)

        card_number = options.get('card_number')
        if card_number:
            queryset = queryset.filter(card_number__icontains=card_number.replace(' ', ''))

        phone = options.get('phone')
        if phone:
            clean_phone = ''.join(c for c in phone if c.isdigit())
            queryset = queryset.filter(phone__icontains=clean_phone)

        output_file = options.get('output', 'cards_export.csv')

        total = queryset.count()
        self.stdout.write(f'Found {total} cards to export')

        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['ID', 'Card Number', 'Expiry Date', 'Phone', 'Status', 'Balance'])

            for card in queryset:
                writer.writerow([
                    card.id,
                    format_card(card.card_number),
                    card.expiry_date.strftime('%m/%y') if card.expiry_date else '',
                    format_phone(card.phone) if card.phone else '',
                    card.status.upper(),
                    format_balance(card.balance),
                ])

        self.stdout.write(self.style.SUCCESS(f'Successfully exported to {output_file}'))