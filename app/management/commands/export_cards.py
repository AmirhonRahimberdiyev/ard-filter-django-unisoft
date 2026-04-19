from django.core.management.base import BaseCommand
from app.services import export_cards_to_csv


class Command(BaseCommand):
    help = 'Export cards to CSV with optional filters'

    def add_arguments(self, parser):
        parser.add_argument('--status', type=str, help='Filter by status (active, inactive, expired)')
        parser.add_argument('--card-number', type=str, help='Filter by card number (partial match)')
        parser.add_argument('--phone', type=str, help='Filter by phone (partial match)')
        parser.add_argument('--output', type=str, default='cards_export.csv', help='Output file path')

    def handle(self, *args, **options):
        count = export_cards_to_csv(
            file_path=options['output'],
            status=options.get('status'),
            card_number=options.get('card_number'),
            phone=options.get('phone')
        )
        self.stdout.write(self.style.SUCCESS(f'Exported {count} cards to {options["output"]}'))