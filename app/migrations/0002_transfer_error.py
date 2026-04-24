from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("app", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Error",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("code", models.IntegerField(unique=True)),
                ("en", models.CharField(max_length=255)),
                ("ru", models.CharField(max_length=255)),
                ("uz", models.CharField(max_length=255)),
            ],
            options={"ordering": ("code",)},
        ),
        migrations.CreateModel(
            name="Transfer",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("ext_id", models.CharField(max_length=255, unique=True)),
                ("sender_card_number", models.CharField(max_length=32)),
                ("receiver_card_number", models.CharField(max_length=32)),
                ("sender_card_expiry", models.CharField(max_length=5)),
                ("sender_phone", models.CharField(blank=True, max_length=32, null=True)),
                ("receiver_phone", models.CharField(blank=True, max_length=32, null=True)),
                ("sending_amount", models.DecimalField(decimal_places=2, max_digits=18)),
                ("currency", models.PositiveIntegerField()),
                ("receiving_amount", models.DecimalField(decimal_places=2, max_digits=18)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("created", "Created"),
                            ("confirmed", "Confirmed"),
                            ("cancelled", "Cancelled"),
                        ],
                        default="created",
                        max_length=16,
                    ),
                ),
                ("try_count", models.PositiveSmallIntegerField(default=0)),
                ("otp", models.CharField(blank=True, max_length=6)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.AddIndex(
            model_name="transfer",
            index=models.Index(fields=["ext_id"], name="app_transfe_ext_id_0eec4d_idx"),
        ),
        migrations.AddIndex(
            model_name="transfer",
            index=models.Index(fields=["sender_card_number"], name="app_transfe_sender__1d5e24_idx"),
        ),
        migrations.AddIndex(
            model_name="transfer",
            index=models.Index(fields=["receiver_card_number"], name="app_transfe_receive_9978ab_idx"),
        ),
        migrations.AddIndex(
            model_name="transfer",
            index=models.Index(fields=["state"], name="app_transfe_state_87f146_idx"),
        ),
        migrations.AddIndex(
            model_name="transfer",
            index=models.Index(fields=["created_at"], name="app_transfe_created_2bf7d4_idx"),
        ),
    ]
