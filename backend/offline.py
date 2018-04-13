from datetime import timedelta, datetime

from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum

from backend import api_helper, model_manager, zhiyue
from backend.models import OfflineUser


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
