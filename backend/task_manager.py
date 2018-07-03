from django.utils import timezone
from django.core.cache import cache

from backend import model_manager
from backend.models import SnsTaskDevice, ActiveDevice


def get_working_task(phone_label):
    key = 'task-{}'.format(phone_label)
    value = cache.get(key)
    if not value:
        value = reload_next_task(phone_label)

    if value.device_id:
        return value

    return None


def update_task(phone_label):
    reload_next_task(phone_label)


def reload_next_task(phone_label):
    phone = model_manager.get_phone(phone_label)
    if phone:
        device_task = SnsTaskDevice.objects.filter(device=phone, status=0,
                                                   schedule_at__lte=timezone.now()).first()
    if not device_task:
        device_task = SnsTaskDevice()

    key = 'task-{}'.format(phone_label)
    cache.set(key, device_task, timeout=300)
    return device_task


def mark_task_cancel(phone_label, force=True):
    key = 'flash-%s' % phone_label
    if cache.get(key) != '1' or force:
        cache.set(key, '1', timeout=120)
        for x in SnsTaskDevice.objects.filter(device__label=phone_label, status__in=(1, 10, 11, 12)):
            model_manager.mark_task_cancel(x)


def set_device_active(device, working=0):
    key = 'active-%s' % device.label
    if cache.get(key) != '1':
        cache.set(key, '1', timeout=180)
        ad = model_manager.get_active_device(device)
        if not ad:
            ad = ActiveDevice(device=device, status=working, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = working
        ad.save()
