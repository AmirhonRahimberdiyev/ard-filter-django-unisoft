from django.db import models
from django.core.exceptions import BadRequest
# Create your models here.
class Card(models.Model):
    STATUS = [
        ("active","Active"),
        ("inactive","Inactive"),
        ("expired","Expired")

    ]
    card_number = models.PositiveIntegerField(max_length=16)
    expire = models.CharField(max_length=20)
    phone = models.CharField(max_length=20, blank=True, null=True)
    status = models.CharField(max_length=10, choices=STATUS)
    balance = models.DecimalField(max_digits=15, decimal_places=2)

    def __str__(self):
        return self.card_number
    def save(self,*args,**kwargs):
        if Card.card_number < 16:
            return  BadRequest("Card number 16 tista bolishi lozim")
        else:
            return super(Card,self).save(*args,**kwargs)


