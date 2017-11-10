from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db import connections
from django.shortcuts import render
from django.utils import timezone

from backend.models import DailyActive, App


@api_func_anonymous
def daily_stat(request, i_appId):
    appId = i_appId
    app = App.objects.filter(app_id=appId).first()
    return render(request, 'daily_stat.html', context={
        'new': get_new_device(appId),
        'today': get_active_device(appId),
        'yesterday': get_last_day(appId),
        'name': app.app_name,
    }) if app else ''


def get_last_day(appId):
    da = DailyActive.objects.filter(created_at__lt=timezone.now() - timedelta(days=1), app_id=appId).order_by(
        "-pk").first()
    return {
        'iphone': da.iphone if da.iphone else 0,
        'android': da.android if da.android else 0,
        'total': da.total if da.total else 0,
    } if da else {
        'iphone': 0,
        'android': 0,
        'total': 0,
    }


def get_active_device(appId):
    return get_by_query('''
                select platform,count(*) from pojo_ZhiyueUser where platform in (%s)
                 and appId = %s
                 and lastActiveTime > current_date
                group by platform
            ''' % ('\'iphone\', \'android\'', appId))


def get_new_device(appId):
    return get_by_query('''
            select platform,count(*) from pojo_ZhiyueUser where platform in (%s)
             and appId = %s
             and createTime > current_date
            group by platform
        ''' % ('\'iphone\', \'android\'', appId))


def get_by_query(query):
    android = 0
    iphone = 0
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            if row[0] == 'android':
                android = row[1]
            else:
                iphone = row[1]
    return {
        'android': android,
        'iphone': iphone,
        'total': int(android) + int(iphone)
    }
