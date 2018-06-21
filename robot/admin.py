from django.contrib import admin

from robot.models import Keyword


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'created_time')
    ordering = ('-created_time',)
