import json
import re
from collections import defaultdict
from datetime import datetime, timedelta

import math
from dj import times
from dj.utils import api_func_anonymous
from django.db import connections
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone

from backend import api_helper, model_manager, stats
from backend.api_helper import get_session_app
from backend.models import AppUser, AppDailyStat, UserDailyStat, App, DailyActive, ItemDeviceUser, UserDailyDeviceUser
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, AdminPartnerUser, CouponInst, ItemMore, \
    ZhiyueUser, UserRewardHistory, AppConstants, CouponPmSentInfo, CouponDailyStatInfo, OfflineDailyStat, DeviceUser


@api_func_anonymous
def user_share(i_uid, request):
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
    # url = re.findall('https?://.+/weizhan/article/\d+/\d+/\d+', text)
    # return url[0] if url else ''
    return 'http://www.cutt.com/weizhan/article/%s/%s/%s' % (
        x.article.item.clipId, x.article.item_id, x.article.partnerId)


@api_func_anonymous
def get_url_title(url):
    u = re.findall('https?://.+/weizhan/article/\d+/(\d+)/(\d+)', url)
    if u:
        (article_id, app_id) = u[0]
        more = model_manager.query(ItemMore).filter(itemId=article_id, appId=app_id).first()
        if more and more.title:
            return more.title
        item = model_manager.query(ClipItem).filter(itemId=article_id).first()
        return item.title if item.title else '(无标题)'
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
    name = models.CharField(max_length=255)
    userId = models.IntegerField(primary_key=True)
    deviceUserId = models.IntegerField()
    partnerId = models.IntegerField()
    shareNum = models.IntegerField()
    weizhanNum = models.IntegerField()
    downPageNum = models.IntegerField()
    appUserNum = models.IntegerField()
    commentNum = models.IntegerField()
    agreeNum = models.IntegerField()
    viewNum = models.IntegerField()
    secondShareNum = models.IntegerField()
    userType = models.IntegerField(help_text='userType=1 内容产生用户 ，userType=2 内容传播用户')
    time = models.DateTimeField()
    :param email:
    :param date:
    :param request:
    :return:
    """
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    the_user = api_helper.get_login_user(request, email)
    return stats.get_user_stat(date, the_user)


@api_func_anonymous
def get_user_majia(email, request):
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
    app = get_session_app(request)
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    return stats.app_daily_stat(app, date, include_sum)


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
    } for x in AppDailyStat.objects.filter(report_date__range=(from_date, to_date),
                                           app_id=i_app).order_by("-pk")]


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
    } for x in UserDailyStat.objects.filter(report_date__range=(from_date, to_date))
        .select_related('app', 'user').order_by("-pk")]


@api_func_anonymous
def get_app_stat():
    return do_get_app_stat()


@api_func_anonymous
def get_stat_before_days(i_days):
    if not i_days:
        i_days = 1

    cnt = App.objects.filter(stage__in=('分发期', '留守期')).count()

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
    apps = {str(x.app_id): x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}
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

            stats.client.gauge('cutt.app%s.active.%s' % (row[0], row[1]), row[2])

            sum['%s' % row[1]] = row[2]

    return sorted(data, key=lambda x: int(x['app_id']))


@api_func_anonymous
def get_new_device():
    apps = {str(x.app_id): x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}
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
            stats.client.gauge('cutt.app%s.new.%s' % (row[0], row[1]), row[2])

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

    date_str = times.to_date_str(timezone.now(), "%Y-%m-%d") if not the_date else the_date

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
    stat_date = timezone.now()

    if not the_date:
        the_date = 'current_date'
    else:
        stat_date = timezone.make_aware(datetime.strptime(the_date, '%Y-%m-%d'))
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
            percent = 1
            low_cnt = int(json.loads(ext_info).get('LowQualityCnt', 0))

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

            total = math.ceil(apps[app_id].price * cnt * percent)
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


def sync_device_user():
    stat_date = datetime.now()
    from_date = stat_date - timedelta(days=1)
    for app in App.objects.filter(stage__in=('分发期', '留守期')):
        majias = {x.cutt_user_id: x for x in AppUser.objects.filter(type__in=(0, 1), user__app=app, user__status=0)}
        qq_user_ids = []
        wx_user_ids = []
        if majias:
            ids_map = defaultdict(dict)
            for device_user in model_manager.query(DeviceUser).filter(sourceUserId__in=majias.keys(),
                                                                      createTime__range=(
                                                                              from_date.strftime('%Y-%m-%d'),
                                                                              stat_date.strftime('%Y-%m-%d'))):
                majia = majias.get(device_user.sourceUserId)
                owner = majia.user
                model_manager.save_ignore(ItemDeviceUser(app=app, owner=owner,
                                                         created_at=device_user.createTime,
                                                         user_id=device_user.deviceUserId,
                                                         item_id=device_user.sourceItemId,
                                                         type=majia.type))
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


def sync_remain():
    to_time = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
    from_time = to_time - timedelta(days=1)
    date_range = (from_time, to_time)
    for app in App.objects.filter(stage__in=('分发期', '留守期')):
        ids = [x.user_id for x in ItemDeviceUser.objects.filter(app=app,
                                                                created_at__range=(
                                                                    to_time - timedelta(days=1), to_time))]
        remains = [x.userId for x in
                   model_manager.query(ZhiyueUser).filter(userId__in=ids, lastActiveTime__range=date_range)]
        ItemDeviceUser.objects.filter(user_id__in=remains).update(remain=1)

        qq_cnt = ItemDeviceUser.objects.filter(type=0, app=app).count()
        wx_cnt = ItemDeviceUser.objects.filter(type=1, app=app).count()

        AppDailyStat.objects.filter()
