from datetime import timedelta

from dj.utils import api_func_anonymous, logger
from django.utils import timezone

from backend import api_helper, model_manager
from backend.models import SnsTask, SnsTaskDevice


@api_func_anonymous
def check_online_task():
    now = timezone.now()
    for task in SnsTask.objects.filter(schedule_at__lt=now, status=0, started_at__isnull=True):
        device_task = task.snstaskdevice_set.filter(status__gt=0).order_by("-started_at").first()
        if device_task:
            task.status = 1
            task.started_at = device_task.started_at
            task.save()

    for task in SnsTaskDevice.objects.filter(
            schedule_at__range=(now - timedelta(minutes=4), now - timedelta(minutes=2)), status=0):
        # 应该开始但是没开始的
        if not model_manager.is_phone_online(task.device):
            logger.warning('任务无法执行%s, 因为手机%s未在线', task.id, task.device.friend_text)
            api_helper.webhook(task, '未能正常执行，请检查手机的在线状态', True)

    return ""
