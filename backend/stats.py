from datetime import timedelta, datetime

from dj import times
from dj.utils import api_func_anonymous
from django.db import connections
from django.template.loader import render_to_string
from django.utils import timezone

from backend import api_helper
from backend import model_manager
from backend.models import SnsTask
from backend.models import User, App
from backend.zhiyue_models import ClipItem
from backend.zhiyue_models import HighValueUser, ShareArticleLog


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
    cutt_users = list(the_user.appuser_set.all())
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


def get_user_share(app_id, user, date):
    uids = {x.cutt_user_id for x in user.appuser_set.all()}

    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id__in=uids, article__partnerId=app_id).filter(time__range=(date.date(),
                                                                         date.date() + timedelta(days=1)))[0:50]

    return {x.article.item_id for x in data if x.article}


@api_func_anonymous
def gen_daily_report():
    yesterday = (datetime.now() - timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    date = times.to_str(yesterday, '%Y-%m-%d')

    # print(yesterday)

    app_stats = []

    for app in App.objects.filter(stage__in=('分发期', '留守期')):
        item_stats = []
        app_stats.append({
            'app': app.app_name,
            'items': item_stats,
            'sum': app_daily_stat(app, date, True),
        })
        for user in app.user_set.filter(status=0):
            item_stats += get_user_share_stat(yesterday, user)
            # sum_stats.append(get_user_stat(date, app.app_id))

    html = render_to_string('daily_report.html', {'stats': app_stats})
    api_helper.send_html_mail('%s线上推广日报' % date, 'yonghui.chen@cutt.com', html)


def get_user_share_stat(date, the_user):
    date_end = date + timedelta(days=3)
    ids = [x.cutt_user_id for x in the_user.appuser_set.all()]
    items = {api_helper.parse_item_id(x.data) for x in
             SnsTask.objects.filter(creator=the_user, type_id=3,
                                    schedule_at__range=(date.date(), date.date() + timedelta(days=1)))}

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
    return [{
        'name': the_user.name,
        'item_id': x.itemId,
        'title': x.title,
        'weizhan': data.get('%s_%s' % (x.itemId, 'article'), 0),
        'reshare': data.get('%s_%s' % (x.itemId, 'article-reshare'), 0),
        'download': data.get('%s_%s' % (x.itemId, 'article-down'), 0) + data.get(
            '%s_%s' % (x.itemId, 'article-mochuang'), 0) + data.get('%s_%s' % (x.itemId, 'tongji-down'), 0),
        'users': data.get('%s_du' % x.itemId, 0),
    } for x in ClipItem.objects.using(ClipItem.db_name()).filter(itemId__in=items)]
