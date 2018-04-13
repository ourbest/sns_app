import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

from dj import times
from dj.utils import api_func_anonymous
from django.db import connections
from django.db.models import Count, Sum, Max
from django.http import HttpResponse
from django.utils import timezone
from django_rq import job
from logzero import logger

import backend.stat_utils
from backend import api_helper, model_manager, stat_utils
from backend.api_helper import get_session_app
from backend.models import AppUser, AppDailyStat, UserDailyStat, App, DailyActive, ItemDeviceUser, UserDailyDeviceUser, \
    User, OfflineUser
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, AdminPartnerUser, CouponInst, ItemMore, \
    ZhiyueUser, UserRewardHistory, AppConstants, CouponPmSentInfo, CouponDailyStatInfo, OfflineDailyStat, DeviceUser, \
    CouponLog, UserRewardGroundHistory, WithdrawApply


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
    date = model_manager.get_date(date)
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
    date = model_manager.get_date(date)
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
                    'app_name': apps[row[0]],
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
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            sum = values.get(row[0])
            if not sum:
                sum = {
                    'app_id': row[0],
                    'app_name': apps[row[0]],
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
def get_coupon_details(save):
    date = times.localtime(datetime.now().replace(hour=0, second=0, minute=0, microsecond=0))
    yesterday = date - timedelta(days=1)
    apps = {x.app_id: x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}

    query = model_manager.query(CouponInst).filter(partnerId__in=apps.keys(), status=1,
                                                   useDate__range=(date, date + timedelta(days=1))).values(
        'partnerId').annotate(total=Count('userId')).order_by('-total')

    ids = [x['partnerId'] for x in query]

    rates = dict()
    remains = dict()
    picked_remains = dict()
    picked_rates = dict()
    others_remains = dict()
    others_rates = dict()

    actives = {x['partnerId']: x['total'] for x in
               model_manager.query(CouponPmSentInfo).filter(partnerId__in=apps.keys(), status=1,
                                                            createTime__gt=date).values('partnerId').annotate(
                   total=Count('userId'))}

    reward_query = model_manager.query(UserRewardHistory).filter(createTime__gt=date,
                                                                 source='groundPush').values('partnerId').annotate(
        total=Count('userId'))
    rewards = {x['partnerId']: x['total'] for x in reward_query}

    for app_id in ids:
        user_ids = {x.userId for x in model_manager.query(CouponInst).filter(partnerId=app_id,
                                                                             status=1,
                                                                             useDate__range=(
                                                                                 yesterday,
                                                                                 yesterday + timedelta(days=1)))}

        user_picked_ids = {x.userId for x in model_manager.query(UserRewardHistory).filter(partnerId=app_id,
                                                                                           source='groundPush',
                                                                                           createTime__range=(
                                                                                               yesterday, date))}

        remain = model_manager.query(ZhiyueUser).filter(userId__in=user_ids,
                                                        lastActiveTime__gt=date).count()

        picked_remain = model_manager.query(ZhiyueUser).filter(userId__in=user_picked_ids,
                                                               lastActiveTime__gt=date).count()

        not_picked = user_ids - user_picked_ids

        others_remains[app_id] = model_manager.query(ZhiyueUser).filter(userId__in=not_picked,
                                                                        lastActiveTime__gt=date).count()
        others_rates[app_id] = int(others_remains[app_id] / len(not_picked) * 100) if len(not_picked) else 100

        rates[app_id] = int(remain / len(user_ids) * 100) if len(user_ids) else 0
        remains[app_id] = remain
        picked_remains[app_id] = picked_remain
        picked = len(user_picked_ids)
        picked_rates[app_id] = int(picked_remain / picked * 100) if picked else 0

    ret = [{'app_id': x['partnerId'], 'app_name': apps[x['partnerId']], 'today': x['total'],
            'remain': '%s%%' % rates[x['partnerId']], 'open': rewards.get(x['partnerId'], 0),
            'active': actives.get(x['partnerId'], 0), 'picked_remain': picked_remains.get(x['partnerId'], 0),
            'picked_remain_rate': '%s%%' % picked_rates.get(x['partnerId'], 0),
            'others_remain': others_remains.get(x['partnerId'], 0),
            'others_remain_rate': '%s%%' % others_rates.get(x['partnerId'], 0), } for x in query]
    if save:
        for x in ret:
            info = CouponDailyStatInfo(partnerId=x['app_id'], statDate=date,
                                       total=x['today'], active=x['active'],
                                       open=x['open'], remainDay=x['remain'][:-1],
                                       remainOpen=x['picked_remain_rate'][:-1],
                                       remainNotOpen=x['others_remain_rate'][:-1])
            info.save(using='partner_rw')
    return ret


@api_func_anonymous
def make_offline(the_date):
    stat_date_from = 'current_date - interval 1 day'
    stat_date_to = 'current_date'

    if the_date:
        stat_date_from = '\'%s 00:00:00\'' % the_date
        stat_date_to = '\'%s 23:59:59\'' % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])
    query = '''
    select partnerId, count(*) from partner_CouponInst 
    where useDate between %s and %s AND 
    partnerId in (%s) GROUP BY partnerId
    ''' % (stat_date_from, stat_date_to, ids)

    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") if not the_date else the_date

    # 使用量
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [app_id, cnt] in rows:
            try:
                OfflineDailyStat(app_id=app_id, stat_date=date_str, user_num=cnt).save()
            except:
                pass

    make_offline_remain(the_date)

    return "ok"


@api_func_anonymous
def make_offline_remain(the_date):
    stat_date = datetime.now()

    if not the_date:
        the_date = 'current_date'
    else:
        stat_date = datetime.strptime(the_date, '%Y-%m-%d')
        the_date = "'%s'" % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])

    # 补红包打开数字
    bonus_query = '''
    select partnerId, count(*) from pojo_ZhiyueUser u, partner_UserRewardHistory c 
    where u.createTime between %s - interval 2 day and %s - interval 1 day
    and u.userId = c.userId and partnerId in (%s) and c.source='groundPush' group by partnerId
    ''' % (the_date, the_date, ids)
    # 补留存率
    # 补结算数字
    query = '''
    select partnerId, useNum, extInfo, remainDay from partner_ShopCouponStatSum
    WHERE useDate = %s - INTERVAL 2 DAY AND partnerId in (%s)
    ''' % (the_date, ids)
    # 补红包补贴
    op_bonus_query = '''
    SELECT partnerId, sum(amount)  FROM partner_RedCouponBonus
    WHERE partnerId = 1564403 AND rewardDate = %s - INTERVAL 2 DAY
    GROUP BY partnerId
    ''' % the_date
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        values = defaultdict(dict)
        for [app_id, cnt, ext_info, remain_day] in rows:
            percent = _get_percent(ext_info)

            total = apps[app_id].price * cnt * percent
            r = values[app_id]
            r['total'] = r.get('total', 0) + total
            remain_cnt = 0

            if remain_day:
                day_ = re.split(';', remain_day)[0]
                if day_:
                    remain_cnt = int(re.split('-', day_)[1])

            r['remain'] = r.get('remain', 0) + remain_cnt

        cursor.execute(bonus_query)
        rows = cursor.fetchall()

        for [app_id, cnt] in rows:
            values[app_id]['open'] = cnt

        cursor.execute(op_bonus_query)
        rows = cursor.fetchall()

        for [app_id, amount] in rows:
            values[app_id]['bonus'] = amount
    for stat in OfflineDailyStat.objects.filter(stat_date=times.to_date_str(stat_date - timedelta(days=2),
                                                                            "%Y-%m-%d")):
        r = values[stat.app_id]
        stat.user_bonus_num = r.get('open', 0)
        stat.remain = r.get('remain', 0)
        stat.user_cost = r.get('total', 0)
        stat.bonus_cost = r.get('bonus', 0)
        stat.total_cost = stat.bonus_cost + stat.user_cost
        try:
            stat.save(force_update=True)
        except:
            pass


def _get_percent(ext_info):
    low_cnt = int(json.loads(ext_info).get('LowQualityCnt', 0))
    percent = 1
    if low_cnt == 1:
        percent = 0.95
    elif low_cnt == 2:
        percent = 0.9
    elif low_cnt == 3:
        percent = 0.8
    elif low_cnt == 4:
        percent = 0.5
    elif low_cnt >= 5:
        percent = 0
    return percent


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

            # 获取领红包信息
    save_bonus_info()

    sync_remain()


def save_bonus_info(until=model_manager.yesterday()):
    ids = [x.userId for x in model_manager.query(UserRewardGroundHistory).filter(createTime__gt=until,
                                                                                 type=-1)]

    if ids:
        OfflineUser.objects.filter(user_id__in=ids).update(bonus_view=1)

    # 红包步骤
    for x in model_manager.query(UserRewardGroundHistory).filter(createTime__gt=until,
                                                                 type__gte=0) \
            .values('userId').annotate(amount=Sum('amount'), current=Max('type')):
        if x['amount'] > 0:
            OfflineUser.objects.filter(user_id=x['userId']).update(bonus_step=x['current'],
                                                                   bonus_pick=1,
                                                                   bonus_amount=x['amount'])

    # 获得红包信息
    for x in model_manager.query(UserRewardHistory).filter(createTime__gt=until,
                                                           source='groundPush'):
        OfflineUser.objects.filter(user_id=x.userId).update(bonus_got=1,
                                                            bonus_pick=1,
                                                            bonus_amount=x.amount,
                                                            bonus_time=x.createTime)
    # 提款信息
    for x in model_manager.query(WithdrawApply).filter(finishTime__gt=until):
        OfflineUser.objects.filter(user_id=x.userId).update(bonus_withdraw=float(x.amount) * 100,
                                                            withdraw_time=x.finishTime)


def sync_to_item_dev_user(app, owner, device_user, majia):
    return ItemDeviceUser(app=app, owner=owner,
                          created_at=device_user.createTime,
                          user_id=device_user.deviceUserId,
                          item_id=device_user.sourceItemId,
                          type=majia.type,
                          ip=device_user.ip,
                          city=device_user.city,
                          cutt_user_id=majia.cutt_user_id,
                          location=device_user.location)


def sync_remain():
    logger.info('同步留存数据')
    to_time = datetime.now()
    to_time_str = to_time.strftime('%Y-%m-%d')
    from_time_str = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')
    date_range = (from_time_str, to_time_str)
    create_range = ((to_time - timedelta(days=2)).strftime('%Y-%m-%d'), from_time_str)
    report_date = (to_time - timedelta(days=2)).strftime('%Y-%m-%d')  # 留存记录是针对前一天的
    for app in model_manager.get_dist_apps():
        ids = [x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=create_range, remain=0)]
        if ids:
            remains = [x.userId for x in
                       model_manager.query(ZhiyueUser).filter(userId__in=ids, lastActiveTime__range=date_range)]
            if remains:
                ItemDeviceUser.objects.filter(user_id__in=remains).update(remain=1)

            make_daily_remain(app.app_id, report_date)

        if app.offline:
            offline_users = OfflineUser.objects.filter(app=app, created_at__range=create_range, remain=0)
            user_ids = [x.user_id for x in offline_users]
            remain_ids = {x.userId for x in
                          model_manager.query(ZhiyueUser).filter(userId__in=user_ids, lastActiveTime__range=date_range)}
            if remain_ids:
                OfflineUser.objects.filter(user_id__in=remain_ids).update(remain=1)


def make_daily_remain(app_id, date):
    the_date = model_manager.get_date(date)
    qq_remain_total = 0
    wx_remain_total = 0
    for user in ItemDeviceUser.objects.filter(app_id=app_id,
                                              created_at__range=[the_date,
                                                                 the_date + timedelta(days=1)]).values(
        'owner_id',
        'type'
    ).annotate(total=Count('user_id'), remain=Sum('remain')):
        if user['type'] == 0:
            UserDailyStat.objects.filter(report_date=date, user_id=user['owner_id']).update(qq_remain=user['remain'])
            qq_remain_total += user['remain']
        elif user['type'] == 1:
            UserDailyStat.objects.filter(report_date=date, user_id=user['owner_id']).update(wx_remain=user['remain'])
            wx_remain_total += user['remain']

    AppDailyStat.objects.filter(report_date=date, app_id=app_id).update(wx_remain=wx_remain_total,
                                                                        qq_remain=qq_remain_total)


def calc_save_remain():
    logger.info('同步留存数据')
    to_time = datetime.now()
    from_time_str = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')
    create_range = ((to_time - timedelta(days=2)).strftime('%Y-%m-%d'), from_time_str)
    for app in model_manager.get_dist_apps():
        qq_cnt = ItemDeviceUser.objects.filter(type=0, app=app, created_at__range=create_range, remain=1).count()
        wx_cnt = ItemDeviceUser.objects.filter(type=1, app=app, created_at__range=create_range, remain=1).count()

        report_date = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')  # 留存记录是针对前一天的
        AppDailyStat.objects.filter(report_date=report_date, app=app).update(qq_remain=qq_cnt, wx_remain=wx_cnt)

        for user in User.objects.filter(app=app, status=0):
            qq_cnt = ItemDeviceUser.objects.filter(type=0, owner=user, created_at__range=create_range).count()
            wx_cnt = ItemDeviceUser.objects.filter(type=1, owner=user, created_at__range=create_range).count()
            UserDailyStat.objects.filter(report_date=report_date, user=user).update(
                qq_remain=qq_cnt, wx_remain=wx_cnt)


def re_calc_off():
    for i in range(0, 14):
        _re_calc((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))


def _re_calc(the_date):
    stat_date_from = '\'%s 00:00:00\'' % the_date
    stat_date_to = '\'%s 23:59:59\'' % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])
    query = '''
        select partnerId, count(*) from partner_CouponInst 
        where useDate between %s and %s AND 
        partnerId in (%s) GROUP BY partnerId
        ''' % (stat_date_from, stat_date_to, ids)

    date_str = times.to_date_str(datetime.now() - timedelta(days=1), "%Y-%m-%d") if not the_date else the_date

    # 使用量
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [app_id, cnt] in rows:
            try:
                row = OfflineDailyStat.objects.filter(app_id=app_id, stat_date=date_str).update(user_num=cnt)
                if row == 0:
                    OfflineDailyStat(app_id=app_id, stat_date=date_str, user_num=cnt).save()
            except:
                pass

        query_q = '''
            select partnerId, useNum, extInfo, remainDay from partner_ShopCouponStatSum
            WHERE useDate = '%s' AND partnerId in (%s)
            ''' % (the_date, ids)

        cursor.execute(query_q)
        rows = cursor.fetchall()
        total_map = dict()
        remain_map = dict()

        if len(rows):
            for [app_id, cnt, ext_info, remain_day] in rows:
                percent = _get_percent(ext_info)

                if app_id not in total_map:
                    total_map[app_id] = 0
                    remain_map[app_id] = 0

                total_map[app_id] += apps[app_id].price * cnt * percent
                if remain_day:
                    day_ = re.split(';', remain_day)[0]
                    if day_:
                        remain_cnt = int(re.split('-', day_)[1])
                        remain_map[app_id] += remain_cnt

            for app_id in apps:
                total = total_map[app_id]
                OfflineDailyStat.objects.filter(app_id=app_id, stat_date=date_str).update(user_cost=total,
                                                                                          total_cost=total,
                                                                                          remain=remain_map[app_id])


def sync_online_remain():
    to_time = datetime.now()
    to_time_str = to_time.strftime('%Y-%m-%d')
    from_time_str = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')
    date_range = (from_time_str, to_time_str)
    for app in model_manager.get_dist_apps():
        ids = [x.user_id for x in ItemDeviceUser.objects.filter(app=app, created_at__range=date_range, remain=0)]
        remains = [x.userId for x in
                   model_manager.query(ZhiyueUser).filter(userId__in=ids, lastActiveTime__gt=to_time_str)]
        ItemDeviceUser.objects.filter(user_id__in=remains, app=app,
                                      created_at__range=date_range, remain=0).update(remain=1)


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
    from pyhive import hive

    cursor = hive.connect('10.19.9.13').cursor()
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
    from pyhive import hive

    cursor = hive.connect('10.19.9.13').cursor()
    try:
        for app in model_manager.get_dist_apps():
            ids = [x.user_id for x in OfflineUser.objects.filter(app=app, created_at__range=create_range, remain=0)]
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
