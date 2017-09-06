from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend.models import PhoneDevice, SnsTaskType, App, User, ActiveDevice


def get_phone(label):
    return PhoneDevice.objects.filter(label=label).first()


def get_phones(labels):
    return PhoneDevice.objects.filter(label__in=labels)


def get_task_type(type):
    return SnsTaskType.objects.filter(id=type).first()


def get_app(app_id):
    return App.objects.filter(app_id=app_id).first()


def get_user(email):
    return User.objects.filter(email=email).first()


def get_online(email):
    return ActiveDevice.objects.filter(device__owner__email=email).filter(
        Q(active_at__gt=(timezone.now() - timedelta(seconds=300))) | Q(status=1))


def get_active_device(device):
    return ActiveDevice.objects.filter(device=device).first()
