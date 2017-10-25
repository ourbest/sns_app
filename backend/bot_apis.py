from dj.utils import api_func_anonymous
from django.http import HttpResponse

from backend import bots


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

    return {'status': status, 'message': message, 'name': name}


def get_session_id(request):
    return request.session.session_key
