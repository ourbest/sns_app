from datetime import timedelta

from dj.utils import api_func_anonymous
from django.db.models import Count

from backend import model_manager, api_helper
from backend.models import ChannelUser
from backend.zhiyue_models import ZhiyueUser


@api_func_anonymous
def api_channel_stats(date):
    """
    激活渠道的统计数据
    :return:
    """
    date = model_manager.today() if not date else model_manager.get_date(date)

    app_names = model_manager.app_names()
    ret = list(model_manager.query(ZhiyueUser).values('appId', 'source').filter(
        appId__in=app_names.keys(), createTime__gt=date,
        platform='android').exclude(source__in=('', '0000'),
                                    source__isnull=True).annotate(
        total=Count('userId')))
    for x in ret:
        x['app_name'] = app_names.get(int(x['appId']), 'app%s' % x['appId'])
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
def api_channel_names(request):
    return list(ChannelUser.objects.values('channel').filter(created_at__gt=model_manager.yesterday(),
                                                             app_id=api_helper.get_session_app(request)).annotate(
        total=Count('user_id')))
