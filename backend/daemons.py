from datetime import timedelta, datetime

from dj import times
from dj.utils import api_func_anonymous, logger
from django.db.models import Sum
from django.utils import timezone

from backend import api_helper, model_manager, stats, zhiyue
from backend.models import SnsTask, SnsTaskDevice, App, UserDailyStat, AppDailyStat, DailyActive, AppUser, \
    UserDailyResourceStat, SnsUserGroup, DeviceWeixinGroup, SnsApplyTaskLog, SnsGroupLost, DeviceWeixinGroupLost, \
    AppDailyResourceStat, SnsGroup
from backend.zhiyue_models import HighValueUser


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
def save_daily_active():
    daily_stats = zhiyue.do_get_app_stat()
    for daily_stat in daily_stats:
        iphone = int(daily_stat.get('iphone', 0))
        android = int(daily_stat.get('android', 0))
        DailyActive(app_id=daily_stat['app_id'], iphone=iphone,
                    android=android, total=iphone + android).save()


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

    make_resource_stat()


def make_resource_stat():
    today = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    today_range = (today - timedelta(days=1), today)
    for app in App.objects.filter(stage__in=('留守期', '分发期', '准备期')):
        # 记录资源的情况
        users = app.user_set.filter(status=0)
        user_stats = []
        for user in users:
            group_cnt = SnsUserGroup.objects.filter(sns_user__device__owner=user).count()
            group_uniq_cnt = SnsUserGroup.objects.filter(sns_user__device__owner=user).values(
                'sns_group_id').distinct().count()
            wx_group_cnt = DeviceWeixinGroup.objects.filter(device__owner=user).count()
            wx_group_uniq_cnt = DeviceWeixinGroup.objects.filter(device__owner=user).values('name').count()
            qq_apply_cnt = SnsApplyTaskLog.objects.filter(device__owner=user,
                                                          created_at__range=today_range,
                                                          memo__in=('已发送验证', '无需验证已加入')).count()
            qq_lost_cnt = SnsGroupLost.objects.filter(sns_user__owner=user,
                                                      created_at__range=today_range).count()
            wx_lost_cnt = DeviceWeixinGroupLost.objects.filter(device__owner=user,
                                                               created_at__range=today_range).count()

            qq_cnt = SnsTask.objects.filter(creator=user, status=2, started_at__range=today_range, type=3).count()
            wx_cnt = SnsTask.objects.filter(creator=user, status=2, started_at__range=today_range, type=5).count()

            s = UserDailyResourceStat(app=app, user=user, qq_cnt=qq_cnt, wx_cnt=wx_cnt,
                                      phone_cnt=user.phonedevice_set.filter(status=0).count(),
                                      qq_acc_cnt=user.snsuser_set.filter(status=0).count(),
                                      qq_group_cnt=group_cnt, qq_uniq_group_cnt=group_uniq_cnt,
                                      wx_group_cnt=wx_group_cnt, wx_uniq_group_cnt=wx_group_uniq_cnt,
                                      qq_apply_cnt=qq_apply_cnt, qq_lost_cnt=qq_lost_cnt, wx_lost_cnt=wx_lost_cnt)
            s.save()
            user_stats.append(s)

        group_total = SnsGroup.objects.filter(app=app).count()
        group_new = SnsGroup.objects.filter(app=app, created_at__range=today_range).count()
        group_uniq_cnt = SnsUserGroup.objects.filter(sns_user__app=app).values('sns_group_id').distinct().count()
        wx_uniq_cnt = DeviceWeixinGroup.objects.filter(device__owner__app=app).values('name').distinct().count()

        s = AppDailyResourceStat(app=app, qq_cnt=0, wx_cnt=0, phone_cnt=0, qq_acc_cnt=0,
                                 qq_group_cnt=0, qq_uniq_group_cnt=group_uniq_cnt, qq_group_new_cnt=group_new,
                                 wx_group_cnt=0, wx_uniq_group_cnt=wx_uniq_cnt, qq_group_total=group_total,
                                 qq_apply_cnt=0, qq_lost_cnt=0, wx_lost_cnt=0)
        for x in user_stats:
            s.qq_cnt += x.qq_cnt
            s.wx_cnt += x.wx_cnt
            s.phone_cnt += x.phone_cnt
            s.qq_acc_cnt += x.qq_acc_cnt
            s.qq_group_cnt += x.qq_group_cnt
            s.wx_group_cnt += x.wx_group_cnt
            s.qq_apply_cnt += x.qq_apply_cnt
            s.qq_lost_cnt += x.qq_lost_cnt
            s.wx_lost_cnt += x.wx_lost_cnt
        s.save()


@api_func_anonymous
def gauge_data():
    app_ids = [x.app_id for x in App.objects.filter(stage__in=('留守期', '分发期'))]
    cutt_users = {x.cutt_user_id for x in AppUser.objects.filter(type__gte=0)}

    date = times.localtime(datetime.now().replace(hour=0, second=0, minute=0, microsecond=0))

    for stat in model_manager.query(HighValueUser).filter(partnerId__in=app_ids,
                                                          time=date, userType=2,
                                                          userId__in=cutt_users).values('partnerId').annotate(
        pv=Sum('weizhanNum')).annotate(users=Sum('appUserNum')):
        stats.client.gauge('cutt.app%s.sns.pv' % stat['partnerId'], stat['pv'])
        stats.client.gauge('cutt.app%s.sns.users' % stat['partnerId'], stat['users'])
