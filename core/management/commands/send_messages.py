from django.core.management.base import BaseCommand
from core.models import Card
from core.utils import prepare_message, send_message, format_card, format_balance
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send fake messages to filtered cards'

    def add_arguments(self, parser):
        parser.add_argument('--status', type=str, help='Filter by status (active, inactive, expired)')
        parser.add_argument('--min-balance', type=float, help='Minimum balance')
        parser.add_argument('--max-balance', type=float, help='Maximum balance')
        parser.add_argument('--dry-run', action='store_true', help='Preview messages without sending')

    def handle(self, *args, **options):
        queryset = Card.objects.all()

        status = options.get('status')
        if status:
            queryset = queryset.filter(status__iexact=status)

        min_balance = options.get('min_balance')
        if min_balance is not None:
            queryset = queryset.filter(balance__gte=min_balance)

        max_balance = options.get('max_balance')
        if max_balance is not None:
            queryset = queryset.filter(balance__lte=max_balance)

        cards = list(queryset)
        total = len(cards)

        self.stdout.write(f'Found {total} cards to process')

        sent_count = 0
        for card in cards:
            message = prepare_message(card.card_number, card.balance, lang="UZ")
            
            if options.get('dry_run'):
                self.stdout.write(f'[DRY-RUN] Chat ID: {card.phone or "N/A"}')
                self.stdout.write(f'  Message: {message}')
            else:
                result = send_message(message, chat_id=card.phone)
                if result:
                    logger.info(f"Sent to {card.phone}: {message}")
                    sent_count += 1
                    self.stdout.write(f'Sent to {card.phone}: {message[:50]}...')

        if options.get('dry_run'):
            self.stdout.write(self.style.WARNING(f'Dry run complete: {total} messages would be sent'))
        else:
            self.stdout.write(self.style.SUCCESS(f'Successfully sent {sent_count} messages'))