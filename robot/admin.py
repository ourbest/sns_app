from django.contrib import admin

# Register your models here.

from robot.models import *


@admin.register(Area)
class AreaAdmin(admin.ModelAdmin):
    list_display = ('area', 'app', 'isDelete')


@admin.register(Keyword)
class KeywordAdmin(admin.ModelAdmin):
    list_display = ('keyword', 'isDelete')


@admin.register(Search)
class SearchAdmin(admin.ModelAdmin):
    list_display = ('word', 'group_increment', 'status', 'last_time', 'area', 'keyword')


@admin.register(ScheduledTasks)
class ScheduledTasksAdmin(admin.ModelAdmin):
    list_display = ('device', 'type', 'estimated_start_time', 'sns_user')


@admin.register(Config)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ('owner',)


@admin.register(TaskLog)
class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('device', 'type', 'start_time', 'sns_user', 'finish_time', 'status', 'result')
