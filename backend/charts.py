from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db import connection

from backend import dates, model_manager
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
def api_get_app_today(request):
    hours = []
    pv = dict()
    users = dict()

    app = get_session_app(request)

    with connection.cursor() as cursor:
        cursor.execute('select app_id, concat(left(ts, 14), \'00\'), count(*) from backend_weizhanclick '
                       'force index(backend_weizhanclick_ts_9fbc43af) '
                       'where ts > now() - interval 24 hour and tid>0 and app_id=%s '
                       'group by app_id, left(ts, 14)' % app)
        rows = cursor.fetchall()
        for app, hour, cnt in rows:
            if hour not in hours:
                hours.append(hour)

            pv[hour] = cnt

        cursor.execute('select app_id, concat(left(created_at, 14), \'00\'), count(*) from backend_itemdeviceuser '
                       'where created_at > now() - interval 24 hour and app_id=%s '
                       'group by app_id, left(created_at, 14)' % app)

        rows = cursor.fetchall()
        for app, hour, cnt in rows:
            if hour not in hours:
                hours.append(hour)

            users[hour] = cnt

    return {
        'hours': hours,
        'pv': [pv.get(x, '0') for x in hours],
        'users': [users.get(x, '0') for x in hours],
    }
