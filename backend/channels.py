from dj.utils import api_func_anonymous
from django.db.models import Count

from backend import model_manager
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
