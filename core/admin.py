# from django.contrib import admin
# from .models import Card
#
#
# @admin.register(Card)
# class CardAdmin(admin.ModelAdmin):
#     list_display = ("card_number", "expire", "phone", "status", "balance")
#     list_filter = ("status", "expire", "phone", "balance")
#     # print("shu ishlayabdi")

from django.contrib import admin
from .models import Card
from import_export.admin import ImportExportModelAdmin

@admin.register(Card)
class BookAdmin(ImportExportModelAdmin):
    pass
