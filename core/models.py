# models.py - O'zgarishsiz (avvalgiday)
from django.db import models
import re


class Card(models.Model):
    card_number = models.CharField(max_length=16, unique=True)
    expiry_date = models.DateField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=20, default='active')
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)

    def save(self, *args, **kwargs):
        if self.card_number:
            clean_num = re.sub(r'\D', '', str(self.card_number))
            if len(clean_num) < 16:
                raise ValueError(f"Karta raqami 16 ta raqamdan kam: {len(clean_num)}")
            self.card_number = clean_num
        super().save(*args, **kwargs)

    def __str__(self):
        return str(self.card_number)