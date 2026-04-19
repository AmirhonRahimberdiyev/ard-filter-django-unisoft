from django.core.management.base import BaseCommand

from app.services import send_messages_to_cards


class Command(BaseCommand):
    help = 'Send template messages to cards via Telegram (requires chat id per card or --chat-id / settings).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--status',
            type=str,
            default='active',
            help='Filter by status (default: active)',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            default=True,
            help='Log only, no Telegram API calls (default)',
        )
        parser.add_argument(
            '--send',
            action='store_false',
            dest='dry_run',
            help='Call Telegram sendMessage for each row',
        )
        parser.add_argument(
            '--chat-id',
            type=int,
            default=None,
            dest='chat_id',
            help='Override destination when card.telegram_chat_id is empty',
        )

    def handle(self, *args, **options):
        result = send_messages_to_cards(
            status=options.get('status'),
            dry_run=options['dry_run'],
            default_chat_id=options.get('chat_id'),
        )

        mode = 'DRY RUN' if options['dry_run'] else 'SENT'
        self.stdout.write(
            self.style.SUCCESS(f'{mode}: ok={result["sent"]}, failed={result["failed"]}')
        )
        if options['dry_run']:
            self.stdout.write(
                'Tip: /link in the bot stores telegram_chat_id on the card, '
                'or pass --chat-id or set TELEGRAM_DEFAULT_CHAT_ID.'
            )