from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0002_card_expire_card_phone_alter_card_balance_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='card',
            name='telegram_chat_id',
            field=models.BigIntegerField(
                blank=True,
                help_text='Telegram chat id linked with /link for this card (optional).',
                null=True,
            ),
        ),
    ]
