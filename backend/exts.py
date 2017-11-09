from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db import connections
from django.shortcuts import render
from django.utils import timezone

from backend.models import DailyActive


@api_func_anonymous
def daily_stat(request, appId):
    return render(request, 'daily_stat.html', context={
        'new': get_new_device(appId),
        'today': get_active_device(appId),
        'yesterday': get_last_day(appId),
    }) if appId else ''


def get_last_day(appId):
    da = DailyActive.objects.filter(created_at__lt=timezone.now() - timedelta(days=1), app_id=appId).order_by(
        "-pk").first()
    return {
        'iphone': da.iphone,
        'android': da.android,
        'total': da.total
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
