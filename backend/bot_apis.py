from dj.utils import api_func_anonymous
from django.http import HttpResponse

from backend import bots, model_manager, api_helper
from backend.models import SnsUser, SnsGroup, SnsUserGroup


def login_qr(request):
    bot = bots.anonymous_bots[get_session_id(request)]

    qr = bot.get_qr()
    qr.seek(0)
    response = HttpResponse(qr, content_type="image/png")
    return response


@api_func_anonymous
def get_qr_status(request):
    bot = bots.anonymous_bots[get_session_id(request)]
    status = bot.check_login()
    message = "请扫描二维码"
    name = ""
    if status == '200':
        message = '登录成功'

        bot.post_login()

        del bots.anonymous_bots[get_session_id(request)]
        name = bot.self.name
    elif status == '201':
        message = '等待客户端确认'
    elif status == '408':
        message = '二维码已过期，请重新扫描'

    return {'status': status, 'message': message, 'name': name, 'puid': bot.self.user_name[1:] if bot.self else ''}


@api_func_anonymous
def get_contacts(name, request):
    wx = model_manager.get_wx(api_helper.get_login_user(request), name)
    return {
        'items': [{
            'name': x.sns_group.group_name,
            'user_count': x.sns_group.group_user_count,
        } for x in wx.snsusergroup_set.filter(status=0, type=1).select_related('sns_group')]
    }


@api_func_anonymous
def sync_contacts(name, request):
    bot = bots.running_bots.get(name)
    if bot:
        save_contacts(bot, api_helper.get_login_user(request))

    return '保存成功'


def save_contacts(bot, user):
    puid = bot.self.user_name[1:]
    wx = SnsUser.objects.filter(login_name=puid, type=1).first()
    if not wx:
        wx = SnsUser(name=bot.name, login_name=puid, type=1, phone='N/A', owner=user, app=user.app)
        wx.save()

    groups = bot.groups

    wx.snsusergroup_set.exclude(sns_group_id__in=[g.group_id for g in groups]).update(status=-1)
    for group in groups:
        gid = group.user_name[1:]
        sns_group = SnsGroup.objects.filter(type=1, group_id=gid)
        if not sns_group:
            sns_group = SnsGroup(group_id=gid, group_name=group.name,
                                 group_user_count=len(group.members), from_user=user, app=user.app)
            sns_group.save()

        old = sns_group.snsusergroup_set.filter(sns_user=wx).first()
        if not old:
            SnsUserGroup(sns_user=wx, sns_group=sns_group).save()
        else:
            old.status = 0
            old.save()


def get_session_id(request):
    return request.session.session_key
