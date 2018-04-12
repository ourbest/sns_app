from datetime import timedelta, datetime
from functools import lru_cache

from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum
from django.shortcuts import render

from backend import api_helper, model_manager
from backend.models import ItemDeviceUser
from backend.zhiyue_models import ZhiyueUser, DeviceUser


@api_func_anonymous
def api_owners(request):
    app = api_helper.get_session_app(request)
    today = model_manager.today()
    ret = [x for x in
           ItemDeviceUser.objects.filter(app_id=app, created_at__lt=today - timedelta(days=1)).values('owner_id',
                                                                                                      'type').annotate(
               total=Count('user_id'), remain=Sum('remain')) if x['total']]
    ids = [x['owner_id'] for x in ret]
    users = {x.pk: x.name for x in model_manager.get_users(ids)}
    for x in ret:
        x['name'] = users.get(x['owner_id'], x['owner_id'])
        x['owner'] = '%s_%s' % (x['owner_id'], x['type'])
    return ret


@api_func_anonymous
def api_owner_remain(owner):
    [owner_id, type_id] = owner.split('_')
    today = model_manager.today()
    return ItemDeviceUser.objects.filter(owner_id=owner_id, type=type_id,
                                         created_at__lt=today - timedelta(days=1)).values('owner_id', 'type').annotate(
        total=Count('user_id'),
        remain=Sum('remain'))[0] if owner else []


@api_func_anonymous
def api_daily_remain(request):
    sql = 'select date(created_at), count(*), sum(remain) from backend_itemdeviceuser ' \
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

    [owner_id, type_id] = owner.split('_')

    query = ItemDeviceUser.objects.filter(owner_id=owner_id, type=type_id).exclude(location='')
    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def api_app_detail(request, date):
    app = api_helper.get_session_app(request)

    if not date:
        date = datetime.now().strftime('%Y-%m-%s')

    query = ItemDeviceUser.objects.filter(app_id=app).exclude(location='')

    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


def html_heat(request):
    return render(request, 'online.html')


@api_func_anonymous
def api_heat():
    return [{
        "lng": 116.191031,
        "lat": 39.988585,
        "count": 10
    }, {
        "lng": 116.389275,
        "lat": 39.925818,
        "count": 11
    }]


@api_func_anonymous
def api_owner_date(owner):
    if not owner:
        return []
    [owner_id, type_id] = owner.split('_')

    sql = 'select type, date(created_at), count(*), sum(remain) from backend_itemdeviceuser ' \
          'where owner_id = %s and type = %s group by type, date(created_at) ' \
          'order by date(created_at) desc' % (owner_id, type_id)

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{
            'type': owner_type,
            'owner': '%s_%s' % (owner_id, owner_type),
            'date': date,
            'total': total,
            'remain': remain
        } for owner_type, date, total, remain in rows]


@api_func_anonymous
def api_active_users(request):
    ids = [x.userId for x in model_manager.query(ZhiyueUser).filter(appId=str(api_helper.get_session_app(request)),
                                                                    platform__in=['iphone', 'android'],
                                                                    lastActiveTime__gt=model_manager.get_date())]
    return [{
        'remain': 0,
        'location': x.location,
    } for x in model_manager.query(DeviceUser).filter(deviceUserId__in=ids) if x.location]


@lru_cache(maxsize=100000)
def get_device_loc(user_id):
    x = model_manager.query(DeviceUser).filter(deviceUserId=user_id).first()
    return x.location if x else None