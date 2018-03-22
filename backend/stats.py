from datetime import timedelta

from dj.utils import api_func_anonymous

from backend import api_helper
from backend.jobs import do_get_item_stat_values, do_gen_daily_report
from backend.models import DistArticle, DistArticleStat
from backend.stat_utils import to_stat_json
from backend.zhiyue_models import ShareArticleLog

import statsd

client = statsd.StatsClient('10.9.88.19')


def get_user_share(app_id, user, date):
    uids = {x.cutt_user_id for x in user.appuser_set.filter(type__gte=0)}

    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id__in=uids, article__partnerId=app_id).filter(time__range=(date.date(),
                                                                         date.date() + timedelta(days=1)))[0:50]

    return {x.article.item_id for x in data if x.article}


@api_func_anonymous
def gen_daily_report():
    do_gen_daily_report.delay()


@api_func_anonymous
def get_item_stat_values(app):
    """
    统计7天内的文章
    :return:
    """
    do_get_item_stat_values.delay(app)


@api_func_anonymous
def team_articles(request, i_page, i_size, url):
    item_id = None
    if url:
        item_id = api_helper.parse_item_id(url)

    size = i_size if i_size else 50
    offset = (i_page - 1) * size if i_page else 0
    app = api_helper.get_session_app(request)
    if not item_id:
        articles = DistArticle.objects.filter(app_id=app).order_by("-started_at")[offset:size + offset]
        total = DistArticle.objects.filter(app_id=app).count()
    else:
        articles = DistArticle.objects.filter(app_id=app, item_id=item_id)
        total = len(articles)

    stat_data = {x.article_id: x for x in DistArticleStat.objects.filter(article_id__in=[x.id for x in articles])}

    return {
        'total': total,
        'items': [to_stat_json(x, stat_data.get(x.id)) for x in articles]
    }
