from collections import defaultdict
from datetime import timedelta

from logzero import logger

from backend import model_manager, hives, zhiyue
from backend.models import OfflineUser


def remain_week(app_id=1564460):
    today = model_manager.today()

    date_users = defaultdict(list)
    remains = OfflineUser.objects.filter(
        created_at__range=(today - timedelta(days=14), today - timedelta(days=7)), app_id=app_id, remain=1)
    # if not remains:
    #     zhiyue.sync_offline_from_hive()

    for x in remains:
        date_users[model_manager.get_date(x.created_at)].append(x)

    for k, v in date_users.items():
        users = {x.user_id: x for x in v}
        remain_ids = get_remain_ids(app_id, list(users.keys()), k + timedelta(days=7), device=False)
        for user_id in remain_ids:
            users[user_id].remain_7 = 1

        remain_ids = get_remain_ids(app_id, [str(x) for x in list(users.keys())], k + timedelta(days=8),
                                    to_date=k + timedelta(days=14),
                                    device=False)
        for user_id in remain_ids:
            users[user_id].remain_14 = 1


def get_remain_ids(app_id, ids, date, to_date=None, device=True):
    if len(ids) == 0:
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
        return [x[0] for x in rows]
    finally:
        cursor.close()
