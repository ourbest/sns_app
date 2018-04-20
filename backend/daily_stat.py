import json
import re
from collections import defaultdict
from datetime import timedelta, datetime

from dj import times
from django.db import connections

from django.db.models import Count, Sum, Max
from django_rq import job
from logzero import logger

from backend import model_manager
from backend.models import ItemDeviceUser, UserDailyStat, AppDailyStat, User, App, OfflineUser
from backend.zhiyue_models import OfflineDailyStat, UserRewardGroundHistory, UserRewardHistory, WithdrawApply


def make_daily_remain(app_id, date):
    the_date = model_manager.get_date(date)
    qq_remain_total = 0
    wx_remain_total = 0
    for user in ItemDeviceUser.objects.filter(app_id=app_id,
                                              created_at__range=[the_date,
                                                                 the_date + timedelta(days=1)]).values(
        'owner_id',
        'type'
    ).annotate(total=Count('user_id'), remain=Sum('remain')):
        if user['type'] == 0:
            UserDailyStat.objects.filter(report_date=date, user_id=user['owner_id']).update(qq_remain=user['remain'])
            qq_remain_total += user['remain']
        elif user['type'] == 1:
            UserDailyStat.objects.filter(report_date=date, user_id=user['owner_id']).update(wx_remain=user['remain'])
            wx_remain_total += user['remain']

    AppDailyStat.objects.filter(report_date=date, app_id=app_id).update(wx_remain=wx_remain_total,
                                                                        qq_remain=qq_remain_total)


def calc_save_remain():
    logger.info('同步留存数据')
    to_time = datetime.now()
    from_time_str = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')
    create_range = ((to_time - timedelta(days=2)).strftime('%Y-%m-%d'), from_time_str)
    for app in model_manager.get_dist_apps():
        qq_cnt = ItemDeviceUser.objects.filter(type=0, app=app, created_at__range=create_range, remain=1).count()
        wx_cnt = ItemDeviceUser.objects.filter(type=1, app=app, created_at__range=create_range, remain=1).count()

        report_date = (to_time - timedelta(days=1)).strftime('%Y-%m-%d')  # 留存记录是针对前一天的
        AppDailyStat.objects.filter(report_date=report_date, app=app).update(qq_remain=qq_cnt, wx_remain=wx_cnt)

        for user in User.objects.filter(app=app, status=0):
            qq_cnt = ItemDeviceUser.objects.filter(type=0, owner=user, created_at__range=create_range).count()
            wx_cnt = ItemDeviceUser.objects.filter(type=1, owner=user, created_at__range=create_range).count()
            UserDailyStat.objects.filter(report_date=report_date, user=user).update(
                qq_remain=qq_cnt, wx_remain=wx_cnt)


def re_calc_off():
    for i in range(0, 14):
        _re_calc((datetime.now() - timedelta(days=i)).strftime('%Y-%m-%d'))


def _re_calc(the_date):
    stat_date_from = '\'%s 00:00:00\'' % the_date
    stat_date_to = '\'%s 23:59:59\'' % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])
    query = '''
        select partnerId, count(*) from partner_CouponInst 
        where useDate between %s and %s AND 
        partnerId in (%s) GROUP BY partnerId
        ''' % (stat_date_from, stat_date_to, ids)

    date_str = times.to_date_str(datetime.now() - timedelta(days=1), "%Y-%m-%d") if not the_date else the_date

    # 使用量
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [app_id, cnt] in rows:
            try:
                row = OfflineDailyStat.objects.filter(app_id=app_id, stat_date=date_str).update(user_num=cnt)
                if row == 0:
                    OfflineDailyStat(app_id=app_id, stat_date=date_str, user_num=cnt).save()
            except:
                pass

        query_q = '''
            select partnerId, useNum, extInfo, remainDay from partner_ShopCouponStatSum
            WHERE useDate = '%s' AND partnerId in (%s)
            ''' % (the_date, ids)

        cursor.execute(query_q)
        rows = cursor.fetchall()
        total_map = dict()
        remain_map = dict()

        if len(rows):
            for [app_id, cnt, ext_info, remain_day] in rows:
                percent = _get_percent(ext_info)

                if app_id not in total_map:
                    total_map[app_id] = 0
                    remain_map[app_id] = 0

                total_map[app_id] += apps[app_id].price * cnt * percent
                if remain_day:
                    day_ = re.split(';', remain_day)[0]
                    if day_:
                        remain_cnt = int(re.split('-', day_)[1])
                        remain_map[app_id] += remain_cnt

            for app_id in apps:
                total = total_map[app_id]
                OfflineDailyStat.objects.filter(app_id=app_id, stat_date=date_str).update(user_cost=total,
                                                                                          total_cost=total,
                                                                                          remain=remain_map[app_id])


def save_bonus_daily_stat(date=model_manager.yesterday()):
    if isinstance(date, str):
        date = model_manager.get_date(date)

    for x in OfflineUser.objects.filter(created_at__range=(date, date + timedelta(1))).values(
            'app_id').annotate(total=Sum('bonus_pick')):
        OfflineDailyStat.objects.filter(app_id=x['app_id'],
                                        stat_date=date.strftime('%Y-%m-%d')).update(user_bonus_num=x['total'])

    for x in OfflineUser.objects.filter(withdraw_time__range=(date, date + timedelta(1))).values(
            'app_id').annotate(total=Sum('bonus_withdraw'), num=Count('withdraw_time')):
        OfflineDailyStat.objects.filter(app_id=x['app_id'],
                                        stat_date=date.strftime('%Y-%m-%d')).update(user_cash_num=x['num'],
                                                                                    bonus_cash=x['total'])

    for x in OfflineUser.objects.filter(bonus_time__range=(date, date + timedelta(1))).values(
            'app_id').annotate(total=Sum('bonus_amount')):
        OfflineDailyStat.objects.filter(app_id=x['app_id'],
                                        stat_date=date.strftime('%Y-%m-%d')).update(user_bonus_got=x['total'])


def save_bonus_info(until=model_manager.yesterday()):
    ids = [x.userId for x in model_manager.query(UserRewardGroundHistory).filter(createTime__gt=until,
                                                                                 type=-1)]

    if ids:
        OfflineUser.objects.filter(user_id__in=ids, bonus_view=0).update(bonus_view=1)

    # 红包步骤
    for x in model_manager.query(UserRewardGroundHistory).filter(createTime__gt=until,
                                                                 type__gte=0) \
            .values('userId').annotate(amount=Sum('amount'), current=Max('type')):
        if x['amount'] > 0:
            OfflineUser.objects.filter(user_id=x['userId']).update(bonus_step=x['current'],
                                                                   bonus_pick=1,
                                                                   bonus_amount=x['amount'])

    # 获得红包信息
    for x in model_manager.query(UserRewardHistory).filter(createTime__gt=until,
                                                           source='groundPush'):
        OfflineUser.objects.filter(user_id=x.userId).update(bonus_got=1,
                                                            bonus_pick=1,
                                                            bonus_amount=x.amount,
                                                            bonus_time=x.createTime)
    # 提款信息
    for x in model_manager.query(WithdrawApply).filter(finishTime__gt=until):
        OfflineUser.objects.filter(user_id=x.userId).update(bonus_withdraw=float(x.amount) * 100,
                                                            withdraw_time=x.finishTime)


@job
def make_offline_stat(the_date):
    stat_date = datetime.now()

    if not the_date:
        the_date = 'current_date'
    else:
        stat_date = datetime.strptime(the_date, '%Y-%m-%d')
        the_date = "'%s'" % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])

    # 补红包打开数字
    bonus_query = '''
    select partnerId, count(*) from pojo_ZhiyueUser u, partner_UserRewardHistory c 
    where u.createTime between %s - interval 2 day and %s - interval 1 day
    and u.userId = c.userId and partnerId in (%s) and c.source='groundPush' group by partnerId
    ''' % (the_date, the_date, ids)
    # 补留存率
    # 补结算数字
    query = '''
    select partnerId, useNum, extInfo, remainDay from partner_ShopCouponStatSum
    WHERE useDate = %s - INTERVAL 2 DAY AND partnerId in (%s)
    ''' % (the_date, ids)
    # 补红包补贴
    op_bonus_query = '''
    SELECT partnerId, sum(amount)  FROM partner_RedCouponBonus
    WHERE partnerId = 1564403 AND rewardDate = %s - INTERVAL 2 DAY
    GROUP BY partnerId
    ''' % the_date
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        values = defaultdict(dict)
        for [app_id, cnt, ext_info, remain_day] in rows:
            percent = _get_percent(ext_info)

            total = apps[app_id].price * cnt * percent
            r = values[app_id]
            r['total'] = r.get('total', 0) + total
            remain_cnt = 0

            if remain_day:
                day_ = re.split(';', remain_day)[0]
                if day_:
                    remain_cnt = int(re.split('-', day_)[1])

            r['remain'] = r.get('remain', 0) + remain_cnt

        cursor.execute(bonus_query)
        rows = cursor.fetchall()

        for [app_id, cnt] in rows:
            values[app_id]['open'] = cnt

        cursor.execute(op_bonus_query)
        rows = cursor.fetchall()

        for [app_id, amount] in rows:
            values[app_id]['bonus'] = amount
    for stat in OfflineDailyStat.objects.filter(stat_date=times.to_date_str(stat_date - timedelta(days=2),
                                                                            "%Y-%m-%d")):
        r = values[stat.app_id]
        stat.user_bonus_num = r.get('open', 0)
        stat.remain = r.get('remain', 0)
        stat.user_cost = r.get('total', 0)
        stat.bonus_cost = r.get('bonus', 0)
        stat.total_cost = stat.bonus_cost + stat.user_cost
        try:
            stat.save(force_update=True)
        except:
            pass


def _get_percent(ext_info):
    low_cnt = int(json.loads(ext_info).get('LowQualityCnt', 0))
    percent = 1
    if low_cnt == 1:
        percent = 0.95
    elif low_cnt == 2:
        percent = 0.9
    elif low_cnt == 3:
        percent = 0.8
    elif low_cnt == 4:
        percent = 0.5
    elif low_cnt >= 5:
        percent = 0
    return percent


@job
def do_offline_stat(the_date):
    stat_date_from = 'current_date - interval 1 day'
    stat_date_to = 'current_date'

    if the_date:
        stat_date_from = '\'%s 00:00:00\'' % the_date
        stat_date_to = '\'%s 23:59:59\'' % the_date

    apps = {x.app_id: x for x in App.objects.filter(offline=1)}
    ids = ','.join([str(x) for x in apps.keys()])
    query = '''
    select partnerId, count(*) from partner_CouponInst 
    where useDate between %s and %s AND 
    partnerId in (%s) GROUP BY partnerId
    ''' % (stat_date_from, stat_date_to, ids)

    date_str = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d") if not the_date else the_date

    # 使用量
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for [app_id, cnt] in rows:
            try:
                OfflineDailyStat(app_id=app_id, stat_date=date_str, user_num=cnt).save()
                save_bonus_daily_stat()
            except:
                pass

    make_offline_stat(the_date)
    save_bonus_daily_stat()
