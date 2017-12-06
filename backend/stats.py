from datetime import timedelta, datetime

from dj import times
from dj.utils import api_func_anonymous
from django.conf import settings
from django.db import connections, connection
from django.template.loader import render_to_string
from django.utils import timezone

from backend import api_helper
from backend import model_manager
from backend.models import SnsTask, AppUser, DistArticle, DistArticleStat
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


def get_user_share(app_id, user, date):
    uids = {x.cutt_user_id for x in user.appuser_set.filter(type__gte=0)}

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
    api_helper.send_html_mail('%s线上推广日报' % date, settings.DAILY_REPORT_EMAIL, html)


def get_user_share_stat(date, the_user):
    date_end = date + timedelta(days=7)
    if not the_user:
        return []
    ids = [x.cutt_user_id for x in the_user.appuser_set.filter(type__gte=0)]
    tasks = list(SnsTask.objects.filter(creator=the_user, type_id__in=(5, 3),
                                        schedule_at__range=(date.date(), date.date() + timedelta(days=1))))
    items = {api_helper.parse_item_id(x.data) for x in tasks}

    task_dict = dict()
    for x in tasks:
        item_id = api_helper.parse_item_id(x.data)
        if item_id and item_id not in task_dict:
            task_dict[item_id] = x

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
        'time': times.to_str(task_dict.get(str(x.itemId)).started_at, '%H:%M'),
        'date': times.to_str(task_dict.get(str(x.itemId)).started_at, '%y-%m-%d'),
        'title': x.title if x.title else '（无标题）',
        'weizhan': data.get('%s_%s' % (x.itemId, 'article'), 0),
        'reshare': data.get('%s_%s' % (x.itemId, 'article-reshare'), 0),
        'download': data.get('%s_%s' % (x.itemId, 'article-down'), 0) + data.get(
            '%s_%s' % (x.itemId, 'article-mochuang'), 0) + data.get('%s_%s' % (x.itemId, 'tongji-down'), 0),
        'users': data.get('%s_du' % x.itemId, 0),
    } for x in ClipItem.objects.using(ClipItem.db_name()).filter(itemId__in=items)]


@api_func_anonymous
def get_item_stat_values(app):
    """
    统计7天内的文章
    :return:
    """
    item_apps = dict()
    article_dict = dict()
    from_time = timezone.now() - timedelta(days=7)
    query = DistArticle.objects.filter(started_at__gte=from_time)

    if app:
        query = query.filter(app_id=app)
    for item in query:
        if item.app_id not in item_apps:
            item_apps[item.app_id] = list()

        items = item_apps[item.app_id]
        items.append(item.item_id)
        article_dict[item.item_id] = item

    for app_id, items in item_apps.items():
        qq_stats = batch_item_stat(app_id, items, from_time)
        wx_stats = {x['item_id']: x for x in batch_item_stat(app_id, items, from_time, user_type=1)}

        for qq_stat in qq_stats:
            article = article_dict.get(qq_stat['item_id'])
            db = DistArticleStat.objects.filter(article=article).first()
            if not db:
                db = DistArticleStat(article=article)

            db.qq_pv = qq_stat.get('weizhan')
            db.qq_down = qq_stat.get('download')
            db.qq_user = qq_stat.get('users')
            wx_stat = wx_stats.get(article.item_id)
            if wx_stat:
                db.wx_pv = wx_stat.get('weizhan')
                db.wx_down = wx_stat.get('download')
                db.wx_user = wx_stat.get('users')

            user_ids = {x.creator_id for x in article.snstask_set.all()}
            db.dist_user_count = len(user_ids)

            db.save()

    with connection.cursor() as cursor:
        query = '''update backend_distarticlestat s,
(select a.id, count(distinct t.creator_id) owners, count(l.group_id) groups,
 count(distinct d.`device_id`) devices, sum(group_user_count) users
from 
  backend_snsgroup g,
  backend_disttasklog l, backend_snstaskdevice d, 
  backend_snstask t, backend_distarticle a
where g.group_id = l.group_id and success=1 and d.task_id=t.id and l.task_id=t.id and t.article_id=a.id and t.type_id=3
and a.`created_at` > current_date - interval 7 day group by a.id) a
set s.`dist_qq_user_count` = a.owners,
s.`dist_qq_phone_count` = a.devices,
s.`dist_qun_count` = a.groups,
s.dist_qun_user = a.users
where s.`article_id` = a.id
'''
        cursor.execute(query)

        query = '''update backend_distarticlestat s,
(select a.id, count(distinct t.creator_id) owners, count(distinct d.`device_id`) devices
from backend_snstaskdevice d, 
  backend_snstask t, backend_distarticle a
where d.task_id = t.id and t.article_id=a.id and t.type_id=5
and a.`created_at` > current_date - interval 7 day group by a.id) a
set s.dist_wx_user_count = a.owners,
s.dist_wx_phone_count = devices
where s.article_id=a.id'''

        cursor.execute(query)


def batch_item_stat(app_id, items, from_time, user_type=0):
    date_end = from_time + timedelta(days=7)
    ids = [x.cutt_user_id for x in AppUser.objects.filter(user__app_id=app_id, type=user_type)]
    query = 'SELECT itemId, itemType, count(1) as cnt FROM datasystem_WeizhanItemView ' \
            'WHERE itemId in (%s) AND shareUserId in (%s) AND time BETWEEN \'%s\' AND \'%s\' ' \
            'GROUP BY itemId, itemType' % (
                ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(from_time),
                times.to_str(date_end, '%Y-%m-%d %H:%M:%S'))
    device_user_query = 'select sourceItemId, count(1) as cnt from datasystem_DeviceUser ' \
                        'where sourceItemId in (%s) and sourceUserId in (%s) ' \
                        'and createTime between \'%s\' AND \'%s\' GROUP BY sourceItemId' % (
                            ','.join(map(str, items)), ','.join(map(str, ids)), times.to_date_str(from_time),
                            times.to_date_str(date_end, '%Y-%m-%d %H:%M:%S'))
    data = dict()
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
        'item_id': x,
        'weizhan': data.get('%s_%s' % (x, 'article'), 0),
        'reshare': data.get('%s_%s' % (x, 'article-reshare'), 0),
        'download': data.get('%s_%s' % (x, 'article-down'), 0) + data.get(
            '%s_%s' % (x, 'article-mochuang'), 0) + data.get('%s_%s' % (x, 'tongji-down'), 0),
        'users': data.get('%s_du' % x, 0),
    } for x in items]


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
        'weizhan': data.get('article', 0),
        'reshare': data.get('article-reshare', 0),
        'download': data.get('article-down', 0) + data.get('article-mochuang', 0) + data.get('tongji-down', 0),
        'users': data.get('du', 0),
    }


@api_func_anonymous
def team_articles(request, i_page, i_size, url):
    item_id = None
    if url:
        item_id = api_helper.parse_item_id(url)

    size = i_size if i_size else 50
    offset = (i_page - 1) * size if i_page else 0
    app = api_helper.get_session_app(request)
    if not item_id:
        articles = DistArticle.objects.filter(app_id=app).order_by("-started_at")[offset:size + offset]
        total = DistArticle.objects.filter(app_id=app).count()
    else:
        articles = DistArticle.objects.filter(app_id=app, item_id=item_id)
        total = len(articles)

    stat_data = {x.article_id: x for x in DistArticleStat.objects.filter(article_id__in=[x.id for x in articles])}

    return {
        'total': total,
        'items': [to_stat_json(x, stat_data.get(x.id)) for x in articles]
    }


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
