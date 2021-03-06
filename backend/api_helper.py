import pathlib

import hashlib
import os
import re
import threading
from collections import defaultdict
from datetime import timedelta
from random import shuffle

import requests
from dj import times
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db.models import Q
from django.utils import timezone
from .loggs import logger

from backend import model_manager, caches, zhiyue_models
from backend.models import User, AppUser, TaskGroup, GroupTag, SnsGroupSplit, DistTaskLog, SnsApplyTaskLog, SnsGroup, \
    SnsUser, SnsUserGroup, DistArticle, DeviceWeixinGroup, PhoneDevice, CallingList, ActiveDevice

DEFAULT_APP = 1519662


def get_session_user(request):
    return request.session.get('user')


def get_session_app(request, login_user=None):
    app = request.GET.get('app') or request.POST.get('app')
    if app:
        return app

    if not login_user:
        login_user = model_manager.get_user(get_session_user(request))

    if login_user:
        return login_user.app_id
    else:
        logger.warning("cannot find session user")
        return DEFAULT_APP


def sns_user_to_json(sns_user, owner=0):
    ret = {
        'id': sns_user.id,
        'name': sns_user.name,
        'type': sns_user.type,
        'login': sns_user.login_name,
        'password': sns_user.passwd,
        'phone': '%s%s' % (sns_user.phone, '' if not sns_user.device or
                                                 not sns_user.device.memo else '(%s)' % sns_user.device.memo),
        'memo': sns_user.memo,
        'dist': sns_user.dist,
        'search': sns_user.search,
        'friend': sns_user.friend,
        'status': sns_user.status,
        'provider': sns_user.provider,
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
           'device': {
               'label': x.sns_user.device.label, 'phone': x.sns_user.device.phone_num
           } if x.sns_user.device else None,
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
    } for y in x.appuser_set.filter(type__gte=0)]

    ret = {
        'id': x.id, 'email': x.email, 'name': x.name, 'notify': 0 if not x.notify else x.notify,
        'role': x.role, 'phone': x.phone, 'app_users': app_users, 'status': x.status,
    }
    for u in app_users:
        if u['type'] == 0:
            ret['qq_id'] = u['cutt_id']
        elif u['type'] == 1:
            ret['wx_id'] = u['cutt_id']
    return ret


def auth(email, password):
    user = User.objects.filter(email=email, status__gte=0).first()
    if user:
        return user if (user.passwd and password == user.passwd) or user.userauth.password == password else None
    return None


def set_password(user, new_pwd):
    user.userauth.passwd = new_pwd
    user.userauth.save()


def get_app_user_info(app_id, cutt_id):
    url = 'https://api.cutt.com/user/%s/%s' % (app_id, cutt_id)
    try:
        return requests.get(url).json().get('name')
    except:
        return cutt_id


def save_cutt_id(user, cutt_id, user_type):
    db = user.appuser_set.filter(type=user_type).first()
    if not db:
        name = get_app_user_info(user.app_id, cutt_id)
        db = AppUser(name=name, type=user_type, user=user, app_id=user.app_id)
    db.cutt_user_id = cutt_id
    db.save()


def to_share_url(user, url, share_type=0, label=None, task_id=0):
    lines = url.split('\n')
    url = lines[0]
    u = re.findall(r'(https?://.+?/weizhan/article/\d+/\d+)/\d+', url)
    if u:
        u = '%s/%s' % (u[0], user.app_id)

        cutt_id = None
        if lines:
            for line in lines:
                if line.find('cutt_id=') == 0:
                    cutt_id = line[len('cutt_id='):]
                    break

        if not cutt_id:
            qq = user.appuser_set.filter(type=share_type).first()
            if qq:
                cutt_id = qq.cutt_user_id

        u = '%s/%s' % (u, cutt_id)
        u = u.replace('http://tz.', 'https://tz.')
        if label:
            suffix = label if len(label) != 11 else '%s' % (label[-4:])
            u += '/' + suffix + '?ts=%s&dev=%s' % (int(timezone.now().timestamp() * 1000 % 1000000), task_id)

    return u if u else url


def extract_url(url):
    url = url.split('\n')[0]
    u = re.findall(r'https?://.+?/weizhan/article/\d+/\d+/\d+', url)
    return u[0] if u else None


def parse_item_id(url):
    for res in url.split('\n'):
        if not res:
            continue
        u = re.findall(r'https?://.+?/weizhan/article/\d+/(\d+)/\d+', res)
        return u[0] if u else None
    return None


def get_dist_wx_qun(lines, device, percent):
    groups = list(DeviceWeixinGroup.objects.filter(device=device).order_by('last_dist_at'))
    num = int(len(groups) * percent / 100)
    to_send = list()
    lines.append('total=%s' % len(groups))
    lines.append('num=%s' % num)
    lines.append('send=%s' % len(to_send))
    for idx in range(0, num):
        group = groups[idx]
        lines.append('group_%s=%s' % (idx, group.name))
        to_send.append(group.id)

    if to_send:
        DeviceWeixinGroup.objects.filter(pk__in=to_send).update(last_dist_at=timezone.now())


def add_wx_params(device_task):
    device = device_task.device
    logger.info('%s微信分发任务手机（%s）', device_task.id, device.friend_text)

    lines = device_task.data.split('\n')

    user_lines = []
    for line in lines:
        idx = line.find('=')
        if 0 < idx < 10:
            user_lines.append(line)
            v = line.split('=')
            if len(v) == 2 and v[0] == 'ratio':
                percent = int(v[1] if v[1].isdigit() else 100)
                get_dist_wx_qun(user_lines, device, percent)

    return '\n%s' % '\n'.join(user_lines)


def add_dist_qun(device_task):
    device = device_task.device
    logger.info('%s分发任务手机（%s）', device_task.id, device.friend_text)

    sns_user_query = device.snsuser_set.filter(type=0, dist=1)
    # if 'client=qq' in device_task.data:
    #     sns_user_query = sns_user_query.filter(provider='qq')
    # elif 'client=tim' in device_task.data:
    #     sns_user_query = sns_user_query.filter(provider='tim')

    sns_users = list(sns_user_query)
    shuffle(sns_users)

    logger.info('%s分发%s个QQ', device_task.id, len(sns_users))

    groups = dict()
    # ignore_qun = {x.group_id for x in
    #               DistTaskLog.objects.filter(success=1, group__app_id=device_task.task.app_id,
    #                                          created_at__gte=timezone.now() - timedelta(minutes=5))}
    ignore_qun = {}

    lines = device_task.data.split('\n')

    ids = None
    user_lines = []
    qun = 2
    for line in lines:
        if line.find('tag=') == 0:
            logger.info('按照标签分发，标签为%s', line)
            tags = line[4:].split(';')
            if tags:
                ids = {x.group_id for x in GroupTag.objects.filter(group__app_id=device_task.task.app_id, tag__in=tags)}
                if len(ids) == 0:
                    ids = None
                else:
                    logger.info('%s分发最多%s个QQ群', device_task.id, len(ids))

        elif line.find('app=') == 0:
            user_lines.append(line)
        elif line.find('client=') == 0:
            user_lines.append(line)
        elif line.find('apply_qun=') == 0:
            qun = int(line[line.find('=') + 1:])
        elif '=' in line:
            user_lines.append(line)

    for user in sns_users:
        user_groups = user.snsusergroup_set.filter(status=0, active=1)
        logger.info('%s QQ(%s)分发预计%s个QQ群', device_task.id, user.login_name, len(user_groups))
        if user_groups:
            dup = 0
            user_groups = list(user_groups)
            shuffle(user_groups)

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
                    dup += 1
                    pass

            if group_ids:
                groups['%s@%s' % (user.login_name, user.provider)] = group_ids
                logger.info('%s QQ(%s)分发%s个QQ群，忽略%s个群', device_task.id, user.login_name, len(group_ids), dup)

    idx = 0
    group_lines = []

    to_add_groups = get_add_groups(qun, device_task) if qun else []

    for login_name, groups in groups.items():
        idx += 1
        [qq_id, platform] = login_name.split('@')
        user_lines.append('QQ_%s=%s' % (idx, qq_id))
        user_lines.append('QQ_%s_AT=%s' % (idx, platform))

        for group in groups:
            group_lines.append('QUN_%s=%s' % (idx, group))

        if login_name in to_add_groups:
            for group in to_add_groups.get(login_name):
                # 在分发过程中申请加群
                group_lines.append('ADD_%s=%s' % (idx, group))

    if len(user_lines) == 0:
        logger.warning('此次任务没有Q群，请检查 %s' % device.label)

    return '\napply_qun=%s\n%s\n%s' % (qun, '\n'.join(user_lines), '\n'.join(group_lines))


def remove_dup_split(user):
    matched = set()
    for x in SnsGroupSplit.objects.filter(user=user, status=0):
        if x.group_id in matched:
            x.delete()
        else:
            matched.add(x.group_id)


def add_add_qun(device_task):
    data = ''  # device_task.data

    cnt = 5
    # if data:
    #     try:
    #         cnt = int(data.strip())
    #     except:
    #         pass
    #     # data = data.strip() + '\n'
    # data = 'COUNT=%s\n' % cnt
    # # data += '\n'.join(ids)
    for line in device_task.data.strip().split('\n'):
        if '=' in line:
            data += '%s\n' % line
        else:
            try:
                cnt = int(line.strip())
            except:
                pass

    data += 'COUNT=%s\n' % cnt

    groups = get_add_groups(cnt, device_task)

    # if 'client=qq' in device_task.data:
    #     data += 'client=qq\n'
    # elif 'client=tim' in device_task.data:
    #     data += 'client=tim\n'

    idx = 0
    user_lines = []
    group_lines = []
    for login_name, groups in groups.items():
        idx += 1
        [qq_id, platform] = login_name.split('@')
        user_lines.append('QQ_%s=%s' % (idx, qq_id))
        user_lines.append('QQ_%s_AT=%s' % (idx, platform))
        for group in groups:
            group_lines.append('QUN_%s=%s' % (idx, group))
    return data + '%s\n%s' % ('\n'.join(user_lines), '\n'.join(group_lines))


def get_add_groups(cnt, device_task):
    device = device_task.device

    sns_users = device.snsuser_set.filter(type=0, friend=1)

    if 'client=qq' in device_task.data:
        sns_users = sns_users.filter(provider='qq')
    elif 'client=tim' in device_task.data:
        sns_users = sns_users.filter(provider='tim')

    idx = 0
    ids = [x.group_id for x in
           model_manager.get_qun_idle(device_task.task.creator, len(sns_users) * cnt * 5, device_task.device)]
    shuffle(ids)
    groups = dict()
    for user in sns_users:
        group_ids = []
        groups['%s@%s' % (user.login_name, user.provider)] = group_ids

    while idx < len(ids):
        for user in sns_users:
            group_ids = groups['%s@%s' % (user.login_name, user.provider)]
            if idx < len(ids):
                group_ids.append(ids[idx])
                idx += 1
            else:
                break

    return groups


def merge_task_log(task, log_content):
    pass


def merge_task_result(task, result_content):
    path = pathlib.Path('./logs/result')
    if not path.exists():
        path.mkdir(parents=True, exist_ok=True)
    file_path = './logs/result/%s.txt' % task.id
    with open(file_path, 'at', encoding='utf-8') as file:
        file.write(result_content)
        file.write('\n')


def get_result_content(task_id):
    file_path = './logs/result/%s.txt' % task_id
    if os.path.exists(file_path):
        with open(file_path, "rt") as file:
            return file.read()
    else:
        return ''


def get_login_user(request, email=None):
    return model_manager.get_user(get_session_user(request) if not email else email)


def webhook(device_task, msg, force=0):
    user = device_task.device.owner
    if not force and (not user.notify or user.notify <= 1):
        return

    msg = '%s：%s %s' % (device_task.device.friend_text, device_task.task.type.name, msg)
    if device_task.task.type_id in (3, 5):
        msg += ' URL: %s' % extract_url(device_task.task.data)

    thread = threading.Thread(target=send_msg, args=(msg, user))
    thread.start()


def webhook_task(task, msg):
    user = task.creator
    if not user.notify:
        return

    msg = '%s：任务%s' % (task.type.name, msg)
    if task.type_id in (3, 5):
        msg += ' URL: %s' % extract_url(task.data)

    thread = threading.Thread(target=send_msg, args=(msg, user))
    thread.start()


def send_msg(msg, user):
    now = timezone.now().timestamp()
    val = caches.get_or_create(hashlib.md5(msg.encode()).hexdigest(), now, 300)
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


def send_html_mail(subject, to, html_content, text_content='HTML'):
    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_HOST_USER, [to] if isinstance(to, str) else to)
    msg.attach_alternative(html_content, "text/html")
    msg.send()


def deal_result_line(device_task, line):
    if not line:
        return None

    values = re.split('\s+', line)
    if device_task.task.type_id in (2, 3):
        if len(values) == 3:
            [qun_id, status, qq_id] = values
            qun = model_manager.get_qun(qun_id)
            qq = model_manager.get_qq(qq_id)
            if status in ADD_STATUS:
                model_manager.increase_apply_count(qun)
                deal_add_result(device_task, qq, qun, status)
            else:
                deal_dist_result(device_task, qq, qun, status)
    elif device_task.task.type_id == 1:  # 查群
        account = line.split('\t')
        save_group(account[0], account[1], account[2], device_task.task.app_id, device_task.device.owner)
    elif device_task.task.type_id == 4:  # 统计
        account = line.split('\t')
        if len(account) == 4 and account[0].isdigit():
            device = device_task.device
            [qun_num, qun_name, qun_user_cnt, qq] = account
            deal_count_result(qun_num, qun_name, qun_user_cnt, qq, device)
    return None


def deal_count_result(qun_num, qun_name, qun_user_cnt, qq, device):
    qun_user_cnt = 0 if not qun_user_cnt.isdigit() else int(qun_user_cnt)
    qun = SnsGroup.objects.filter(group_id=qun_num, type=0).first()
    sns_user = SnsUser.objects.filter(login_name=qq, type=0).first()
    if not sns_user:
        logger.info("Sns user %s not found device is %s", qq, device.id)
        sns_user = SnsUser(name=qq, login_name=qq, passwd='_',
                           phone=device.phone_num, device=device,
                           owner=device.owner, app=device.owner.app)
        sns_user.save()
    elif sns_user.device != device:
        sns_user.device = device
        sns_user.owner = device.owner
        sns_user.phone = device.label
        sns_user.save()

    if not qun:
        qun = SnsGroup(group_id=qun_num, group_name=qun_name, type=0, app_id=sns_user.app_id,
                       group_user_count=qun_user_cnt, status=2, created_at=timezone.now(),
                       from_user_id=device.owner_id)
        qun.save()
        model_manager.process_tag(qun)
    else:
        qun.group_name = qun_name
        qun.group_user_count = qun_user_cnt
        qun.status = 2
        try:
            qun.save(update_fields=['group_name', 'group_user_count', 'status'])
        except:
            pass
        model_manager.process_tag(qun)

    found = qun.snsusergroup_set.filter(sns_user=sns_user).first()
    if found:
        if found.status != 0:
            found.status = 0
            found.active = 1
            found.save()
    else:
        found = SnsUserGroup(sns_group=qun, sns_user=sns_user, status=0, active=1)
        found.save()

    qun.snsgroupsplit_set.filter(phone=device).update(status=3)

    SnsApplyTaskLog.objects.filter(account=sns_user, memo='已发送验证', group=qun).update(status=1)


def save_group(group_id, group_name, group_user_count, app_id, from_user):
    try:
        db = SnsGroup(group_id=group_id, group_name=group_name, type=0, app_id=app_id,
                      group_user_count=group_user_count, created_at=timezone.now(), from_user=from_user)
        db.save()
        model_manager.process_tag(db)
        logger.info('发现了新群 %s' % group_id)
    except:
        pass


def deal_dist_result(device_task, qq, qun, status):
    db = DistTaskLog.objects.filter(task=device_task, group=qun, sns_user=qq).first()
    if not db:
        DistTaskLog(task=device_task, group=qun, sns_user=qq, status=status,
                    success=1 if status == '已分发' else 0).save()

    kicked = False

    if status == '被踢出':
        ug = qun.snsusergroup_set.filter(sns_user=qq).first()
        if ug:
            model_manager.set_qun_kicked(ug)
        kicked = True

    return kicked


def deal_add_result(device_task, qq, qun, status, device=None):
    SnsApplyTaskLog(device=device or device_task.device, device_task=device_task, account=qq, memo=status,
                    group=qun).save()
    if status in ('付费群', '不存在', '不允许加入', '满员群'):
        model_manager.set_qun_useless(qun)
    elif status in ('已加群', '无需验证已加入'):
        model_manager.set_qun_join(qq, qun)
    elif status in ('已发送验证',):
        model_manager.set_qun_applying(device or device_task.device, qun)
    elif status in ('需要回答问题',):
        model_manager.set_qun_manual(qun)
    elif status in ('无需验证未加入', '发送验证失败'):
        pass


ADD_STATUS = {'付费群', '不存在', '不允许加入', '已加群', '无需验证已加入', '已发送验证', '需要回答问题', '无需验证未加入', '满员群', '发送验证失败'}
DIST_STATUS = {}


def parse_dist_article(data, task, from_time=None):
    if not from_time:
        from_time = timezone.now()
    item_id = parse_item_id(data)
    if item_id:
        db = DistArticle.objects.filter(item_id=item_id).first()
        from_time = from_time if from_time > task.schedule_at else task.schedule_at
        if not db:
            db = DistArticle(item_id=item_id, app_id=task.app_id,
                             started_at=from_time, created_at=from_time, last_started_at=from_time,
                             title=zhiyue_models.get_article_title(item_id))
            model_manager.save_ignore(db)

        else:
            if db.last_started_at != from_time:
                db.last_started_at = from_time
                model_manager.save_ignore(db)

        if task.article != db:
            task.article = db
            model_manager.save_ignore(task)
    else:
        logger.warning('cannot parse task item id %s of %s' % (data, task))


class RequestCalling:
    """在两个设备间建立呼叫连接，每个设备有且仅有一条连接"""

    def __init__(self, device: PhoneDevice):
        self.device = device

    def pull_connection(self):
        connection = self._get_existing_connection()
        if connection:
            return self.filter(connection)

    def _get_existing_connection(self) -> CallingList:
        return CallingList.objects.filter(Q(calling=self.device) | Q(called=self.device),
                                          Q(success_or_failure=None)).first()

    def create(self, qq_numbers: list) -> CallingList or None:
        old_connection = self.pull_connection()
        new_connection = None
        qq = self._filter_calling_qq(qq_numbers)
        if qq:
            called_device = self.get_called_device()
            if called_device:
                new_connection = CallingList(calling=self.device, calling_qq=qq, called=called_device)

        if new_connection is not None:
            if old_connection:
                old_connection.success_or_failure = False
                old_connection.failure_reason = '%s创建了新的请求' % self.what_role(old_connection)
            new_connection.save()
        return new_connection

    def get_called_device(self) -> PhoneDevice or None:
        """获取另一个没有连接、在线且空闲的设备"""
        idlers = ActiveDevice.objects.filter(active_at__gt=timezone.now() - timedelta(minutes=10),
                                             status=0).exclude(device=self.device)
        ids_1 = {x.device_id for x in idlers}
        connections = CallingList.objects.filter(Q(calling_id__in=ids_1) | Q(called_id__in=ids_1),
                                                 Q(success_or_failure=None))
        ids_2 = {*[x.calling_id for x in connections], *[x.called_id for x in connections]}
        ids = ids_1 - ids_2
        return PhoneDevice.objects.filter(pk__in=ids).order_by('?').first()

    def _filter_calling_qq(self, qq_numbers) -> SnsUser:
        qqs = SnsUser.objects.filter(type=0, status=0, login_name__in=qq_numbers)
        if qqs.exists():
            queryset = CallingList.objects.filter(Q(calling_qq__in=qqs) | Q(called_qq__in=qqs),
                                                  Q(success_or_failure=True),
                                                  Q(change_time__gte=self._today_zero()))
            listing = {*[x.calling_qq_id for x in queryset], *[x.called_qq_id for x in queryset]}
            for qq in qqs:
                if qq.id not in listing:
                    return qq

    @staticmethod
    def _today_zero():
        return timezone.localtime().replace(hour=0, minute=0, second=0, microsecond=0)

    def filter(self, connection: CallingList) -> CallingList or None:
        if self._check_status_timeout(connection):
            if connection.status == 0:
                failure_reason = 'calling未及时切换到指定QQ号'
            elif connection.status == 1:
                failure_reason = 'called未及时查看请求'
            elif connection.status == 2:
                failure_reason = 'called未及时返回QQ号'
            elif connection.status == 3:
                failure_reason = 'calling未及时查看返回的QQ号'
            elif connection.status == 4:
                failure_reason = 'calling未及时呼叫'
            elif connection.status == 5:
                failure_reason = 'called未及时接呼叫'
            elif connection.status == 6:
                failure_reason = 'calling确认呼叫失败'
            else:
                failure_reason = '未知'
            connection.success_or_failure = False
            connection.failure_reason = failure_reason
            connection.save()

        else:
            return connection

    STATUS_TIMEOUT = defaultdict(lambda: 30)
    STATUS_TIMEOUT.update([(1, 60), (2, 2 * 60), (4, 3 * 60)])

    def _check_status_timeout(self, connection: CallingList) -> bool:
        if self.STATUS_TIMEOUT[connection.status]:
            return timezone.now() > connection.change_time + timedelta(seconds=self.STATUS_TIMEOUT[connection.status])
        return False

    ROLES = ('calling', 'called')

    def what_role(self, connection: CallingList):
        if connection.calling_id == self.device.pk:
            return self.ROLES[0]
        elif connection.called_id == self.device.pk:
            return self.ROLES[1]

    def update(self, new_status: int, qq_number=None) -> CallingList or None:
        connection = self.pull_connection()
        if not connection or connection.status + 1 != new_status:
            return

        role = self.what_role(connection)
        if new_status == 1 and role == self.ROLES[0]:
            connection.status += 1
            connection.save()
        elif new_status == 2 and role == self.ROLES[1]:
            connection.status += 1
            connection.save()
        elif new_status == 3 and role == self.ROLES[1] and qq_number:
            qq = model_manager.get_qq(qq_number)
            if qq:
                connection.status += 1
                connection.called_qq = qq
                connection.save()
        elif new_status == 4 and role == self.ROLES[0]:
            connection.status += 1
            connection.save()
        elif new_status == 5 and role == self.ROLES[0]:
            connection.status += 1
            connection.save()
        elif new_status == 6 and role == self.ROLES[1]:
            connection.status += 1
            connection.save()
        elif new_status == 7 and role == self.ROLES[0]:
            connection.status += 1
            connection.success_or_failure = True
            connection.save()

        return connection
