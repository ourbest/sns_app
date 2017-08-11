from django.contrib import admin

# Register your models here.
from django.utils.html import format_html

from backend.models import User, PhoneDevice, App, AppUser, SnsUser, SnsGroup


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'created_at')

    ordering = ('-id',)
    search_fields = ('name',)


@admin.register(PhoneDevice)
class PhoneDeviceAdmin(admin.ModelAdmin):
    list_display = ('label', 'phone_num', 'type', 'model', 'owner')


@admin.register(App)
class AppAdmin(admin.ModelAdmin):
    list_display = ('app_id', 'app_name')


@admin.register(AppUser)
class AppUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'memo', 'user')


@admin.register(SnsUser)
class SnsUserAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'login_name', 'owner', 'app')


@admin.register(SnsGroup)
class SnsGroup(admin.ModelAdmin):
    list_display = ('group_id', 'type', 'group_name', 'group_user_count', 'status')
