from collections import defaultdict
from datetime import timedelta

from logzero import logger

from backend import model_manager, hives, cassandras, dates
from backend.models import OfflineUser, ItemDeviceUser, ChannelUser


def remain_week_online(app_id=1564460, date_range=(dates.today() - timedelta(days=14),
                                                   dates.today() - timedelta(days=7))):
    date_users = defaultdict(list)
    remains = ItemDeviceUser.objects.filter(created_at__range=date_range, app_id=app_id)
    for x in remains:
        date_users[dates.get_date(x.created_at)].append(x)

    for k, v in date_users.items():
        users = {x.user_id: x for x in v}
        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(days=7))
        for user_id in remain_ids:
            users[user_id].remain_7 = 1
            model_manager.save_ignore(users[user_id], fields=['remain_7'])

        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(days=8),
                                    to_date=k + timedelta(days=14))
        for user_id in remain_ids:
            users[user_id].remain_14 = 1
            model_manager.save_ignore(users[user_id], fields=['remain_14'])


def remain_week_offline(app_id=1564460, date_range=(dates.today() - timedelta(days=14),
                                                    dates.today() - timedelta(days=7))):
    remains = OfflineUser.objects.filter(created_at__range=date_range, app_id=app_id)
    # if not remains:
    #     zhiyue.sync_offline_from_hive()

    date_users = classify_users(remains)

    for k, v in date_users.items():
        users = {x.user_id: x for x in v}
        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(days=7), device=False)
        OfflineUser.objects.filter(user_id__in=remain_ids).update(remain_7=1)

        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(days=8),
                                    to_date=k + timedelta(days=14),
                                    device=False)
        OfflineUser.objects.filter(user_id__in=remain_ids).update(remain_14=1)


def remain_obj(obj, app_id, date_range=(dates.today() - timedelta(days=14),
                                        dates.today() - timedelta(days=7)), device=True):
    remains = obj.objects.filter(created_at__range=date_range, app_id=app_id, remain=0)
    # if not remains:
    #     zhiyue.sync_offline_from_hive()

    date_users = classify_users(remains)

    for k, v in date_users.items():
        users = {x.user_id: x for x in v}
        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(1), device=device)
        if remain_ids:
            obj.objects.filter(user_id__in=remain_ids).update(remain=1)


def classify_users(remains):
    date_users = defaultdict(list)
    for x in remains:
        date_users[dates.get_date(x.created_at)].append(x)
    return date_users


def get_remain_ids(app_id, ids, date, to_date=None, device=True):
    if len(ids) == 0 or date >= dates.today():
        return list()

    ids = [str(x) for x in ids]

    col = 'deviceuserid' if device else 'userid'
    cursor = hives.hive_cursor()
    try:
        date_str = 'dt = \'%s\'' % date.strftime('%Y-%m-%d') if not to_date else 'dt between \'%s\' and \'%s\'' % (
            date.strftime('%Y-%m-%d'), to_date.strftime('%Y-%m-%d'))

        query = '''select DISTINCT %s from userstartup where partnerid=%s and %s and %s in (%s)''' % (
            col, app_id, date_str, col, ','.join(ids))

        logger.info('hql: %s' % query)

        cursor.execute(query)
        rows = cursor.fetchall()
        logger.info('remain %s' % len(rows))
        return [x[0] for x in rows]
    finally:
        cursor.close()


def sync_remain_week_today():
    pass


def sync_remain_online_rt():
    sync_remain_rt(ItemDeviceUser)

    # from_date = model_manager.today() - timedelta(days=8)
    # user_ids = {x.user_id for x in
    #             ItemDeviceUser.objects.filter(created_at__range=(from_date, from_date + timedelta(days=1)))}
    # ItemDeviceUser.objects.filter(user_id__in=get_last_active_yesterday(user_ids)).update(remain_7=1)
    # early_date = from_date - timedelta(days=7)
    # user_ids = {x.user_id for x in
    #             ItemDeviceUser.objects.filter(created_at__range=(early_date, from_date))}
    # ItemDeviceUser.objects.filter(user_id__in=get_last_active_yesterday(user_ids)).update(remain_14=1)


def sync_remain_offline_rt():
    """
    同步地推7日留存数据
    :return:
    """
    sync_remain_rt(OfflineUser)


def sync_remain_channel_rt():
    sync_remain_rt(ChannelUser)


def sync_remain_rt(obj):
    from_date = dates.today() - timedelta(days=8)
    app_users = classify_app_user(
        obj.objects.filter(created_at__range=(from_date, from_date + timedelta(days=1))))
    for app_id, user_ids in app_users.items():
        remain_ids = get_last_active_yesterday(app_id, user_ids)
        if remain_ids:
            obj.objects.filter(user_id__in=remain_ids).update(remain_7=1)

    # 次周
    early_date = from_date - timedelta(days=7)

    app_users = classify_app_user(
        obj.objects.filter(created_at__range=(early_date, from_date)))
    for app_id, user_ids in app_users.items():
        remain_ids = get_last_active_yesterday(app_id, user_ids)
        if remain_ids:
            obj.objects.filter(user_id__in=remain_ids).update(remain_14=1)


def classify_app_user(users):
    app_users = defaultdict(list)
    for x in users:
        app_users[x.app_id].append(x.user_id)
    return app_users


def get_last_active_yesterday(app_id, ids):
    return cassandras.get_online_ids(app_id, ids, dates.yesterday())
    # return [x['userId'] for x in model_manager.query(ZhiyueUser).filter(userId__in=ids,
    #                                                                     lastActiveTime__range=(
    #                                                                         model_manager.yesterday(),
    #                                                                         model_manager.today())).values('userId')]
