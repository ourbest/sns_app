from dj.utils import api_func_anonymous

from backend import api_helper
from backend.models import KPIPeriod, UserDailyStat, AppDailyStat


@api_func_anonymous
def api_kpi(request, i_period):
    app = api_helper.get_session_app(request)
    return get_kpi(app, i_period)


def get_kpi_periods(app):
    return [x.json for x in KPIPeriod.objects.filter(app=app).order_by("-pk")]


def get_kpi(app_id, period=None):
    query = KPIPeriod.objects.filter(app_id=app_id).order_by("-pk")
    if period:
        query = query.filter(id=period)

    period = query.first()

    if not period:
        return {
            'period': None
        }

    rows = []
    users = dict()
    for x in UserDailyStat.objects.filter(report_date__range=(period.from_date, period.to_date),
                                          app_id=app_id).order_by('report_date'):
        if len(rows) == 0 or rows[-1]['date'] != x.report_date:
            rows.append({
                'date': x.report_date
            })

        the_row = rows[-1]
        the_row['pv_%s' % x.user_id] = x.qq_pv + x.wx_pv
        the_row['users_%s' % x.user_id] = x.qq_install + x.wx_install
        the_row['remain_%s' % x.user_id] = x.qq_remain + x.wx_remain
        if x.user_id not in users:
            users[x.user_id] = x.user.name

    for idx, x in enumerate(AppDailyStat.objects.filter(report_date__range=(period.from_date, period.to_date),
                                                        app_id=app_id).order_by('report_date')):
        the_row = rows[idx]
        the_row['pv'] = x.wx_pv + x.qq_pv
        the_row['users'] = x.qq_install + x.wx_install
        the_row['remain'] = x.qq_remain + x.wx_remain

    return {
        'period': period.json,
        'rows': rows,
        'users': list(users.items()),
    }
