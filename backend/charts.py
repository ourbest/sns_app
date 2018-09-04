from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db import connection

from backend import dates
from backend.api_helper import get_session_app
from backend.models import AppDailyStat


@api_func_anonymous
def api_get_app_month_data(request):
    app = get_session_app(request)

    data = AppDailyStat.objects.filter(app_id=app, qq_install__gt=0,
                                       report_date__gt=(dates.today() - timedelta(days=60)).strftime('%Y-%m-%d'))
    report_dates = []
    pv = []
    install = []
    remain = []
    for x in data:
        report_dates.append(x.report_date)
        install.append(x.qq_install + x.wx_install)
        pv.append(x.qq_pv + x.wx_pv)
        remain.append(x.qq_remain + x.wx_remain)

    return {
        'dates': report_dates,
        'pv': pv,
        'users': install,
        'remains': remain,
    }


@api_func_anonymous
def api_get_app_today():
    hours = []
    app_data = dict()

    with connection.cursor() as cursor:
        cursor.execute('select app_id, concat(left(ts, 14), \'00\'), count(*) from backend_weizhanclick '
                       'where ts > now() - interval 24 hour and tid>0 group by app_id, left(ts, 14)')
        rows = cursor.fetchall()
        for app, hour, cnt in rows:
            if hour not in hours:
                hours.append(hour)

            value = app_data.get(app, {
                'pv': dict(),
                'users': dict(),
            })
            value['pv'][hour] = cnt

        cursor.execute('select app_id, concat(left(created_at, 14), \'00\'), count(*) from backend_itemdeviceuser '
                       'where created_at > now() - interval 24 hour group by app_id, left(created_at, 14)')

        rows = cursor.fetchall()
        for app, hour, cnt in rows:
            if hour not in hours:
                hours.append(hour)

            value = app_data.get(app, {
                'pv': dict(),
                'users': dict(),
            })
            value['users'][hour] = cnt

    return_value = dict()
    for k, v in app_data.items():
        pass

    return {
        'hours': hours,
        'data': return_value,
    }
