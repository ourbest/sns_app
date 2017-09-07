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


def mark_task_finish(device_task):
    _set_task_status(device_task, 2)


def mark_task_cancel(device_task):
    _set_task_status(device_task, 3)


def _set_task_status(device_task, status):
    device_task.status = status
    device_task.finish_at = timezone.now()
    device_task.save()
    device_task.device.status = 0
    device_task.device.save()
    check_task_status(device_task.task)


def check_task_status(task):
    in_prog = False
    for x in task.snstaskdevice_set.all():
        if x.status <= 1:
            in_prog = True
            break
    if not in_prog:
        task.status = 2
        task.save()
