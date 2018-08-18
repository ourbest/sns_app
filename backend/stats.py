from datetime import timedelta, datetime

from dj import times
from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count

from backend import api_helper, model_manager
from backend.models import DistArticle, DistArticleStat, ItemDeviceUser, User
from backend.stat_utils import to_stat_json, classify_data_app
from backend.zhiyue_models import ShareArticleLog


# import statsd
#
# client = statsd.StatsClient('10.9.88.19')


def get_user_share(app_id, user, date):
    uids = {x.cutt_user_id for x in user.appuser_set.filter(type__gte=0)}

    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id__in=uids, article__partnerId=app_id).filter(time__range=(date.date(),
                                                                         date.date() + timedelta(days=1)))[0:50]

    return {x.article.item_id for x in data if x.article}


@api_func_anonymous
def gen_daily_report():
    from backend.jobs import do_gen_daily_report
    do_gen_daily_report.delay()


@api_func_anonymous
def get_item_stat_values(app):
    """
    统计7天内的文章
    :return:
    """
    from backend.jobs import do_get_item_stat_values
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


@api_func_anonymous
def team_category(request):
    """
    分类效果图
    :param request:
    :return:
    """
    app = api_helper.get_session_app(request)
    query = """
    select category, sum(`qq_user`+wx_user) users, sum(qq_pv+wx_pv) pv from backend_distarticle a, backend_distarticlestat s
    where a.`last_started_at` > current_date - interval 7 day and a.app_id={} and s.`article_id` = a.id
    group by category order by pv desc
    """.format(app)

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        return [{
            'category': category,
            'users': users,
            'pv': pv
        } for [category, users, pv] in rows]


@api_func_anonymous
def item_user_loc(request):
    app = api_helper.get_session_app(request)
    today = times.localtime(datetime.now().replace(hour=0, minute=0, second=0, microsecond=0))
    return [{
        'city': x['city'][1:-1].split(', ')[-1],
        'cnt': x['cnt']
    } for x in ItemDeviceUser.objects.filter(app_id=app,
                                             created_at__gt=today - timedelta(days=7)).values('city').annotate(
        cnt=Count('city')).order_by("-cnt")]


def classify_data(request):
    """
    根据文章的类型查看分发的效果
    :return:
    """
    app = api_helper.get_session_app(request)
    return classify_data_app(app)


@api_func_anonymous
def article_remain(request, from_date, to_date):
    from_date = from_date[0:10]
    to_date = to_date[0:10]
    app = api_helper.get_session_app(request)
    query = """
    select item_id, owner_id, count(*), count(case when remain=1 then 1 else null end) from backend_itemdeviceuser 
    where app_id={} 
    and created_at between '{}' and '{}' + interval 1 DAY group by item_id, owner_id order by count(*) DESC
    """.format(app, from_date, to_date)

    with connection.cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()

    item_ids = {x[0] for x in rows}
    articles = {x.item_id: x.title for x in DistArticle.objects.filter(item_id__in=item_ids)}
    ret = list()

    users = {u.id: u for u in User.objects.filter(app_id=app)}

    untitled = dict()

    for x in rows:
        if x[0] in articles:
            if x[1] not in users:
                users[x[1]] = model_manager.get_user_by_id(x[1])
            ret.append({
                'title': articles[x[0]],
                'item_id': x[0],
                'name': users.get(x[1]).name,
                'users': x[2],
                'remain': x[3],
            })
        else:
            if x[1] not in untitled:
                untitled[x[1]] = {
                    'title': '(其它文章)',
                    'item_id': 0,
                    'name': users.get(x[1]).name,
                    'users': 0,
                    'remain': 0,
                }

            s = untitled[x[1]]
            s['users'] += x[2]
            s['remain'] += x[3]

    return ret + list(untitled.values())


@api_func_anonymous
def sum_daily_click():
    query = ("""
replace into backend_weizhanclickdaily (app_id,
                                        stat_date,
                                        item_id,
                                        user_id,
                                        task_id,
                                        qq_id,
                                        platform,
                                        cnt,
                                        down_page_cnt)
select app_id,
       current_date - interval 1 day,
       item_id,
       uid,
       tid,
       if(qq = '', 0, qq),
       platform,
       count(*),
       0
from backend_weizhanclick
where ts between current_date - interval 1 day and current_date and uid in (select cutt_user_id from backend_appuser)
group by app_id, item_id, uid, tid, qq, platform
    """,
             'update backend_weizhanclickdaily d, backend_appuser u set sns_type = u.type '
             'where d.user_id = u.cutt_user_id and d.stat_date = current_date - interval 1 day',
             """
replace into backend_weizhandlclickdaily (app_id, stat_date, item_id, user_id, task_id, qq_id, platform, type, cnt)
select c.app_id,
       current_date - interval 1 day ,
       item_id,
       uid,
       task_id,
       if(qq = '', 0, qq),
       platform,
       type,
       count(*)
from backend_weizhandownclick c
where ts between current_date-interval 1 day and current_date
  and uid in (select cutt_user_id from backend_appuser)
group by c.app_id, item_id, uid, task_id, qq, platform, type
             """,
             'update backend_weizhandlclickdaily d, backend_appuser u set sns_type = u.type '
             'where d.user_id = u.cutt_user_id and d.stat_date = current_date - interval 1 day',
             """
update backend_weizhanclickdaily c,
(select app_id, item_id, stat_date, task_id, qq_id, platform, sum(cnt) s
from backend_weizhandlclickdaily
where stat_date = current_date - interval 1 day 
group by app_id, item_id, stat_date, task_id, qq_id, platform) d
set c.down_page_cnt = d.s
where c.app_id = d.app_id and c.item_id = d.item_id
and c.stat_date = d.stat_date and c.task_id = d.task_id and c.qq_id = d.qq_id
and c.platform = d.platform
             """
             )

    with connection.cursor() as cursor:
        for q in query:
            cursor.execute(q)
