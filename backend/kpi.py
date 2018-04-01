from backend.models import KPIPeriod, UserDailyStat


def get_kpi_periods(app):
    return [x.json for x in KPIPeriod.objects.filter(app=app).order_by("-pk")]


def get_kpi(app_id, period):
    query = KPIPeriod.objects.filter(app_id=app_id).order_by("-pk")
    if period:
        query = query.filter(id=period)

    period = query.first()
    UserDailyStat.objects.filter(report_date__range=(period.from_date, period.to_date), app_id=app_id)
    return {
        'period': period
    }
