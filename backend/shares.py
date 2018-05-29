"""
分享活动的处理
"""
from datetime import timedelta
from dj.utils import api_func_anonymous
from django.db.models import Count, Sum, DateField
from django.db.models.functions import Cast
from django_rq import job

from backend import model_manager, user_factory, remains, dates, api_helper
from backend.loggs import logger
from backend.models import ShareUser
from backend.zhiyue_models import DeviceUser, ShareRewardEvent


@api_func_anonymous
def api_share_stat_weekly(date):
    from_date = dates.get_date(date)
    to_date = from_date + timedelta(7)
    result = ShareUser.objects.filter(created_at__range=(from_date, to_date),
                                      enrolled=1).values(
        'app_id').annotate(referer=Count('referer_id', distinct=True),
                           users=Count('user_id'), remain=Sum('remain'))

    apps = {x.app_id: x.app_name for x in model_manager.get_dist_apps()}
    return [{
        'app_name': apps[x['app_id']][:-3],
        'referer': x['referer'],
        'users': x['users'],
        'remain': x['remain'],
    } for x in result]


@api_func_anonymous
def api_share_stat():
    result = ShareUser.objects.filter(created_at__gt=dates.today() - timedelta(14),
                                      enrolled=1).values(
        'app_id').annotate(referer=Count('referer_id', distinct=True),
                           users=Count('user_id'), remain=Sum('remain'),
                           date=Cast('created_at', DateField())).order_by("-date")

    apps = {x.app_id: x.app_name for x in model_manager.get_dist_apps()}
    return [{
        'app_name': apps[x['app_id']][:-3],
        'referer': x['referer'],
        'users': x['users'],
        'remain': x['remain'],
        'date': x['date'].strftime('%Y-%m-%d')
    } for x in result]


@api_func_anonymous
def api_stat_details(request, date):
    from_date = dates.get_date(date)
    to_date = from_date + timedelta(1)
    app = api_helper.get_session_app(request)
    return [x.json for x in ShareUser.objects.filter(app_id=app, created_at__range=(from_date, to_date), enrolled=1)]


@job
def sync_user(from_time, to_time):
    for app in model_manager.get_dist_apps():
        enrolls = share_enrollments(app.app_id)
        logger.debug('Query device user of %s' % app.app_id)
        new_device_users = model_manager.query(DeviceUser).filter(partnerId=app.app_id, sourceUserId__gt=0,
                                                                  createTime__range=(from_time, to_time))
        logger.debug('Total record %s' % len(new_device_users))
        if len(new_device_users):
            saved = {x.user_id for x in ShareUser.objects.filter(app=app, created_at__gt=(from_time, to_time))}

            for user in new_device_users:
                if user.deviceUserId not in saved:
                    dev_user = user_factory.sync_to_share_dev_user(user)
                    if dev_user.referer_id in enrolls:
                        if enrolls[dev_user.referer_id].createTime < user.createTime:
                            dev_user.enrolled = 1
                    model_manager.save_ignore(dev_user)
                    logger.debug('sync share user %s' % dev_user.user_id)


def share_enrollments(app_id):
    return {x.userId: x for x in model_manager.query(ShareRewardEvent).filter(partnerId=app_id)}


def sync_enrolled():
    for app in model_manager.get_dist_apps():
        enrolls = share_enrollments(app.app_id)
        for dev_user in ShareUser.objects.filter(app=app):
            if dev_user.referer_id in enrolls:
                if enrolls[dev_user.referer_id].createTime < dev_user.created_at:
                    dev_user.enrolled = 1
                    model_manager.save_ignore(dev_user)


def sync_remain():
    pass


def sync_all_remain():
    # all_users = ShareUser.objects.all()
    # classified = remains.classify_users(all_users)

    # 次日
    # 次7日
    for app in model_manager.get_dist_apps():
        remains.remain_obj(ShareUser, app.app_id, (dates.get_date('2018-04-14'), dates.today()))
