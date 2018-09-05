from datetime import timedelta
from dj.utils import api_func_anonymous, logger
from django.utils import timezone

from backend import api_helper, model_manager, backups
from backend.jobs import do_save_daily_active, do_daily_stat, make_weekly_stat
from backend.models import SnsTask, SnsTaskDevice, WeizhanClick


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
            schedule_at__range=(now - timedelta(minutes=12), now - timedelta(minutes=10)), status=0):
        # 应该开始但是没开始的
        if not model_manager.is_phone_online(task.device):
            logger.warning('任务无法执行%s, 因为手机%s未在线', task.id, task.device.friend_text)
            api_helper.webhook(task, '未能正常执行，请检查手机的在线状态', True)

    return ""


@api_func_anonymous
def save_daily_active():
    do_save_daily_active.delay()


@api_func_anonymous
def daily_stat(date):
    do_daily_stat.delay(date)


@api_func_anonymous
def gauge_data():
    # app_ids = [x.app_id for x in App.objects.filter(stage__in=('留守期', '分发期'))]
    # cutt_users = {x.cutt_user_id for x in AppUser.objects.filter(type__gte=0)}
    #
    # date = times.localtime(datetime.now().replace(hour=0, second=0, minute=0, microsecond=0))
    #
    # for stat in model_manager.query(HighValueUser).filter(partnerId__in=app_ids,
    #                                                       time=date, userType=2,
    #                                                       userId__in=cutt_users).values('partnerId').annotate(
    #     pv=Sum('weizhanNum')).annotate(users=Sum('appUserNum')):
    #     stats.client.gauge('cutt.app%s.sns.pv' % stat['partnerId'], stat['pv'])
    #     stats.client.gauge('cutt.app%s.sns.users' % stat['partnerId'], stat['users'])
    pass


@api_func_anonymous
def weekly_stat():
    make_weekly_stat.delay()


@api_func_anonymous
def backup_weizhan():
    backup_date = WeizhanClick.objects.first().ts
    backups.backup_weizhanclick.delay(backup_date)
