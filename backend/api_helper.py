import re
import threading
from datetime import timedelta
from random import shuffle

import requests
from dj import times
from django.utils import timezone

from backend import model_manager, caches
from backend.models import User, AppUser, TaskGroup, DistTaskLog, GroupTag

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


def sns_user_to_json(sns_user, owner=0):
    ret = {
        'id': sns_user.id,
        'name': sns_user.name,
        'type': sns_user.type,
        'login': sns_user.login_name,
        'password': sns_user.passwd,
        'phone': '%s%s' % (sns_user.phone, '' if not sns_user.device.memo else '(%s)' % sns_user.device.memo),
        'memo': sns_user.memo,
        'dist': sns_user.dist,
        'search': sns_user.search,
        'friend': sns_user.friend,
    } if sns_user else {}

    if sns_user and owner:
        ret['owner'] = sns_user.owner.name
    return ret


def device_to_json(x):
    return {
        'id': x.id,
        'label': x.label,
        'num': x.phone_num,
        'memo': x.memo
    }


def qun_to_json(x, owner=0):
    ret = {'id': x.sns_group.group_id, 'name': x.sns_group.group_name,
           'qq': {'id': x.sns_user.login_name, 'name': x.sns_user.name},
           'device': {'label': x.sns_user.device.label, 'phone': x.sns_user.device.phone_num},
           'member_count': x.sns_group.group_user_count}
    if owner:
        ret['owner'] = x.sns_user.owner.name
    return ret


def lost_qun_to_json(x):
    return {
        'id': x.group.group_id,
        'name': x.group.group_name,
        'qq': {
            'id': x.sns_user.login_name,
            'name': x.sns_user.name
        },
        'device': {
            'label': x.sns_user.device.label,
            'phone': x.sns_user.device.phone_num
        },
        'member_count': x.group.group_user_count,
        'lost_time': times.to_str(x.created_at),
    }


def sns_group_to_json(x):
    return {
        'id': x.group_id,
        'name': x.group_name,
        'member_count': x.group_user_count,
        'quiz': x.quiz,
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
        'cutt_id': y.cutt_user_id,
    } for y in x.appuser_set.all()]

    ret = {
        'id': x.id, 'email': x.email, 'name': x.name, 'notify': 0 if not x.notify else x.notify,
        'role': x.role, 'phone': x.phone, 'app_users': app_users
    }
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


def to_share_url(user, url, share_type=0, label=None):
    url = url.split('\n')[0]
    u = re.findall(r'https?://.+?/weizhan/article/\d+/\d+/\d+', url)
    if u:
        u = u[0]
        qq = user.appuser_set.filter(type=share_type).first()
        if qq:
            u = '%s/%s' % (u, qq.cutt_user_id)
            u.replace('http://tz.', 'https://tz.')
            if label:
                suffix = label if len(label) != 11 else '%s___%s' % (label[0:4], label[-4:])
                u += '?l=' + suffix

    return u if u else url


def extract_url(url):
    url = url.split('\n')[0]
    u = re.findall(r'https?://.+?/weizhan/article/\d+/\d+/\d+', url)
    return u[0] if u else None


def parse_item_id(url):
    url = url.split('\n')[0]
    u = re.findall(r'https?://.+?/weizhan/article/\d+/(\d+)/\d+', url)
    return u[0] if u else None


def add_dist_qun(device_task):
    device = device_task.device

    sns_users = device.snsuser_set.filter(type=0, dist=1)

    groups = dict()
    ignore_qun = {x.group_id for x in
                  DistTaskLog.objects.filter(success=1, group__app_id=device_task.task.app_id,
                                             created_at__gte=timezone.now() - timedelta(hours=1))}

    lines = device_task.data.split('\n')

    ids = None
    user_lines = []
    for line in lines:
        if line.find('tag=') == 0:
            tags = line[4:].split(';')
            ids = {x.group_id for x in GroupTag.objects.filter(group__app_id=device_task.task.app_id, tag__in=tags)}
        elif line.find('app=') == 0:
            user_lines.append(line)

    for user in sns_users:
        user_groups = user.snsusergroup_set.filter(status=0, active=1)
        if user_groups:
            group_ids = []
            for group in user_groups:
                if group.sns_group_id in ignore_qun:
                    # 1小时内分发过了
                    continue

                if ids is not None and group.sns_group_id not in ids:
                    # 按标签分发
                    continue
                try:
                    TaskGroup(task=device_task.task, sns_user=user, group_id=group.sns_group_id).save()
                    group_ids.append(group.sns_group_id)
                except:
                    pass
            if group_ids:
                groups[user.login_name] = group_ids

    idx = 0
    group_lines = []

    for login_name, groups in groups.items():
        idx += 1
        user_lines.append('QQ_%s=%s' % (idx, login_name))
        for group in groups:
            group_lines.append('QUN_%s=%s' % (idx, group))
    return '\n%s\n%s' % ('\n'.join(user_lines), '\n'.join(group_lines))


def add_add_qun(device_task):
    device = device_task.device
    data = device_task.data

    cnt = 5

    sns_users = device.snsuser_set.filter(type=0, friend=1)
    idx = 0

    ids = [x.group_id for x in
           model_manager.get_qun_idle(device_task.task.creator, len(sns_users) * cnt * 5, device_task.device)]
    shuffle(ids)
    if not data:
        data = 'COUNT=%s\n' % cnt
    else:
        data = data.strip() + '\n'
    # data += '\n'.join(ids)
    groups = dict()
    while idx < len(ids):
        for user in sns_users:
            group_ids = [] if user.login_name not in groups else groups[user.login_name]
            for i in range(0, cnt):
                if idx < len(ids):
                    group_ids.append(ids[idx])
                    idx += 1
                else:
                    break

            if group_ids:
                groups[user.login_name] = group_ids

    idx = 0
    user_lines = []
    group_lines = []
    for login_name, groups in groups.items():
        idx += 1
        user_lines.append('QQ_%s=%s' % (idx, login_name))
        for group in groups:
            group_lines.append('QUN_%s=%s' % (idx, group))
    return data + '%s\n%s' % ('\n'.join(user_lines), '\n'.join(group_lines))


def merge_task_log(task, log_content):
    pass


def merge_task_result(task, result_content):
    file_path = './logs/result/%s.txt' % task.id
    with open(file_path, 'at', encoding='utf-8') as file:
        file.write(result_content)
        file.write('\n')


def get_result_content(task_id):
    file_path = './logs/result/%s.txt' % task_id
    with open(file_path, "rt") as file:
        return file.read()


def get_login_user(request, email=None):
    return model_manager.get_user(get_session_user(request) if not email else email)


def webhook(device_task, msg, force=0):
    user = device_task.device.owner
    if not force and (not user.notify or user.notify <= 1):
        return

    msg = '%s：%s任务%s' % (device_task.device.friend_text, device_task.task.type.name, msg)
    if device_task.task.type_id == 3:
        msg += ' URL: ' + extract_url(device_task.task.params)

    thread = threading.Thread(target=send_msg, args=(msg, user))
    thread.start()


def webhook_task(task, msg):
    user = task.creator
    if not user.notify:
        return

    msg = '%s：任务%s' % (task.type.name, msg)
    if task.type_id == 3:
        msg += ' URL: ' + extract_url(task.params)

    thread = threading.Thread(target=send_msg, args=(msg, user))
    thread.start()


def send_msg(msg, user):
    now = timezone.now().timestamp()
    val = caches.get_or_create(msg, now, 300)
    if val is not None and val - now < 10:
        return

    # https://oapi.dingtalk.com/robot/send?access_token=114b9ee24111a47f7dd9864195f905ed766c92ddb3c1b346b70d6bf3d4a3ae0d
    url = 'https://oapi.dingtalk.com/robot/send?access_token' \
          '=114b9ee24111a47f7dd9864195f905ed766c92ddb3c1b346b70d6bf3d4a3ae0d'
    dingding_msg = {
        'msgtype': 'text',
        'text': {
            'content': msg
        },
        'at': {
            'atMobiles': [user.phone],
            'isAtAll': False
        }
    } if user.phone else {
        'msgtype': 'text',
        'text': {
            'content': '%s: %s' % (user.name, msg)
        }
    }
    requests.post(url, json=dingding_msg)
