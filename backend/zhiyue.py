import re
from datetime import datetime

from dj import times
from dj.utils import api_func_anonymous
from django.http import HttpResponse

from backend import api_helper, model_manager
from backend.api_helper import get_session_app
from backend.models import AppUser, User
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, HighValueUser, AdminPartnerUser


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


def find_url(x):
    # url = re.findall('https?://.+/weizhan/article/\d+/\d+/\d+', text)
    # return url[0] if url else ''
    return 'http://www.cutt.com/weizhan/article/%s/%s/%s' % (
        x.article.item.clipId, x.article.item_id, x.article.partnerId)


@api_func_anonymous
def get_url_title(url):
    u = re.findall('https?://.+/weizhan/article/\d+/(\d+)/\d+', url)
    if u:
        article_id = u[0]
        item = ClipItem.objects.using('zhiyue').filter(itemId=article_id).first()
        return item.title
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
    the_user = api_helper.get_login_user(request, email)
    return get_user_stat(date, the_user)


def get_user_stat(date, the_user):
    cutt_users = list(the_user.appuser_set.all())
    cutt_user_dict = {x.cutt_user_id: x for x in cutt_users}
    date = times.localtime(
        datetime.now().replace(hour=0, second=0,
                               minute=0, microsecond=0) if not date else datetime.strptime(date, '%Y-%m-%d'))
    return [{
        'id': x.userId,
        'name': x.name,
        'type': '微信' if 1 == cutt_user_dict.get(x.userId).type else 'QQ',
        'share': x.shareNum,
        'weizhan': x.weizhanNum,
        'download': x.downPageNum,
        'reshare': x.secondShareNum,
        'users': x.appUserNum,
    } for x in model_manager.query(HighValueUser).filter(partnerId=the_user.app_id, time=date, userType=2,
                                                         userId__in=[x.cutt_user_id for x in cutt_users])]


@api_func_anonymous
def get_user_majia(request):
    user = api_helper.get_login_user(request)

    cutt = {x.user_id: x.user.name for x in model_manager.query(AdminPartnerUser).select_related('user')
        .filter(loginUser=api_helper.get_session_user(request), partnerId=get_session_app(request))}

    for x in user.appuser_set.all():
        if x.cutt_user_id in cutt:
            if x.name != cutt[x.cutt_user_id]:
                x.name = cutt[x.cutt_user_id]
                x.save()
            del cutt[x.cutt_user_id]

    for k, v in cutt.items():
        AppUser(user=user, name=v, type=2, cutt_user_id=k).save()

    return [{
        'id': x.cutt_user_id,
        'name': x.name,
        'type': x.type,
    } for x in user.appuser_set.all()]


@api_func_anonymous
def weekly_report_dist(date_from, date_to, request):
    pass


@api_func_anonymous
def sum_team_dist(date, request):
    app = get_session_app(request)
    qq_stats = []
    wx_stats = []
    qq_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
    }

    wx_sum = {
        'share': 0,
        'weizhan': 0,
        'download': 0,
        'reshare': 0,
        'users': 0,
        'name': '合计',
    }
    for user in User.objects.filter(app=app):
        stats = get_user_stat(date, user)
        qq_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'name': user.name,
        }

        qq_stats.append(qq_stat)
        wx_stat = {
            'share': 0,
            'weizhan': 0,
            'download': 0,
            'reshare': 0,
            'users': 0,
            'name': user.name,
        }

        wx_stats.append(wx_stat)
        for qq in stats:
            stat = qq_stat if qq['type'] == 'QQ' else wx_stat
            sum = qq_sum if qq['type'] == 'QQ' else wx_sum
            stat['share'] += qq['share']
            stat['weizhan'] += qq['weizhan']
            stat['download'] += qq['download']
            stat['reshare'] += qq['reshare']
            stat['users'] += qq['users']

            sum['share'] += qq_stat['share']
            sum['weizhan'] += qq['weizhan']
            sum['download'] += qq['download']
            sum['reshare'] += qq['reshare']
            sum['users'] += qq['users']

    if len(qq_stats) > 1:
        qq_stats.append(qq_sum)
        wx_stats.append(wx_sum)
    return {
        'qq': qq_stats,
        'wx': wx_stats,
    }


def show_open_link(request):
    url = request.GET.get('url')

    if not url:
        url = 'comcuttapp965004://article?id=31412177424'
    else:
        info = re.findall(r'https?://.+?/weizhan/article/\d+/(\d+)/(\d+)', url)
        if info:
            [aid, app] = info
            url = 'comcuttapp%s://article?id=%s' % (aid, app)

    return HttpResponse('<a style="font-size: 10em" href="%s">open</a>' % url)
