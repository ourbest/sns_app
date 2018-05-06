"""
线上相关API
"""
from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db.models import Count, Sum

from backend import dates, model_manager
from backend.models import AppDailyStat, ItemDeviceUser


@api_func_anonymous
def api_stat():
    return [x.json for x in
            AppDailyStat.objects.filter(report_date__gte=(dates.today() - timedelta(14)).strftime('%Y-%m-%d')).order_by(
                "-report_date")]


@api_func_anonymous
def api_today(date):
    date = dates.today() if not date else dates.get_date(date)
    apps = {x.app_id: x.app_name[:-3] for x in model_manager.get_dist_apps()}
    stat = list(ItemDeviceUser.objects.filter(created_at__range=(date, date + timedelta(1))).values('app_id').annotate(
        users=Count('user_id'), remain=Sum('remain')))
    for x in stat:
        x['app_name'] = apps[x['app_id']]
    return stat


@api_func_anonymous
def api_weekly(date):
    date = dates.today() - timedelta(8) if not date else dates.get_date(date)
    from_date = date.strftime('%Y-%m-%d')
    to_date = (date + timedelta(6)).strftime('%Y-%m-%d')
    apps = {x.app_id: x.app_name[:-3] for x in model_manager.get_dist_apps()}
    stat = list(AppDailyStat.objects.filter(report_date__range=(from_date, to_date)).values('app_id').annotate(
        qq_users=Sum('qq_install'), wx_users=Sum('wx_install'), qq_pv=Sum('qq_pv'), wx_pv=Sum('wx_pv'),
        wx_remain=Sum('wx_remain'), qq_remain=Sum('qq_remain')))
    for x in stat:
        x['app_name'] = apps[x['app_id']]
    return stat
