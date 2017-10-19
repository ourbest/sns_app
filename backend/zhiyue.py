import re
from datetime import datetime

from dj import times
from dj.utils import api_func_anonymous

from backend import api_helper, model_manager
from backend.api_helper import get_session_app
from backend.zhiyue_models import ShareArticleLog, ClipItem, WeizhanCount, HighValueUser


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
    cutt_users = list(the_user.appuser_set.all())
    cutt_user_dict = {x.cutt_user_id: x for x in cutt_users}
    date = times.localtime(
        datetime.now().replace(hour=0, second=0, minute=0, microsecond=0) if not date else datetime.strptime(date,
                                                                                                             '%Y-%m-%d'))

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
