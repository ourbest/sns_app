import re
import requests

from backend.models import User, AppUser

DEFAULT_APP = 1519662


def get_session_user(request):
    return request.session.get('user')


def get_session_app(request):
    email = get_session_user(request)
    user = User.objects.filter(email=email).first()
    if user:
        return user.app_id
    else:
        return DEFAULT_APP


def sns_user_to_json(sns_user):
    return {
        'id': sns_user.id,
        'name': sns_user.name,
        'type': sns_user.type,
        'login': sns_user.login_name,
        'password': sns_user.passwd,
        'phone': sns_user.phone,
        'memo': sns_user.memo
    } if sns_user else {}


def device_to_json(x):
    return {
        'id': x.id,
        'label': x.label,
        'num': x.phone_num
    }


def qun_to_json(x):
    return {
        'id': x.sns_group.group_id,
        'name': x.sns_group.group_name,
        'qq': {
            'id': x.sns_user.login_name,
            'name': x.sns_user.name
        },
        'device': {
            'label': x.sns_user.device.label,
            'phone': x.sns_user.device.phone_num
        },
        'member_count': x.sns_group.group_user_count
    }


def user_to_json(x):
    """
    name = models.CharField('姓名', max_length=30)
    email = models.CharField('邮箱', max_length=50)
    status = models.IntegerField('状态', default=0)
    passwd = models.CharField('密码', max_length=50)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    role = models.IntegerField(default=0, help_text='0-组员 1-组长')
    app = models.ForeignKey(App, verbose_name='生活圈', null=True, blank=True, default=None)
    :param x:
    :return:
    """
    if not x:
        return {}

    app_users = [{
        'id': y.id,
        'name': y.name,
        'type': y.type,
        'cutt_id': y.cutt_user_id
    } for y in x.appuser_set.all()]

    ret = {'id': x.id, 'email': x.email, 'name': x.name, 'role': x.role, 'app_users': app_users}
    for u in app_users:
        if u['type'] == 0:
            ret['qq_id'] = u['cutt_id']
        elif u['type'] == 1:
            ret['wx_id'] = u['cutt_id']
    return ret


def auth(email, password):
    user = User.objects.filter(email=email).first()
    return user if user and password == user.passwd else None


def set_password(user, new_pwd):
    user.passwd = new_pwd
    user.save()


def get_app_user_info(app_id, cutt_id):
    url = 'http://api.cutt.com/user/%s/%s' % (app_id, cutt_id)
    try:
        return requests.get(url).json().get('name')
    except:
        return cutt_id


def save_cutt_id(user, cutt_id, user_type):
    db = user.appuser_set.filter(type=user_type).first()
    if not db:
        name = get_app_user_info(user.app_id, cutt_id)
        db = AppUser(name=name, type=user_type, user=user)
    db.cutt_user_id = cutt_id
    db.save()


def to_share_url(user, url, share_type=0):
    u = re.findall(r'https?://tz.fafengtuqiang.cn/weizhan/article/\d+/\d+/\d+', url)[0]
    qq = user.appuser_set.filter(type=share_type).first()
    if qq:
        u = '%s/%s' % (u, qq.cutt_user_id)
    return u
