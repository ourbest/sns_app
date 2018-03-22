from datetime import timedelta

from dj import times
from django.db import connections

from backend import api_helper, model_manager
from backend.models import AppUser, SnsTask, User
from backend.zhiyue_models import ClipItem, HighValueUser


def to_stat_json(x, item):
    return {
        'id': x.id,
        'title': x.title if x.title else '(无标题)',
        'item_id': x.item_id,
        'deleted': x.delete_flag,
        'category': x.category,
        'url': '/api/url?app=%s&id=%s' % (x.app_id, x.item_id),
        'time': times.to_str(x.started_at, '%H:%M'),
        'date': times.to_str(x.started_at, '%y-%m-%d'),
        'qq_pv': item.qq_pv if item else 0,
        'qq_down': item.qq_down if item else 0,
        'qq_user': item.qq_user if item else 0,
        'wx_pv': item.wx_pv if item else 0,
        'wx_down': item.wx_down if item else 0,
        'wx_user': item.wx_user if item else 0,
        'qq_owners': item.dist_qq_user_count if item else 0,
        'wx_owners': item.dist_wx_user_count if item else 0,
        'wx_devices': item.dist_wx_phone_count if item else 0,
        'qq_devices': item.dist_qq_phone_count if item else 0,
        'qq_groups': item.dist_qun_count if item else 0,
        'qq_users': item.dist_qun_user if item else 0,
    }


def get_count(data, item_id, tp):
    return data.get('%s_%s' % (item_id, 'article%s' % tp), 0) \
           + data.get('%s_%s' % (item_id, 'articlea%s' % tp), 0) \
           + data.get('%s_%s' % (item_id, 'articleb%s' % tp), 0)


def get_item_stat(app_id, item_id, from_time, user_type=0):
    date_end = from_time + timedelta(days=7)
    ids = [x.cutt_user_id for x in AppUser.objects.filter(user__app_id=app_id, type=user_type)]

    query = 'SELECT itemType, count(1) as cnt FROM datasystem_WeizhanItemView ' \
            'WHERE itemId = %s AND shareUserId in (%s) AND time BETWEEN \'%s\' AND \'%s\' ' \
            'GROUP BY itemType' % (
                item_id, ','.join(map(str, ids)), times.to_date_str(from_time),
                times.to_date_str(date_end))
    device_user_query = 'select count(1) as cnt from datasystem_DeviceUser ' \
                        'where sourceItemId = %s and sourceUserId in (%s) ' \
                        'and createTime between \'%s\' AND \'%s\' GROUP BY sourceItemId' % (
                            item_id, ','.join(map(str, ids)), times.to_date_str(from_time),
                            times.to_date_str(date_end))
    data = {}
    if not ids:
        return []

    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            data[row[0]] = row[1]

        cursor.execute(device_user_query)
        rows = cursor.fetchall()
        for row in rows:
            data['du'] = row[0]
    return {
        'weizhan': data.get('article', 0) + data.get('articlea', 0) + data.get('articleb', 0),
        'reshare': data.get('article-reshare', 0) + data.get('articlea-reshare', 0) + data.get('articleb-reshare', 0),
        'download': data.get('article-down', 0) + data.get('articlea-down', 0) + data.get('articleb-down',
                                                                                          0) + data.get(
            'article-mochuang', 0) + data.get('articlea-mochuang', 0) + data.get('articleb-mochuang', 0) + data.get(
            'tongji-down', 0),
        'users': data.get('du', 0),
    }


def get_user_share_stat(date, the_user):
    date_end = date + timedelta(days=7)
    if not the_user:
        return []
    ids = [x.cutt_user_id for x in the_user.appuser_set.filter(type__gte=0)]
    tasks = list(SnsTask.objects.filter(creator=the_user, type_id__in=(5, 3),
                                        started_at__range=(date.date(), date.date() + timedelta(days=1)))
                 .order_by('-started_at'))
    items = {api_helper.parse_item_id(x.data) for x in tasks}

    task_dict = dict()
    items_in_order = []
    for x in tasks:
        item_id = api_helper.parse_item_id(x.data)
        if item_id and item_id not in task_dict:
            task_dict[item_id] = x
            items_in_order.append(item_id)

    # items.update(get_user_share(the_user.app_id, the_user, date))

    items = {x for x in items if x}

    # q = model_manager.query(Weizhan).filter(sourceItemId__in=items,
    #                                            sourceUserId__in=ids).values('sourceItemId',
    #                                                                         'sourceUserId').annotate(
    #     Count('deviceUserId')).order_by('sourceItemId')
    # for x in q:
    #     print(x)
    query = 'SELECT itemId, itemType, count(1) as cnt FROM datasystem_WeizhanItemView ' \
            'WHERE itemId in (%s) AND shareUserId in (%s) AND time BETWEEN \'%s\' AND \'%s\' ' \
            'GROUP BY itemId, itemType' % (
                ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(date),
                times.to_date_str(date_end))
    device_user_query = 'select sourceItemId, count(1) as cnt from datasystem_DeviceUser ' \
                        'where sourceItemId in (%s) and sourceUserId in (%s) ' \
                        'and createTime between \'%s\' AND \'%s\' GROUP BY sourceItemId' % (
                            ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(date),
                            times.to_date_str(date_end))

    data = {}
    if not ids:
        return []
    if items:
        with connections['zhiyue'].cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()
            for row in rows:
                data['%s_%s' % (row[0], row[1])] = row[2]

            cursor.execute(device_user_query)
            rows = cursor.fetchall()
            for row in rows:
                data['%s_du' % (row[0],)] = row[1]

    ret_dict = {str(x.itemId): {
        'name': the_user.name,
        'item_id': x.itemId,
        'time': times.to_str(task_dict.get(str(x.itemId)).started_at, '%H:%M'),
        'date': times.to_str(task_dict.get(str(x.itemId)).started_at, '%y-%m-%d'),
        'title': x.title if x.title else '（无标题）',
        'weizhan': get_count(data, x.itemId, ''),
        'reshare': get_count(data, x.itemId, '-reshare'),
        'download': get_count(data, x.itemId, '-down') + get_count(data, x.itemId, '-mochuang') + data.get(
            '%s_%s' % (x.itemId, 'tongji-down'), 0),
        'users': data.get('%s_du' % x.itemId, 0),
    } for x in ClipItem.objects.using(ClipItem.db_name()).filter(itemId__in=items)}
    return [ret_dict[x] for x in items_in_order if x in ret_dict]


def app_daily_stat(app, date, include_sum=False):
    qq_stats = []
    wx_stats = []
    qq_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
        'uid': 0,
    }

    wx_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
        'uid': 0,
    }
    for user in User.objects.filter(app=app, status=0):
        stats = get_user_stat(date, user)
        qq_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'uid': user.id,
            'name': user.name,
        }

        qq_stats.append(qq_stat)
        wx_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'uid': user.id,
            'name': user.name,
        }

        wx_stats.append(wx_stat)
        for qq in stats:
            stat = qq_stat if qq['type'] == 'QQ' else wx_stat
            sum = qq_sum if qq['type'] == 'QQ' else wx_sum
            stat['share'] += qq['share']
            stat['weizhan'] += qq['weizhan']
            stat['download'] += qq['download']
            stat['reshare'] += qq['reshare']
            stat['users'] += qq['users']

            sum['share'] += qq_stat['share']
            sum['weizhan'] += qq['weizhan']
            sum['download'] += qq['download']
            sum['reshare'] += qq['reshare']
            sum['users'] += qq['users']

    if len(qq_stats) or include_sum:
        qq_stats.append(qq_sum)
        wx_stats.append(wx_sum)
    return {
        'qq': qq_stats,
        'wx': wx_stats,
    }


def get_user_stat(date, the_user):
    if not the_user:
        return []

    cutt_users = list(the_user.appuser_set.filter(type__gte=0))
    cutt_user_dict = {x.cutt_user_id: x for x in cutt_users}

    return [{
        'id': x.userId,
        'name': x.name,
        'type': '微信' if 1 == cutt_user_dict.get(x.userId).type else 'QQ',
        'share': x.shareNum,
        'weizhan': x.weizhanNum,
        'download': x.downPageNum,
        'reshare': x.secondShareNum,
        'users': x.appUserNum,
    } for x in model_manager.query(HighValueUser).filter(partnerId=the_user.app_id, time=date, userType=2,
                                                         userId__in=[x.cutt_user_id for x in cutt_users])]