from datetime import timedelta, datetime

from dj import times
from dj.utils import api_func_anonymous, logger
from django.utils import timezone

from backend import api_helper, model_manager, stats
from backend.models import SnsTask, SnsTaskDevice, App, UserDailyStat, AppDailyStat


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


@api_func_anonymous
def daily_stat(date):
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date, '%Y-%m-%d'))

    for app in App.objects.filter(stage__in=('留守期', '分发期')):
        stat = stats.app_daily_stat(app.app_id, date, include_sum=True)
        qq_stat = stat['qq']
        wx_stat = stat['wx']

        for index, qs in enumerate(qq_stat):
            if qs['uid']:
                ws = wx_stat[index]
                UserDailyStat(report_date=date.strftime('%Y-%m-%d'),
                              app=app, user_id=qs['uid'],
                              qq_pv=qs['weizhan'], wx_pv=ws['weizhan'],
                              qq_down=qs['download'], wx_down=ws['download'],
                              qq_install=qs['users'], wx_install=ws['users']).save()
            else:
                ws = wx_stat[index]
                AppDailyStat(report_date=date.strftime('%Y-%m-%d'), app=app,
                             qq_pv=qs['weizhan'], wx_pv=ws['weizhan'],
                             qq_down=qs['download'], wx_down=ws['download'],
                             qq_install=qs['users'], wx_install=ws['users']).save()

    return
