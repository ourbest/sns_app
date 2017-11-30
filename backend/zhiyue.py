import re
from datetime import datetime, timedelta

from dj import times
from dj.utils import api_func_anonymous
from django.db import connections
from django.db.models import Count
from django.http import HttpResponse
from django.utils import timezone

from backend import api_helper, model_manager, stats
from backend.api_helper import get_session_app
from backend.models import AppUser, AppDailyStat, UserDailyStat, App, DailyActive
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, AdminPartnerUser, CouponInst, ItemMore, \
    ZhiyueUser


@api_func_anonymous
def user_share(i_uid, request):
    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id=i_uid, article__partnerId=get_session_app(request)).order_by("-time")[0:50]

    return [{
        'text': x.text,
        'time': times.to_str(x.time),
        'name': x.user.name,
        'url': find_url(x) if x.article else '',
        'itemId': x.article.item_id if x.article else 0,
        'clipId': x.article.item.clipId if x.article else 0,
        'title': x.article.item.title if x.article else '',
    } for x in data]


def get_user_share_items(app_id, uids):
    data = ShareArticleLog.objects.using('zhiyue').select_related('user', 'article', 'article__item').filter(
        user_id__in=uids, article__partnerId=app_id).order_by("-time")[0:50]


def find_url(x):
    # url = re.findall('https?://.+/weizhan/article/\d+/\d+/\d+', text)
    # return url[0] if url else ''
    return 'http://www.cutt.com/weizhan/article/%s/%s/%s' % (
        x.article.item.clipId, x.article.item_id, x.article.partnerId)


@api_func_anonymous
def get_url_title(url):
    u = re.findall('https?://.+/weizhan/article/\d+/(\d+)/(\d+)', url)
    if u:
        (article_id, app_id) = u[0]
        more = model_manager.query(ItemMore).filter(itemId=article_id, appId=app_id).first()
        if more and more.title:
            return more.title
        item = model_manager.query(ClipItem).filter(itemId=article_id).first()
        return item.title if item.title else '(无标题)'
    return None


@api_func_anonymous
def count_weizhan(email, request):
    the_user = api_helper.get_login_user(request, email)
    cutt_users = [the_user.appuser_set.all()]
    model_manager.query(WeizhanCount)
    pass


@api_func_anonymous
def count_user_sum(email, date, request):
    """
    name = models.CharField(max_length=255)
    userId = models.IntegerField(primary_key=True)
    deviceUserId = models.IntegerField()
    partnerId = models.IntegerField()
    shareNum = models.IntegerField()
    weizhanNum = models.IntegerField()
    downPageNum = models.IntegerField()
    appUserNum = models.IntegerField()
    commentNum = models.IntegerField()
    agreeNum = models.IntegerField()
    viewNum = models.IntegerField()
    secondShareNum = models.IntegerField()
    userType = models.IntegerField(help_text='userType=1 内容产生用户 ，userType=2 内容传播用户')
    time = models.DateTimeField()
    :param email:
    :param date:
    :param request:
    :return:
    """
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    the_user = api_helper.get_login_user(request, email)
    return stats.get_user_stat(date, the_user)


@api_func_anonymous
def get_user_majia(email, request):
    user = api_helper.get_login_user(request, email)

    cutt = {x.user_id: x.user.name for x in model_manager.query(AdminPartnerUser).select_related('user')
        .filter(loginUser=user.email, partnerId=get_session_app(request))}

    for x in user.appuser_set.filter(type__gte=0):
        if x.cutt_user_id in cutt:
            if x.name != cutt[x.cutt_user_id]:
                x.name = cutt[x.cutt_user_id]
                x.save()
            del cutt[x.cutt_user_id]

    for k, v in cutt.items():
        AppUser(user=user, name=v if v else k, type=2, cutt_user_id=k).save()

    return [{
        'id': x.cutt_user_id,
        'name': x.name,
        'type': x.type,
    } for x in user.appuser_set.filter(type__gte=0)]


@api_func_anonymous
def sum_team_dist(date, request, include_sum):
    app = get_session_app(request)
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    return stats.app_daily_stat(app, date, include_sum)


def show_open_link(request):
    url = request.GET.get('url')

    if not url:
        url = 'comcuttapp965004://article?id=31412177424'
    else:
        info = re.findall(r'https?://.+?/weizhan/article/\d+/(\d+)/(\d+)', url)
        if info:
            [(aid, app)] = info
            url = 'comcuttapp%s://article?id=%s' % (app, aid)

    return HttpResponse('<a style="font-size: 10em" href="%s">open</a>' % url)


@api_func_anonymous
def app_report(from_date, to_date, i_app):
    if not from_date or not to_date:
        return

    return [{
        'date': x.report_date,
        'qq_pv': x.qq_pv,
        'qq_down': x.qq_down,
        'qq_install': x.qq_install,
        'wx_pv': x.wx_pv,
        'wx_down': x.wx_down,
        'wx_install': x.wx_install,
    } for x in AppDailyStat.objects.filter(report_date__range=(from_date, to_date),
                                           app_id=i_app).order_by("-pk")]


@api_func_anonymous
def app_report_user(from_date, to_date):
    if not from_date or not to_date:
        return

    return [{
        'date': x.report_date,
        'app': x.app.app_name,
        'name': x.user.name,
        'qq_pv': x.qq_pv,
        'qq_down': x.qq_down,
        'qq_install': x.qq_install,
        'wx_pv': x.wx_pv,
        'wx_down': x.wx_down,
        'wx_install': x.wx_install,
    } for x in UserDailyStat.objects.filter(report_date__range=(from_date, to_date))
        .select_related('app', 'user').order_by("-pk")]


@api_func_anonymous
def get_app_stat():
    return do_get_app_stat()


@api_func_anonymous
def get_stat_before_days(i_days):
    if not i_days:
        i_days = 1

    cnt = App.objects.filter(stage__in=('分发期', '留守期')).count()

    return sorted([{
        'app_id': x.app.app_id,
        'app_name': x.app.app_name,
        'iphone': x.iphone,
        'android': x.android,
    } for x in
        DailyActive.objects.filter(created_at__lt=timezone.now() - timedelta(days=i_days)).select_related(
            "app").order_by(
            "-pk")[:cnt]], key=lambda x: x['app_id'])


@api_func_anonymous
def get_active_detail(app_id, i_today):
    query = DailyActive.objects.filter(app_id=app_id).extra(
        where=[
            'created_at>current_date' if i_today == 1
            else 'created_at between current_date - interval 1 day and current_date'
        ])

    return [{
        'time': times.to_str(x.created_at, '%H:%M'),
        'iphone': x.iphone,
        'android': x.android,
        'total': x.total
    } for x in query]


def do_get_app_stat():
    apps = {str(x.app_id): x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}
    query = '''
        select appId,platform,count(*) from pojo_ZhiyueUser where platform in (%s)
         and appId in (%s)
         and lastActiveTime > current_date
        group by appId, platform
    ''' % ('\'iphone\', \'android\'', ','.join(apps.keys()))
    data = []

    values = dict()
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            sum = values.get(row[0])
            if not sum:
                sum = {
                    'app_id': row[0],
                    'app_name': apps[row[0]],
                }
                values[row[0]] = sum
                data.append(sum)

            sum['%s' % row[1]] = row[2]

    return sorted(data, key=lambda x: int(x['app_id']))


@api_func_anonymous
def get_new_device():
    apps = {str(x.app_id): x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}
    query = '''
        select appId,platform,count(*) from pojo_ZhiyueUser where platform in (%s)
         and appId in (%s)
         and createTime > current_date
        group by appId, platform
    ''' % ('\'iphone\', \'android\'', ','.join(apps.keys()))
    data = []

    values = dict()
    with connections['zhiyue'].cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            sum = values.get(row[0])
            if not sum:
                sum = {
                    'app_id': row[0],
                    'app_name': apps[row[0]],
                }
                values[row[0]] = sum
                data.append(sum)

            sum['%s' % row[1]] = row[2]

    return sorted(data, key=lambda x: int(x['app_id']))


@api_func_anonymous
def get_offline_ids(request, date):
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date[0:10], '%Y-%m-%d'))
    app = api_helper.get_session_app(request)

    # today = timezone.now().date()
    query = model_manager.query(CouponInst).filter(partnerId=app, status=1,
                                                   useDate__range=(date, date + timedelta(days=1)))
    return [x.userId for x in query] if app else ""


@api_func_anonymous
def get_coupon_details():
    date = times.localtime(datetime.now().replace(hour=0, second=0, minute=0, microsecond=0))
    yesterday = date - timedelta(days=1)
    apps = {x.app_id: x.app_name for x in App.objects.filter(stage__in=('分发期', '留守期'))}

    query = model_manager.query(CouponInst).filter(partnerId__in=apps.keys(), status=1,
                                                   useDate__range=(date, date + timedelta(days=1))).values(
        'partnerId').annotate(total=Count('userId')).order_by('-total')

    ids = [x['partnerId'] for x in query]

    rates = dict()

    for app_id in ids:
        user_ids = [x.userId for x in model_manager.query(CouponInst).filter(partnerId=app_id,
                                                                             status=1,
                                                                             useDate__range=(
                                                                                 yesterday,
                                                                                 yesterday + timedelta(days=1)))]
        rates[app_id] = int(model_manager.query(ZhiyueUser).filter(userId__in=user_ids,
                                                                   lastActiveTime__gt=date).count() / len(
            user_ids) * 100)

    return [{
        'app_id': x['partnerId'],
        'app_name': apps[x['partnerId']],
        'today': x['total'],
        'remain': '%s%%' % rates[x['partnerId']],
    } for x in query]
