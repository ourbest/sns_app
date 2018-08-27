from dj.utils import api_func_anonymous
from .loggs import logger

from backend import api_helper, model_manager
from backend.models import KPIPeriod, UserDailyStat, AppDailyStat


@api_func_anonymous
def api_kpi(request, i_period):
    app = api_helper.get_session_app(request)
    return get_kpi(app, i_period)


@api_func_anonymous
def api_kpi_config(request):
    app = api_helper.get_session_app(request)
    return [x.json for x in KPIPeriod.objects.filter(app_id=app, status=0).order_by("-pk")[0:10]]


@api_func_anonymous
def api_kpi_remove(request, i_id):
    db = KPIPeriod.objects.filter(id=i_id).first()
    if db:
        db.status = -1
        model_manager.save_ignore(db)


@api_func_anonymous
def api_kpi_save(request, from_date, to_date, i_pv, i_users, i_remain, i_id):
    app = api_helper.get_session_app(request)
    user = model_manager.get_user(api_helper.get_session_user(request))
    if i_id:
        db = KPIPeriod.objects.filter(id=i_id).first()
        if not db:
            return
    else:
        db = KPIPeriod(app_id=app)
    db.from_date = from_date
    db.to_date = to_date
    db.pv = i_pv
    db.users = i_users
    db.remains = i_remain
    editors = db.editors.split(',') if db.editors else []
    if str(user.id) not in editors:
        editors.append(str(user.id))
        db.editors = ','.join(editors)
    model_manager.save_ignore(db)


def get_kpi_periods(app):
    return [x.json for x in KPIPeriod.objects.filter(app=app, status=0).order_by("-pk")]


def get_kpi(app_id, period=None):
    query = KPIPeriod.objects.filter(app_id=app_id, status=0).order_by("-pk")
    if period:
        query = query.filter(id=period)

    period = query.first()

    if not period:
        return {
            'period': None
        }

    rows = []
    rows_dict = dict()
    users = dict()
    for x in UserDailyStat.objects.filter(report_date__range=(period.from_date, period.to_date),
                                          app_id=app_id, user__status=0).order_by('report_date'):
        if x.report_date not in rows_dict:
            the_row = {'date': x.report_date}
            rows.append(the_row)
            rows_dict[x.report_date] = the_row

        the_row = rows_dict[x.report_date]
        the_row['pv_%s' % x.user_id] = x.qq_pv + x.wx_pv
        the_row['users_%s' % x.user_id] = x.qq_install + x.wx_install
        the_row['remain_%s' % x.user_id] = x.qq_remain + x.wx_remain
        if x.user_id not in users:
            users[x.user_id] = x.user.name

    for idx, x in enumerate(AppDailyStat.objects.filter(report_date__range=(period.from_date, period.to_date),
                                                        app_id=app_id).order_by('report_date')):
        the_row = rows_dict.get(x.report_date)
        if the_row is None:
            logger.warn('error get row %s %s' % (app_id, x.report_date))
        else:
            the_row['pv'] = x.wx_pv + x.qq_pv
            the_row['users'] = x.qq_install + x.wx_install
            the_row['remain'] = x.qq_remain + x.wx_remain

    return {
        'period': period.json,
        'rows': rows,
        'users': list(users.items()),
    }
