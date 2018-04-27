from datetime import timedelta, datetime

from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum
from django.template.loader import render_to_string
from django_rq import job
from logzero import logger

from backend import dates
from backend import api_helper, model_manager, zhiyue
from backend.models import OfflineUser, App, RuntimeData
from backend.zhiyue_models import ShopCouponStatSum, UserRewardHistory, UserRewardGroundHistory, OfflineDailyStat


@api_func_anonymous
def api_owners(request):
    """
    获取扫码用户
    :param request:
    :return:
    """
    app = api_helper.get_session_app(request)
    today = dates.today()
    ret = [x for x in
           OfflineUser.objects.filter(app_id=app, created_at__lt=today - timedelta(days=1)).values('owner').annotate(
               total=Count('user_id'), remain=Sum('remain'))]
    ids = [x['owner'] for x in ret]
    users = {x.userId: x.name for x in zhiyue.get_users(ids)}
    for x in ret:
        x['name'] = users.get(x['owner'], x['owner'])
    return ret


@api_func_anonymous
def api_owner_remain(owner):
    """
    根据扫码用户获取留存情况
    :param owner:
    :return:
    """
    today = dates.today()
    return OfflineUser.objects.filter(owner=owner,
                                      created_at__lt=today - timedelta(days=1)).values('owner').annotate(
        total=Count('user_id'),
        remain=Sum('remain'))[0] if owner else []


@api_func_anonymous
def api_owner_stat(app_id, date):
    return [x.json for x in
            model_manager.query(ShopCouponStatSum).filter(partnerId=app_id, useDate=date).order_by('-useNum')]


@api_func_anonymous
def api_daily_remain(request, all):
    """
    日留存情况
    :param request:
    :return:
    """
    if all == "1":
        sql = 'select app_id, date(created_at), count(*), sum(remain), sum(bonus_pick) from backend_offlineuser ' \
              'where created_at > current_date - interval 14 day ' \
              'group by app_id, date(created_at) order by date(created_at) desc'
    else:
        sql = 'select app_id, date(created_at), count(*), sum(remain), sum(bonus_pick) from backend_offlineuser ' \
              'where app_id = %s group by date(created_at) order by app_id, date(created_at) desc' \
              % api_helper.get_session_app(request)

    app_names = model_manager.app_names()
    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{
            'app_id': app_id,
            'app': app_names[app_id][:-3],
            'date': date,
            'total': total,
            'remain': remain,
            'picked': pick
        } for app_id, date, total, remain, pick in rows]


@api_func_anonymous
def api_owner_detail(owner, date):
    """
    扫码兼职日留存情况
    :param owner:
    :param date:
    :return:
    """
    if not owner:
        return []

    query = OfflineUser.objects.filter(owner=owner)
    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def api_owner_detail_stat(owner, app_id):
    return [x.json for x in
            model_manager.query(ShopCouponStatSum).filter(partnerId=app_id, ownerId=owner).order_by("-useDate")]


@api_func_anonymous
def api_app_detail(request, date):
    """
    整体日留存情况
    :param request:
    :param date:
    :return:
    """
    app = api_helper.get_session_app(request)

    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    query = OfflineUser.objects.filter(app_id=app)

    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def get_coupon_at(date):
    date = dates.get_date(date)
    yesterday = date - timedelta(days=1)
    apps = {x.app_id: x.app_name for x in App.objects.filter(offline=1)}

    remains = dict()

    query = OfflineUser.objects.filter(created_at__gt=date).values('app_id').annotate(
        total=Count('user_id'), viewed=Sum('bonus_view'), picked=Sum('bonus_pick'))

    for u in OfflineUser.objects.filter(created_at__range=(yesterday, date)).values(
            'app_id').annotate(total=Count('user_id'), remain=Sum('remain')):
        remains[u['app_id']] = int(u['remain'] / u['total'] * 100)

    ret = [{'app_id': x['app_id'], 'app_name': apps[x['app_id']][:-3], 'today': x['total'],
            'remain': '%s%%' % remains[x['app_id']],
            'open': x['viewed'],
            'picked': x['picked']} for x in query]
    return ret


@api_func_anonymous
def api_owner_date(owner):
    """
    兼职日留存情况
    :param owner:
    :return:
    """
    if not owner:
        return []

    sql = 'select owner, date(created_at), count(*), sum(remain) from backend_offlineuser ' \
          'where owner = %s group by owner, date(created_at) order by date(created_at) desc' % owner

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{
            'owner': owner,
            'date': date,
            'total': total,
            'remain': remain
        } for owner, date, total, remain in rows]


@api_func_anonymous
def daily_report():
    """
    发送日志
    :return:
    """
    do_send_daily_report.delay()


@api_func_anonymous
def api_weekly_report(i_week=0):
    """
    获取周报数据
    :return:
    """
    this_week = dates.current_week() if not i_week else dates.plus_week(-i_week)
    apps = {x.app_id: x.app_name for x in App.objects.all()}
    ret = list(
        OfflineDailyStat.objects.filter(stat_date__range=dates.to_date_str_range(this_week)).values(
            'app_id').annotate(total=Sum('user_num'),
                               amount=Sum('user_cost'),
                               remain=Sum('remain'),
                               bonus_num=Sum('user_bonus_num'),
                               bonus_got=Sum('user_bonus_got'),
                               cash_num=Sum('user_cash_num'),
                               withdraw=Sum('bonus_cash')))

    for x in ret:
        x['app'] = apps[x['app_id']][:-3]

    return ret


@api_func_anonymous
def api_cash_amount(from_date, to_date):
    """
    获取提款情况
    :return:
    """
    if not from_date:
        today = dates.today()
        from_date = (today - timedelta(today.weekday())).strftime('%Y-%m-%d')
    else:
        from_date = from_date[:10]

    if not to_date:
        to_date = (today + timedelta(1)).strftime('%Y-%m-%d')
    else:
        to_date = to_date[:10]

    query = 'select app_name, sum(bonus_withdraw), count(*) ' \
            'from backend_app a, backend_offlineuser u ' \
            'where a.app_id = u.app_id and u.withdraw_time between \'%s\' and \'%s\' ' \
            'group by app_name' % (from_date, to_date)

    with connection.cursor() as cursor:
        cursor.execute(query)
        return [{'app': app_name, 'amount': amount, 'cnt': cnt} for [app_name, amount, cnt] in
                cursor.fetchall()]


@api_func_anonymous
def api_weekdays():
    return {
        'current': dates.to_str(dates.current_week()),
        'last': dates.to_str(dates.plus_week(-1)),
        'last2': dates.to_str(dates.plus_week(-2)),
    }


# --------------------------------------------- #

@job
def do_send_daily_report(send_mail=True):
    """
    发送日报
    :param send_mail:
    :return:
    """
    yesterday = dates.yesterday()

    apps = {x.app_id: x.app_name for x in App.objects.filter(offline=1)}

    sum = OfflineUser.objects.filter(created_at__range=(yesterday, dates.today())).values('app_id').annotate(
        total=Count('user_id'), view=Sum('bonus_view'), picked=Sum('bonus_pick'))

    for x in sum:
        x['app'] = apps[x['app_id']]

    sum_yesterday = OfflineUser.objects.filter(created_at__range=(yesterday - timedelta(days=1),
                                                                  yesterday)).values('app_id').annotate(
        total=Count('user_id'), remain=Sum('remain'), picked=Sum('bonus_pick'))

    for x in sum_yesterday:
        x['app'] = apps[x['app_id']]

    html = render_to_string('offline_daily.html', {'sum': sum, 'sum_yesterday': sum_yesterday})
    if send_mail:
        api_helper.send_html_mail('%s地推日报' % yesterday.strftime('%Y-%m-%d'), 'yonghui.chen@cutt.com', html)

    htmls = list()
    for idx, value in enumerate(sum):
        htmls.append(send_offline_detail(value['app_id'], value, sum_yesterday[idx],
                                         date=yesterday, send_mail=send_mail))

    api_helper.send_html_mail('%s地推详情汇总' % yesterday.strftime('%Y-%m-%d'),
                              'yonghui.chen@cutt.com', '<p>'.join(htmls))


def send_offline_detail(app_id, app_detail, prev_detail, date=dates.yesterday(), send_mail=True):
    total_na = 0
    date_str = date.strftime('%Y-%m-%d')
    logger.info('Send offline detail at %s' % date_str)
    stats = model_manager.query(ShopCouponStatSum).filter(partnerId=app_id, useDate=date_str).order_by('-useNum')
    picks = {x['owner']: x['pick'] for x in
             OfflineUser.objects.filter(app_id=app_id, created_at__range=(date, date + timedelta(days=1))).values(
                 'owner').annotate(total=Count('user_id'), pick=Sum('bonus_pick'))}

    id_names = dict()

    for stat in stats:
        total_na += stat.naNum / 100 * stat.useNum
        stat.rate = int(100 - stat.naNum)
        stat.pick = picks[stat.ownerId]
        id_names[stat.ownerId] = '%s %s' % (stat.ownerName, stat.shopName)

    the_date_before = date - timedelta(days=1)
    the_date_before_str = the_date_before.strftime('%Y-%m-%d')

    id_names = {x.ownerId: '%s %s' % (x.ownerName, x.shopName) for x in
                model_manager.query(ShopCouponStatSum).filter(partnerId=app_id, useDate=the_date_before_str)}

    yesterday_remains = OfflineUser.objects.filter(created_at__range=(the_date_before,
                                                                      date),
                                                   app_id=app_id).values('owner').annotate(
        total=Count('user_id'), remain=Sum('remain'), pick=Sum('bonus_pick')).order_by('-total')

    for x in yesterday_remains:
        x['name'] = id_names.get(x['owner'], '')
        x['ratio'] = x['remain'] / x['total']

    app_detail['na'] = int(100 * (1 - (total_na / app_detail['total'])))
    html = render_to_string('offline_detail.html', {
        'yesterday': app_detail,
        'yesterday_remain': prev_detail,
        'yesterday_remains': yesterday_remains,
        'yesterday_details': stats,
        'yesterday_str': date_str,
        'tdby_str': the_date_before_str,
    })

    if send_mail:
        om = RuntimeData.objects.filter(name='offline_%s' % app_id).first()
        api_helper.send_html_mail('%s%s地推日报' % (app_detail['app'], date_str),
                                  'yonghui.chen@cutt.com' if not om else om.value, html)
    else:
        logger.info(html)

    return html


@job
def sync_bonus_data(date_range=(dates.yesterday() - timedelta(days=30), dates.yesterday()),
                    app_id=1564460):
    picked = model_manager.query(UserRewardGroundHistory).filter(createTime__range=date_range, type=1,
                                                                 amount__gt=0, partnerId=app_id)
    user_ids = [x.userId for x in picked]
    OfflineUser.objects.filter(user_id__in=user_ids).update(bonus_pick=1)

    for x in model_manager.query(UserRewardHistory).filter(userId__in=user_ids, source='GroundPush'):
        OfflineUser.objects.filter(user_id=x.userId).update(bonus_amount=x.amount, bonus_got=1, bonus_time=x.createTime)


@api_func_anonymous
def api_offline_app(request):
    app = model_manager.get_app(api_helper.get_session_app(request))
    return app.json if app else {}
