from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum

from backend import model_manager, api_helper, hives, remains
from backend.models import ChannelUser, RuntimeData
from backend.zhiyue_models import ZhiyueUser


@api_func_anonymous
def api_channel_stats(date):
    """
    激活渠道的统计数据
    :return:
    """
    date = model_manager.today() if not date else model_manager.get_date(date)

    app_names = model_manager.app_names()
    ret = list(ChannelUser.objects.values('app_id', 'channel').filter(
        created_at__gt=date).annotate(total=Count('user_id')))
    for x in ret:
        x['app_name'] = app_names.get(x['app_id'])
    return ret

    # query = 'select * from pojo_ZhiyueUser where source!= \'0000\' and source is not null and source != \'\' ' \
    #         'and createTime > current_date '


@api_func_anonymous
def api_channel_details(request, date, channel):
    app = api_helper.get_session_app(request)
    query = ChannelUser.objects.filter(app_id=app)
    from_date = model_manager.get_date(date) if date else model_manager.today()
    query = query.filter(created_at__range=(from_date, from_date + timedelta(1)))
    if channel:
        query = query.filter(channel=channel)
    return [x.json for x in query]


@api_func_anonymous
def api_channel_remain(request, date, channel):
    app = api_helper.get_session_app(request)

    if date:
        from_date = model_manager.get_date(date)
        date_str = 'created_at between \'%s\' and \'%s\'' % (from_date.strftime('%Y-%m-%d'),
                                                             from_date.strftime('%Y-%m-%d 23:59'))
    else:
        from_date = model_manager.today() - timedelta(10)
        date_str = 'created_at > \'%s\'' % from_date.strftime('%Y-%m-%d')

    channel_str = '' if not channel else 'and channel=\'%s\'' % channel

    sql = 'select date(created_at) date, channel, count(user_id) total, sum(remain) remain from backend_channeluser ' \
          'where app_id=%s and %s %s group by channel, date(created_at) order by date desc' % (
              app, date_str, channel_str)

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{'date': x[0], 'channel': x[1], 'total': x[2], 'remain': x[3]} for x in rows]


@api_func_anonymous
def api_channel_names(request):
    return list(ChannelUser.objects.values('channel').filter(created_at__gt=model_manager.yesterday(),
                                                             app_id=api_helper.get_session_app(request)).annotate(
        total=Count('user_id')))


@api_func_anonymous
def api_get_ad_channels():
    return get_ad_channels()


def get_ad_channels():
    cfg = RuntimeData.objects.filter(name='ad_channels').first()
    return cfg.value if cfg else ''


@api_func_anonymous
def api_set_ad_channels(channels):
    cfg = RuntimeData.objects.filter(name='ad_channels').first()
    if not cfg:
        cfg = RuntimeData('ad_channels')
    else:
        if cfg.value == channels:
            return channels

    cfg.value = channels
    cfg.save()
    return channels


@api_func_anonymous
def api_weekly_report(i_week):
    date_range = model_manager.plus_week(i_week)
    app_names = model_manager.app_names()
    channels = dict()
    for x in get_ad_channels().split('\n'):
        arr = x.split(' ')
        channels[arr[0]] = arr[-1]

    ret = list(ChannelUser.objects.filter(created_at__range=date_range,
                                          channel__in=channels.keys()).values(
        'app_id', 'channel').annotate(total=Count('user_id'),
                                      remain=Sum('remain')).order_by('channel'))

    ava_channels = []
    for x in ret:
        x['app_name'] = app_names[x['app_id']][:-3]
        x['channel'] = channels[x['channel']]
        if x['channel'] not in ava_channels:
            ava_channels.append(x['channel'])

    return {
        'channels': ava_channels,
        'dates': {
            'from': date_range[0].strftime('%Y-%m-%d'),
            'to': date_range[1].strftime('%Y-%m-%d'),
        },
        'data': ret,
    }


# ================= methods ================

def sync_remain_from_hive(date):
    date = model_manager.get_date(date)
    for app in model_manager.get_dist_apps():
        ids = [x.user_id for x in ChannelUser.objects.filter(app=app, remain=0,
                                                             created_at__range=(date, date + timedelta(1)))]
        if ids:
            remain_ids = remains.get_remain_ids(app.app_id, ids, date + timedelta(1), device=True)
            ChannelUser.objects.filter(user_id__in=remain_ids).update(remain=1)


def sync_all_from_hive():
    for app in model_manager.get_dist_apps():
        today = model_manager.today()
        remains.remain_obj(ChannelUser, app.app_id, (today - timedelta(90), today))
