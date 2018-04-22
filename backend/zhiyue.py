import re
from collections import defaultdict
from datetime import datetime, timedelta

from dj import times
from dj.utils import api_func_anonymous
from django.db import connections
from django.db.models import Count, Sum
from django.http import HttpResponse
from django.utils import timezone
from django_rq import job
from logzero import logger

import backend.dates
import backend.stat_utils
from backend import api_helper, model_manager, stat_utils, hives, remains, cassandras
from backend.api_helper import get_session_app
from backend.daily_stat import make_daily_remain, save_bonus_info, make_offline_stat, \
    do_offline_stat
from backend.models import AppUser, AppDailyStat, UserDailyStat, App, DailyActive, ItemDeviceUser, UserDailyDeviceUser, \
    User, OfflineUser, ChannelUser
from backend.user_factory import sync_to_channel_user, sync_to_item_dev_user
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, AdminPartnerUser, CouponInst, ItemMore, \
    ZhiyueUser, AppConstants, CouponDailyStatInfo, OfflineDailyStat, DeviceUser, \
    CouponLog


@api_func_anonymous
def user_share(i_uid, request):
    """
    获取用户分享的文章记录
    :param i_uid:
    :param request:
    :return:
    """
    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id=i_uid, article__partnerId=get_session_app(request)).order_by("-time")[0:50]

    return [{
        'text': x.text,
        'time': times.to_str(x.time),
        'name': x.user.name,
        'url': find_url(x) if x.article else '',
        'itemId': x.article.item_id if x.article else 0,
        'clipId': x.article.item.clipId if x.article else 0,
        'title': x.article.item.title if x.article else '',
    } for x in data]


@api_func_anonymous
def messages():
    data = model_manager.query(AppConstants).filter(constType='pushmessage')
    return [{'constId': x.constId, 'constName': x.constName, 'memo': x.memo} for x in data]


@api_func_anonymous
def message_save(constId, constName):
    db = AppConstants.objects.using('zhiyue_rw').filter(constType='pushmessage', constId=constId).first()
    if db:
        db.constName = constName
        db.save()


def get_user_share_items(app_id, uids):
    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id__in=uids, article__partnerId=app_id).order_by("-time")[0:50]


def find_url(x):
    """
    还原文章的链接
    :param x:
    :return:
    """
    # url = re.findall('https?://.+/weizhan/article/\d+/\d+/\d+', text)
    # return url[0] if url else ''
    return 'http://www.cutt.com/weizhan/article/%s/%s/%s' % (
        x.article.item.clipId, x.article.item_id, x.article.partnerId)


@api_func_anonymous
def get_url_title(url):
    """
    获取文章标题/分享文案
    :param url:
    :return:
    """
    u = re.findall('https?://.+/weizhan/article/\d+/(\d+)/(\d+)', url)
    if u:
        (article_id, app_id) = u[0]
        more = model_manager.query(ItemMore).filter(itemId=article_id, appId=app_id).first()
        if more and more.title:
            return more.title
        item = model_manager.query(ClipItem).filter(itemId=article_id).first()
        return item.title if item and item.title else '(无标题)'
    return None


@api_func_anonymous
def count_weizhan(email, request):
    the_user = api_helper.get_login_user(request, email)
    cutt_users = [the_user.appuser_set.all()]
    model_manager.query(WeizhanCount)
    pass


@api_func_anonymous
def count_user_sum(email, date, request):
    """
    用户数据
    :param email:
    :param date:
    :param request:
    :return:
    """
    date = backend.dates.get_date(date)
    the_user = api_helper.get_login_user(request, email)
    return backend.stat_utils.get_user_stat(date, the_user)


@api_func_anonymous
def get_user_majia(email, request):
    """
    获取用户的马甲列表
    :param email:
    :param request:
    :return:
    """
    user = api_helper.get_login_user(request, email)
    if not user:
        return []

    cutt = {x.user_id: x.user.name for x in model_manager.query(AdminPartnerUser).select_related('user')
        .filter(loginUser=user.email, partnerId=get_session_app(request))}

    for x in user.appuser_set.filter(type__gte=0):
        if x.cutt_user_id in cutt:
            if x.name != cutt[x.cutt_user_id]:
                x.name = cutt[x.cutt_user_id]
                x.save()
            del cutt[x.cutt_user_id]

    for k, v in cutt.items():
        AppUser(user=user, name=v if v else k, type=2, cutt_user_id=k).save()

    return [{
        'id': x.cutt_user_id,
        'name': x.name,
        'type': x.type,
    } for x in user.appuser_set.filter(type__gte=0)]


@api_func_anonymous
def sum_team_dist(date, request, include_sum):
    """
    小组分发情况
    :param date:
    :param request:
    :param include_sum:
    :return:
    """
    app = get_session_app(request)
    date = backend.dates.get_date(date)
    return backend.stat_utils.app_daily_stat(app, date, include_sum)


def show_open_link(request):
    url = request.GET.get('url')

    if not url:
        url = 'comcuttapp965004://article?id=31412177424'
    else:
        info = re.findall(r'https?://.+?/weizhan/article/\d+/(\d+)/(\d+)', url)
        if info:
            [(aid, app)] = info
            url = 'comcuttapp%s://article?id=%s' % (app, aid)

    return HttpResponse('<a style="font-size: 10em" href="%s">open</a>' % url)


@api_func_anonymous
def app_report(from_date, to_date, i_app):
    if not from_date or not to_date:
        return

    return [{
        'date': x.report_date,
        'qq_pv': x.qq_pv,
        'qq_down': x.qq_down,
        'qq_install': x.qq_install,
        'wx_pv': x.wx_pv,
        'wx_down': x.wx_down,
        'wx_install': x.wx_install,
    } for x in AppDailyStat.objects.filter(report_date__range=(from_date, to_date), app_id=i_app).order_by("-pk")]


@api_func_anonymous
def app_report_user(from_date, to_date):
    if not from_date or not to_date:
        return

    return [{
        'date': x.report_date,
        'app': x.app.app_name,
        'name': x.user.name,
        'qq_pv': x.qq_pv,
        'qq_down': x.qq_down,
        'qq_install': x.qq_install,
        'wx_pv': x.wx_pv,
        'wx_down': x.wx_down,
        'wx_install': x.wx_install,
    } for x in UserDailyStat.objects.filter(report_date__range=(from_date,
                                                                to_date)).select_related('app', 'user').order_by("-pk")]


@api_func_anonymous
def get_app_stat():
    return do_get_app_stat()


@api_func_anonymous
def get_stat_before_days(i_days):
    if not i_days:
        i_days = 1

    cnt = model_manager.get_dist_apps().count()

    return sorted([{
        'app_id': x.app.app_id,
        'app_name': x.app.app_name,
        'iphone': x.iphone,
        'android': x.android,
    } for x in
        DailyActive.objects.filter(created_at__lt=timezone.now() - timedelta(days=i_days)).select_related(
            "app").order_by(
            "-pk")[:cnt]], key=lambda x: x['app_id'])


@api_func_anonymous
def get_active_detail(app_id, i_today):
    query = DailyActive.objects.filter(app_id=app_id).extra(
        where=[
            'created_at>current_date' if i_today == 1
            else 'created_at between current_date - interval 1 day and current_date'
        ])

    return [{
        'time': times.to_str(x.created_at, '%H:%M'),
        'iphone': x.iphone,
        'android': x.android,
        'total': x.total
    } for x in query]


def do_get_app_stat():
    apps = {str(x.app_id): x.app_name for x in model_manager.get_dist_apps()}
    query = '''
        select appId,platform,count(*) from pojo_ZhiyueUser where platform in (%s)
         and appId in (%s)
         and lastActiveTime > current_date
        group by appId, platform
    ''' % ('\'iphone\', \'android\'', ','.join(apps.keys()))
    data = []

    values = dict()
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            sum = values.get(row[0])
            if not sum:
                sum = {
                    'app_id': row[0],
                    'app_name': apps[row[0]][:-3],
                }
                values[row[0]] = sum
                data.append(sum)

            sum['%s' % row[1]] = row[2]

    return sorted(data, key=lambda x: int(x['app_id']))


@api_func_anonymous
def get_new_device():
    apps = {str(x.app_id): x.app_name for x in model_manager.get_dist_apps()}
    query = '''
        select appId,platform,count(*) from pojo_ZhiyueUser where platform in (%s)
         and appId in (%s)
         and createTime > current_date
        group by appId, platform
    ''' % ('\'iphone\', \'android\'', ','.join(apps.keys()))
    data = []

    values = dict()
    online = {x['app_id']: x['total'] for x in
              ItemDeviceUser.objects.filter(created_at__gt=backend.dates.today()).values(
                  'app_id').annotate(total=Count('user_id'))}

    offline = {x['app_id']: x['total'] for x in OfflineUser.objects.filter(created_at__gt=backend.dates.today()).values(
        'app_id').annotate(total=Count('user_id'))}

    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            sum = values.get(row[0])
            if not sum:
                sum = {
                    'app_id': row[0],
                    'app_name': apps[row[0]][:-3],
                    'online': online.get(int(row[0]), 0),
                    'offline': offline.get(int(row[0]), 0),
                }
                values[row[0]] = sum
                data.append(sum)

            sum['%s' % row[1]] = row[2]
            # stats.client.gauge('cutt.app%s.new.%s' % (row[0], row[1]), row[2])

    return sorted(data, key=lambda x: int(x['app_id']))


@api_func_anonymous
def get_offline_ids(request, date):
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    app = api_helper.get_session_app(request)

    # today = timezone.now().date()
    query = model_manager.query(CouponInst).filter(partnerId=app, status=1,
                                                   useDate__range=(date, date + timedelta(days=1)))
    return [x.userId for x in query] if app else ""


@api_func_anonymous
def get_coupon_message_details():
    query = 'SELECT (userId % 2) AS g, message, count(*), status, type FROM partner_CouponPmSentInfo ' \
            'WHERE createTime > current_date - INTERVAL 1 DAY GROUP BY message, userId % 2, status, type'

    ret = []
    values = {}
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [group, message, cnt, status, type] in rows:
            key = '%s_%s_%s' % (group, message, type)
            row = values.get(key)
            if not row:
                row = {'group': group, 'message': message, 'total': 0, 'type': type, 'open': 0}
                ret.append(row)
                values[key] = row

            row['total'] += cnt
            if status:
                row['open'] = cnt

    return ret


@api_func_anonymous
def get_coupon_details(date, save):
    date = backend.dates.get_date(date)
    yesterday = date - timedelta(days=1)
    apps = {x.app_id: x.app_name for x in App.objects.filter(offline=1)}

    remain_rates = dict()

    query = OfflineUser.objects.filter(created_at__range=(date, date + timedelta(1))).values('app_id').annotate(
        total=Count('user_id'), viewed=Sum('bonus_view'), picked=Sum('bonus_pick'), remain=Sum('remain'))

    for u in OfflineUser.objects.filter(created_at__range=(yesterday, date)).values(
            'app_id').annotate(total=Count('user_id'), remain=Sum('remain')):
        remain_rates[u['app_id']] = int(u['remain'] / u['total'] * 100)

    ret = [{'app_id': x['app_id'], 'app_name': apps[x['app_id']][:-3], 'today': x['total'],
            'remain': '%s%%' % remain_rates[x['app_id']],
            'today_remain': '%s%%' % int(x['remain'] / x['total'] * 100),
            'open': x['viewed'],
            'picked': x['picked']} for x in query]
    if save:
        for x in ret:
            info = CouponDailyStatInfo(partnerId=x['app_id'], statDate=date,
                                       total=x['today'], active=x['picked'],
                                       open=x['open'], remainDay=x['remain'][:-1])
            info.save(using='partner_rw')
    return ret


@api_func_anonymous
def make_offline(the_date):
    do_offline_stat.delay(the_date)
    return "ok"


@api_func_anonymous
def make_offline_remain(the_date):
    make_offline_stat.delay(the_date)


@api_func_anonymous
def make_offline_days(days):
    if not days:
        days = 10
    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])
    query = '''
        SELECT date(useDate), partnerId, count(*) FROM partner_CouponInst 
    WHERE useDate BETWEEN current_date - INTERVAL %s DAY AND current_date AND 
    partnerId IN (%s) GROUP BY partnerId, date(useDate)
    ''' % (days, ids)

    # 使用量
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [day, app_id, cnt] in rows:
            try:
                OfflineDailyStat(app_id=app_id, stat_date=day, user_num=cnt).save()
            except:
                pass


@api_func_anonymous
def get_offline_detail(the_date):
    stat_date = timezone.now()

    if the_date:
        stat_date = timezone.make_aware(datetime.strptime(the_date, '%Y-%m-%d'))

    return [{
        'app_id': x.app_id,
        'stat_date': x.stat_date,
        'user_num': x.user_num,
        'user_cost': x.user_cost,
        'total_cost': x.total_cost,
        'bonus_cost': x.bonus_cost,
        'user_bonus_num': x.user_bonus_num,
        'remain': x.remain,
    } for x in OfflineDailyStat.objects.filter(stat_date=times.to_date_str(stat_date - timedelta(days=2),
                                                                           "%Y-%m-%d"))]


@api_func_anonymous
def sync_user():
    sync_device_user.delay()


@api_func_anonymous
def sync_user_realtime():
    sync_recent_user.delay()


@api_func_anonymous
def sync_pv():
    stat_utils.sync_item_stat.delay()


@job
def sync_recent_user():
    """
    同步最新的用户数据
    :return:
    """
    logger.info('同步最新数据')
    minutes = 30
    sync_user_in_minutes(minutes)
    save_bonus_info()
    sync_online_remain()
    sync_offline_remain()
    sync_channel_remain()


@job
def sync_user_in_minutes(minutes):
    for app in model_manager.get_dist_apps():
        majias = {x.cutt_user_id: x for x in AppUser.objects.filter(type__in=(0, 1), user__app=app, user__status=0)}
        qq_user_ids = []
        wx_user_ids = []
        if majias:
            saved = {x.user_id for x in
                     ItemDeviceUser.objects.filter(app=app, created_at__gt=timezone.now() - timedelta(
                         minutes=minutes))}

            ids_map = defaultdict(dict)
            for device_user in model_manager.query(DeviceUser).filter(sourceUserId__in=majias.keys(),
                                                                      createTime__gt=timezone.now() - timedelta(
                                                                          minutes=minutes)):
                majia = majias.get(device_user.sourceUserId)
                owner = majia.user
                if device_user.deviceUserId not in saved:
                    model_manager.save_ignore(sync_to_item_dev_user(app, owner, device_user, majia))
                (wx_user_ids if majia.type else qq_user_ids).append(device_user.deviceUserId)

                ids_map_owner = ids_map[owner]
                if len(ids_map_owner) == 0:
                    ids_map_owner[0] = list()
                    ids_map_owner[1] = list()

                if majia.type in ids_map_owner:
                    ids_map_owner[majia.type].append(device_user.deviceUserId)

        if app.offline:
            coupons = model_manager.query(CouponInst).filter(partnerId=app.pk, status=1,
                                                             useDate__gt=timezone.now() - timedelta(minutes=minutes))
            save_coupon_user(coupons)

        sync_channel_user_in_minutes(minutes)


def sync_channel_user_in_minutes(minutes):
    for app in model_manager.get_dist_apps():
        query = ChannelUser.objects.filter(app=app)
        if minutes > 0:
            query = query.filter(created_at__gt=timezone.now() - timedelta(minutes=minutes * 2))
        else:
            query = query.filter(created_at__range=(backend.dates.yesterday(), backend.dates.today()))

        saved = {x.user_id for x in query}

        user_query = model_manager.query(ZhiyueUser).filter(
            platform='android', appId=str(app.app_id)).exclude(source__isnull=True, source='')
        if minutes > 0:
            user_query = user_query.filter(createTime__gt=timezone.now() - timedelta(minutes=minutes))
        else:
            user_query = user_query.filter(createTime__range=(backend.dates.yesterday(), backend.dates.today()))

        users = user_query

        user_dict = {x.userId: x for x in users}

        for device_user in model_manager.query(DeviceUser).filter(deviceUserId__in=[x.userId for x in users]):
            if device_user.deviceUserId not in saved:
                model_manager.save_ignore(sync_to_channel_user(user_dict[device_user.deviceUserId], device_user))


def sync_channel_remain(date=0):
    _sync_remain(ChannelUser, date)


def _sync_remain(obj, date=0):
    today = backend.dates.today()
    if date:
        today = today + timedelta(date)
    yesterday = today - timedelta(1)

    for app in model_manager.get_dist_apps():
        ids = [x.user_id for x in
               obj.objects.filter(app=app, created_at__range=(yesterday, today), remain=0)]
        if not ids:
            continue

        # remains_ids = [x.userId for x in
        #                model_manager.query(ZhiyueUser).filter(userId__in=ids, lastActiveTime__gt=today)]
        remains_ids = cassandras.get_online_ids(app.app_id, ids, today)
        if remains_ids:
            obj.objects.filter(user_id__in=remains_ids, app=app, remain=0).update(remain=1)


def _sync_app_remain(obj, app, date=0):
    today = backend.dates.today()
    if date:
        today = today + timedelta(date)
    yesterday = today - timedelta(1)
    ids = [x.user_id for x in
           obj.objects.filter(app=app, created_at__range=(yesterday, today), remain=0)]

    if not ids:
        return

    remains_ids = cassandras.get_online_ids(app.app_id, ids, today) if date else \
        [x.userId for x in
         model_manager.query(ZhiyueUser).filter(userId__in=ids, lastActiveTime__gt=today)]
    if remains_ids:
        obj.objects.filter(user_id__in=remains_ids, app=app, remain=0).update(remain=1)


def save_coupon_user(coupons, saved=None):
    for coupon in coupons:
        if saved is None or coupon.userId not in saved:
            log = model_manager.query(CouponLog).filter(appId=coupon.partnerId, couponId=coupon.couponId,
                                                        num=coupon.couponNum, lbs__isnull=False).first()
            offline_user = OfflineUser(user_id=coupon.userId, app_id=coupon.partnerId, owner=coupon.shopOwner,
                                       created_at=coupon.useDate)
            if log:
                offline_user.location = log.lbs
            model_manager.save_ignore(offline_user)


@job
def sync_device_user():
    logger.info('同步用户数据')
    stat_date = datetime.now()
    from_date = stat_date - timedelta(days=1)
    date_range = (from_date.strftime('%Y-%m-%d'), stat_date.strftime('%Y-%m-%d'))
    for app in model_manager.get_dist_apps():
        majias = {x.cutt_user_id: x for x in AppUser.objects.filter(type__in=(0, 1), user__app=app, user__status=0)}
        qq_user_ids = []
        wx_user_ids = []
        if majias:
            saved = {x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=date_range)}
            ids_map = defaultdict(dict)
            for device_user in model_manager.query(DeviceUser).filter(sourceUserId__in=majias.keys(),
                                                                      createTime__range=date_range):
                majia = majias.get(device_user.sourceUserId)
                owner = majia.user
                if device_user.deviceUserId not in saved:
                    model_manager.save_ignore(sync_to_item_dev_user(app, owner, device_user, majia))
                (wx_user_ids if majia.type else qq_user_ids).append(device_user.deviceUserId)

                ids_map_owner = ids_map[owner]
                if len(ids_map_owner) == 0:
                    ids_map_owner[0] = list()
                    ids_map_owner[1] = list()

                if majia.type in ids_map_owner:
                    ids_map_owner[majia.type].append(device_user.deviceUserId)

            for k, v in ids_map.items():
                model_manager.save_ignore(
                    UserDailyDeviceUser(report_date=from_date.strftime('%Y-%m-%d'), app=app, user=k,
                                        qq_user_ids=','.join([str(x) for x in v[0]]),
                                        wx_user_ids=','.join([str(x) for x in v[1]])))

        if app.offline:
            coupons = model_manager.query(CouponInst).filter(partnerId=app.pk, status=1, useDate__range=date_range)
            today_saved = OfflineUser.objects.filter(app=app, created_at__range=date_range)
            saved = {x.user_id for x in today_saved}

            if len(saved) != coupons.count():
                save_coupon_user(coupons, saved)

        sync_channel_user_in_minutes(0)

        # 获取领红包信息
    save_bonus_info(backend.dates.today())

    sync_remain()


def sync_remain():
    logger.info('同步留存数据')
    to_time = datetime.now()
    report_date = (to_time - timedelta(days=2)).strftime('%Y-%m-%d')  # 留存记录是针对前一天的
    for app in model_manager.get_dist_apps():
        _sync_app_remain(ItemDeviceUser, app, -1)
        make_daily_remain(app.app_id, report_date)
        _sync_app_remain(ChannelUser, app, -1)

        if app.offline:
            _sync_app_remain(OfflineUser, app, -1)

    remains.sync_remain_offline_rt()
    remains.sync_remain_online_rt()
    remains.sync_remain_channel_rt()


def sync_online_remain(date=0):
    _sync_remain(ItemDeviceUser, date)


def sync_offline_remain(date=0):
    _sync_remain(OfflineUser, date)


def sync_report_online_remain(report):
    from_time_str = report.report_date
    to_time_str = times.to_str(datetime.strptime(from_time_str, '%Y-%m-%d') + timedelta(days=1), '%Y-%m-%d')
    date_range = (from_time_str, to_time_str)
    qq_cnt = ItemDeviceUser.objects.filter(app=report.app, created_at__range=date_range, remain=1, type=0).count()
    wx_cnt = ItemDeviceUser.objects.filter(app=report.app, created_at__range=date_range, remain=1, type=1).count()
    report.qq_remain = qq_cnt
    report.wx_remain = wx_cnt
    model_manager.save_ignore(report)


def sync_remain_at(report_date):
    date_range = (report_date, '%s 23:59:59' % report_date)
    for app in model_manager.get_dist_apps():
        for user in User.objects.filter(app=app, status=0):
            qq_cnt = ItemDeviceUser.objects.filter(app=app, owner=user, created_at__range=date_range, remain=1,
                                                   type=0).count()
            wx_cnt = ItemDeviceUser.objects.filter(app=app, owner=user, created_at__range=date_range, remain=1,
                                                   type=1).count()
            UserDailyStat.objects.filter(report_date=report_date, user=user).update(
                qq_remain=qq_cnt, wx_remain=wx_cnt)

        qq_cnt = ItemDeviceUser.objects.filter(app=app, created_at__range=date_range, remain=1,
                                               type=0).count()
        wx_cnt = ItemDeviceUser.objects.filter(app=app, created_at__range=date_range, remain=1,
                                               type=1).count()
        AppDailyStat.objects.filter(report_date=report_date, app=app).update(
            qq_remain=qq_cnt, wx_remain=wx_cnt)


@job("default", timeout=600)
def sync_online_from_hive(the_date):
    to_time = datetime.strptime(the_date, '%Y-%m-%d')
    next_day = (to_time + timedelta(days=1)).strftime('%Y-%m-%d')
    create_range = (to_time, next_day)
    cursor = hives.hive_cursor()
    try:
        for app in App.objects.filter(stage__in=('分发期', '留守期')):
            ids = [x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=create_range, remain=0)]
            if ids:
                print('%s total %s' % (app.app_id, len(ids)))
                query = """
                select DISTINCT deviceuserid from userstartup where partnerid=%s and dt = '%s' and deviceuserid in (%s)
                """ % (str(app.app_id), next_day, ','.join([str(x) for x in ids]))
                cursor.execute(query)
                rows = cursor.fetchall()
                print('remain %s' % len(rows))
                ItemDeviceUser.objects.filter(app=app, created_at__range=create_range, remain=0,
                                              user_id__in=[x[0] for x in rows]).update(remain=1)
    finally:
        cursor.close()


@job("default", timeout=600)
def sync_offline_from_hive(the_date):
    to_time = datetime.strptime(the_date, '%Y-%m-%d')
    next_day = (to_time + timedelta(days=1)).strftime('%Y-%m-%d')
    create_range = (to_time, next_day)
    cursor = hives.hive_cursor()
    try:
        for app in model_manager.get_dist_apps():
            ids = [x.user_id for x in OfflineUser.objects.filter(app=app, created_at__range=create_range, remain=0)]
            if ids:
                query = """
                select DISTINCT userid from userstartup where partnerid=%s and dt = '%s' and userid in (%s)
                """ % (str(app.app_id), next_day, ','.join([str(x) for x in ids]))
                cursor.execute(query)
                rows = cursor.fetchall()
                OfflineUser.objects.filter(app=app, created_at__range=create_range, remain=0,
                                           user_id__in=[x[0] for x in rows]).update(remain=1)
    finally:
        cursor.close()


def get_users(ids):
    return model_manager.query(ZhiyueUser).filter(userId__in=ids)
