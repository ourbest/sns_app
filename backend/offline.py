from datetime import timedelta, datetime

from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum
from django.template.loader import render_to_string

from backend import api_helper, model_manager, zhiyue
from backend.models import OfflineUser, App
from backend.zhiyue_models import ShopCouponStatSum


@api_func_anonymous
def api_owners(request):
    app = api_helper.get_session_app(request)
    today = model_manager.today()
    ret = [x for x in
           OfflineUser.objects.filter(app_id=app, created_at__lt=today - timedelta(days=1)).values('owner').annotate(
               total=Count('user_id'), remain=Sum('remain')) if x['total'] >= 30]
    ids = [x['owner'] for x in ret]
    users = {x.userId: x.name for x in zhiyue.get_users(ids)}
    for x in ret:
        x['name'] = users.get(x['owner'], x['owner'])
    return ret


@api_func_anonymous
def api_owner_remain(owner):
    today = model_manager.today()
    return OfflineUser.objects.filter(owner=owner,
                                      created_at__lt=today - timedelta(days=1)).values('owner').annotate(
        total=Count('user_id'),
        remain=Sum('remain'))[0] if owner else []


@api_func_anonymous
def api_daily_remain(request):
    sql = 'select date(created_at), count(*), sum(remain) from backend_offlineuser ' \
          'where app_id = %s group by date(created_at) order by date(created_at) desc' \
          % api_helper.get_session_app(request)

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{
            'date': date,
            'total': total,
            'remain': remain
        } for date, total, remain in rows]


@api_func_anonymous
def api_owner_detail(owner, date):
    if not owner:
        return []

    query = OfflineUser.objects.filter(owner=owner)
    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def api_app_detail(request, date):
    app = api_helper.get_session_app(request)

    if not date:
        date = datetime.now().strftime('%Y-%m-%d')

    query = OfflineUser.objects.filter(app_id=app)

    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def api_owner_date(owner):
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
def daily_report(send_mail=True):
    yesterday = model_manager.yesterday()

    apps = {x.app_id: x.app_name for x in App.objects.filter(offline=1)}

    sum = OfflineUser.objects.filter(created_at__range=(yesterday, model_manager.today())).values('app_id').annotate(
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

    for idx, value in enumerate(sum):
        send_offline_detail(value['app_id'], value, sum_yesterday[idx])


def send_offline_detail(app_id, app_detail, prev_detail, date=model_manager.yesterday()):
    total_na = 0
    stats = model_manager.query(ShopCouponStatSum).filter(partnerId=app_id, useDate=date.strftime('%Y-%m-%d')).order_by(
        '-useNum')
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

    id_names = {x.ownerId: '%s %s' % (x.ownerName, x.shopName) for x in
                model_manager.query(ShopCouponStatSum).filter(partnerId=app_id,
                                                              useDate=the_date_before.strftime('%Y-%m-%d'))}

    yesterday_remains = OfflineUser.objects.filter(created_at__range=(the_date_before,
                                                                      date),
                                                   app_id=app_id).values('owner').annotate(
        total=Count('user_id'), remain=Sum('remain'), pick=Sum('bonus_pick')).order_by('-total')

    for x in yesterday_remains:
        x['name'] = id_names.get(x['owner'], '')

    app_detail['na'] = int(100 * (1 - (total_na / app_detail['total'])))
    html = render_to_string('offline_detail.html', {
        'yesterday': app_detail,
        'yesterday_remain': prev_detail,
        'yesterday_remains': yesterday_remains,
        'yesterday_details': stats,
    })
    api_helper.send_html_mail('%s%s地推日报' % (app_detail['app'], date.strftime('%Y-%m-%d')),
                              'yonghui.chen@cutt.com', html)
