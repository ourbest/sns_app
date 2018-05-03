"""
分享活动的处理
"""
from django_rq import job

from backend import model_manager, user_factory, remains, dates
from backend.models import ShareUser
from backend.zhiyue_models import DeviceUser, ShareRewardEvent


@job
def sync_user(from_time, to_time):
    for app in model_manager.get_dist_apps():
        enrolls = share_enrollments(app.app_id)
        for user in model_manager.query(DeviceUser).filter(partnerId=app.app_id, sourceUserId__gt=0,
                                                           createTime__range=(from_time, to_time)):
            dev_user = user_factory.sync_to_share_dev_user(user)
            if dev_user.referer_id in enrolls:
                if enrolls[dev_user.referer_id].createTime < user.createTime:
                    dev_user.enrolled = 1
            model_manager.save_ignore(dev_user)


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
