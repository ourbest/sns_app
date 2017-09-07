import logging
import os
import re
from collections import defaultdict
from datetime import datetime

import requests
from dj import times
from dj.utils import api_func_anonymous, api_error
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from qiniu import Auth, put_file, etag

from backend import model_manager
from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice, SnsUser, SnsUserGroup, SnsGroupLost, \
    SnsTaskDevice, DeviceFile, SnsTaskType, SnsTask, ActiveDevice

logger = logging.getLogger(__name__)

DEFAULT_APP = 1519662


@api_func_anonymous
def upload(type, id, task_id, request):
    if 'file' not in request.FILES:
        api_error(1000, '没有上传的文件')

    upload_file = request.FILES['file']

    name = os.path.basename(upload_file.name)
    if isinstance(upload_file, TemporaryUploadedFile):
        tmp_file = upload_file.temporary_file_path()
    else:
        tmp_file = "/tmp/%s/%s" % (task_id, name)
        with open(tmp_file, "wb") as out:
            for chunk in upload_file.chunks():
                out.write(chunk)

    key = _upload_to_qiniu(id, task_id, type, name, tmp_file)

    device = PhoneDevice.objects.filter(label=id).first()

    if device:
        ad = model_manager.get_active_device(device)
        if not ad:
            ad = ActiveDevice(device=device, status=0, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = 0
        ad.save()

        device_task = SnsTaskDevice.objects.filter(device__label=id, task_id=task_id).first()
        if device_task:
            if device_task.status != 2:
                device_task.status = 2
                device_task.finish_at = timezone.now()
                device_task.save()

            device_file = DeviceFile(device=device, task_id=device_task.task_id, qiniu_key=key,
                                     file_name=name, type=type, device_task=device_task)
            device_file.save()

            if device_task.task.type_id == 4:
                with open(tmp_file, 'rt', encoding='utf-8') as f:
                    import_qun_stat(f.read())

    if type == 'result' and task_id == 'stat':
        with open(tmp_file, 'rt', encoding='utf-8') as f:
            import_qun_stat(f.read())

    os.remove(tmp_file)
    return "ok"


def _make_task_content(device_task):
    return '[task]\nid=%s\ntype=%s\n[data]\n%s' % (device_task.task_id, device_task.task.type_id, device_task.data)


@api_func_anonymous
def task(id):
    device = model_manager.get_phone(id)
    if device:
        ad = model_manager.get_active_device(device)
        if not ad:
            ad = ActiveDevice(device=device, status=0, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = 0

        SnsTaskDevice.objects.filter(device__label=id, status=1).update(status=3, finish_at=timezone.now())
        device_task = SnsTaskDevice.objects.filter(device__label=id, status=0).first()
        if device_task:
            device_task.status = 1
            device_task.started_at = timezone.now()
            device_task.save()
            ad.status = 1
            ad.save()
            if device_task.task.status == 0:
                device_task.task.status = 1
                device_task.task.save()
            return {
                'name': 'task.txt',
                'content': _make_task_content(device_task)
            }
        else:
            ad.status = 0
        ad.save()

    return {}


@api_func_anonymous
def image():
    pass


@api_func_anonymous
def qq_qr():
    pass


@api_func_anonymous
def import_qq(ids):
    """
    qq passwd nick phone
    :return:
    """
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = SnsUser.objects.filter(type=0, login_name=account[0]).first()
            device = PhoneDevice.objects.filter(phone_num=account[3]).first()
            if not db:
                SnsUser(passwd=account[1], type=0, login_name=account[0],
                        owner=device.owner, app_id=device.owner.app_id,
                        name=account[2], phone=account[3], device=device).save()
                total += 1
            else:
                db.passwd = account[1]
                db.name = account[2]
                db.phone = account[3]
                db.device = device
                db.owner = device.owner
                db.app_id = device.owner.app_id
                db.save()

    return {
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def my_qq(request, email):
    if not email:
        email = _get_session_user(request)

    return [{
        'phone': x.phone,
        'login_name': x.login_name,
        'type': x.type,
        'name': x.name
    } for x in SnsUser.objects.filter(owner__email=email).order_by("phone")]


@api_func_anonymous
def my_qun(request):
    return [_qun_to_json(x) for x in
            SnsUserGroup.objects.filter(sns_user__owner__email=_get_session_user(request), active=1,
                                        status=0).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def device_qun(device):
    return [_qun_to_json(x) for x in SnsUserGroup.objects.filter(active=1, status=0,
                                                                 sns_user__device__label=device).select_related(
        "sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def device_create(request, phone):
    dev = PhoneDevice.objects.filter(label=phone).first()
    if not dev:
        email = _get_session_user(request)
        if email:
            owner = User.objects.filter(email=email).first()
            if owner:
                PhoneDevice(label=phone, phone_num=phone, owner=owner).save()
    return "ok"


@api_func_anonymous
def qq_create(request, qq, name, phone, password):
    dev = PhoneDevice.objects.filter(label=phone).first()
    db = SnsUser.objects.filter(login_name=qq, type=0).first()
    if not db and dev:
        email = _get_session_user(request)
        if email:
            owner = User.objects.filter(email=email).first()
            SnsUser(login_name=qq, device=dev, name=name, passwd=password,
                    type=0, phone=phone, owner=owner, app_id=owner.app_id).save()

    return "ok"


@api_func_anonymous
def account_qun(sns_id):
    return [_qun_to_json(x) for x in
            SnsUserGroup.objects.filter(sns_user_id=sns_id, active=1,
                                        status=0).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def my_lost_qun(request):
    return [_qun_to_json(x) for x in
            SnsUserGroup.objects.filter(sns_user__owner__email=_get_session_user(request), active=0,
                                        status=-1).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def import_phone(ids):
    """
    device_id phone owner
    :param request:
    :param ids:
    :return:
    """
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = PhoneDevice.objects.filter(label=account[0]).first()
            if not db:
                user = None
                if len(account) > 2:
                    user = User.objects.filter(email=account[2]).first()

                device = PhoneDevice(label=account[0], phone_num=account[1], status=0)
                if user:
                    device.owner_id = user.id

                device.save()
                total += 1
            else:
                device.phone_num = account[1]
                if len(account) > 2:
                    user = User.objects.filter(email=account[2]).first()
                    if user:
                        device.owner_id = user.id

                db.save()

    return {
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def import_user(request, ids, app):
    """
    email name
    :return:
    """
    total = 0
    if not app:
        app = _get_session_app(request)
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = User.objects.filter(email=account[0]).first()
            if not db:
                User(email=account[0], name=account[1], status=0, passwd='testpwd', app_id=app).save()
                total += 1
            else:
                db.name = account[1]
                db.app_id = app
                db.save()

    return {
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def import_sns():
    pass


@api_func_anonymous
def import_useless_qun(ids):
    total = 0
    # if not app:
    #     app = _get_session_app(request)

    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            db = SnsGroup.objects.filter(group_id=line).first()
            if db:
                db.status = -2
                db.save()
                # db = SnsGroup()
                # 删除无效群的数据
                db.snsgroupsplit_set.all().delete()


@api_func_anonymous
def import_qun_stat(ids):
    """
    导入群的统计数据
    这个是完整的，如果之前在的群没了，说明被踢了
    :param ids:
    :return:
    """
    to_save = defaultdict(list)
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            if len(account) == 4 and account[0].isdigit():
                total += 1
                to_save[account[3]].append((account[0], account[1], account[2]))

    for k, accounts in to_save.items():
        sns_user = SnsUser.objects.filter(login_name=k, type=0).first()
        if sns_user:
            all_groups = sns_user.snsusergroup_set.all()
            all_group_ids = set()
            for (qun_num, qun_name, qun_user_cnt) in accounts:
                if qun_num in all_group_ids:
                    continue
                all_group_ids.add(qun_num)
                found = None
                for group in all_groups:
                    if qun_num == group.sns_group_id:
                        # in
                        found = group
                        break

                if not found:
                    # 新增
                    qun = SnsGroup.objects.filter(group_id=qun_num, type=0).first()
                    if not qun:
                        qun = SnsGroup(group_id=qun_num, group_name=qun_name, type=0, app_id=sns_user.app_id,
                                       group_user_count=qun_user_cnt, status=2)
                        qun.save()
                    else:
                        if qun.status != 2:
                            qun.status = 2
                            qun.save()

                    SnsUserGroup(sns_group=qun, sns_user=sns_user, status=0, active=1).save()
                else:
                    if found.status != 0:
                        found.status = 0
                        found.active = 1
                        found.save()

                    qun = found.sns_group

                    if qun.status != 2:
                        qun.status = 2

                    qun.group_user_count = qun_user_cnt
                    qun.save()

            for group in all_groups:
                if group.sns_group_id not in all_group_ids:
                    # 被踢了
                    SnsGroupLost(group_id=group.sns_group_id, sns_user=sns_user).save()
                    # SnsGroupSplit.objects.filter(group_id=group.group_id, status__gte=0).update(status=-1)
                    SnsGroupSplit.objects.filter(group_id=group.sns_group_id).delete()
                    group.status = -1
                    group.active = 0
                    group.save()


@api_func_anonymous
def import_qun(app, ids, request):
    """
    群号 群名 群人数 qq号[可选]
    :param app:
    :param ids:
    :param request:
    :return:
    """
    if not app:
        app = _get_session_app(request)
    cnt = 0
    total = 0
    exists = {x.group_id for x in SnsGroup.objects.filter(app_id=app)}
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = re.split('\s+', line)
            try:
                if account[0] in exists:
                    continue

                db = SnsGroup.objects.filter(group_id=account[0]).first()
                if not db:
                    db = SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                                  group_user_count=account[2])
                    db.save()
                    cnt += 1

                if len(account) > 3:
                    qq_num = account[3]
                    su = SnsUser.objects.filter(login_name=qq_num, type=0).first()
                    if su:
                        sug = SnsUserGroup.objects.filter(sns_user=su, sns_group=db).first()
                        if not sug:
                            sug = SnsUserGroup(sns_group=db, sns_user=su, status=0)
                        sug.active = 1
                        sug.save()
                        db.status = 2
                        db.snsgroupsplit_set.filter(status=0).update(status=1)
                        db.save()
            except:
                logger.warning("error save %s" % account)

    return {
        'count': cnt,
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def split_qq(app, request):
    if not app:
        app = _get_session_app(request)
    users = User.objects.filter(app_id=app, role=0)
    idx = 0
    forward = True

    for x in SnsGroup.objects.filter(app_id=app, status=0).order_by("-group_user_count"):
        x.status = 1
        user = users[idx]
        idx += 1 if forward else -1

        if idx == -1:
            idx = 0
            forward = not forward
        elif idx == len(users):
            idx = idx - 1
            forward = not forward

        SnsGroupSplit(group=x, user=user).save()
        x.save()

    return 'ok'


@api_func_anonymous
def export_qun(request, others, filter, device):
    user = _get_session_user(request)
    app = _get_session_app(request)
    # if user:
    #     db = User.objects.filter(email=email).first()
    #     if db:
    #         app = db.app_id

    if filter == '所有':
        db = SnsGroup.objects.filter(app_id=app)
        return ['%s\t%s\t%s' % (x.group_id, x.group_name, x.group_user_count) for x in db]
    elif filter == '分配情况':
        db = SnsGroupSplit.objects.filter(group__app_id=app).select_related('group', 'user')
        return ['%s\t%s\t%s\t%s' % (x.group.group_id, x.group.group_name, x.group.group_user_count, x.user.email) for x
                in db]
    elif filter == '未分配':
        db = SnsGroup.objects.filter(app_id=app, status=0)
        return ['%s\t%s\t%s' % (x.group_id, x.group_name, x.group_user_count) for x in db]
    elif filter == '特定手机':
        if not device:
            return []
        db = SnsGroupSplit.objects.filter(phone_id=device).select_related("group")
        return ['%s\t%s\t%s' % (x.group.group_id, x.group.group_name, x.group.group_user_count) for x in db]
    elif filter == '分配给':
        if not others:
            return []
        db = SnsGroupSplit.objects.filter(user__email=others).select_related("group")
        return ['%s\t%s\t%s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]

    elif user:
        db = SnsGroupSplit.objects.filter(user__email=user).select_related("group")
        if filter == '未指定手机':
            db = db.filter(phone__isnull=True)
            # db = db.filter(status=0)
        # if not full and len(db):
        #     SnsGroupSplit.objects.filter(user__email=user, status=0).update(status=1)
        return ['%s\t%s\t%s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]


@api_func_anonymous
def split_qun_to_device(request, email):
    user = email if email else _get_session_user(request)
    if user:
        phones = PhoneDevice.objects.filter(owner__email=user)
        idx = 0
        forward = True
        for x in SnsGroupSplit.objects.filter(user__email=user, phone__isnull=True):
            phone = phones[idx]
            idx += 1 if forward else -1

            if idx == -1:
                idx = 0
                forward = not forward
            elif idx == len(phones):
                idx = idx - 1
                forward = not forward

            x.phone = phone
            x.save()
    return 'ok'


@api_func_anonymous
def send_qq():
    pass


@api_func_anonymous
def apps():
    return [{'id': x.app_id, 'name': x.app_name} for x in App.objects.all()]


@api_func_anonymous
def app_summary(app_id):
    app = App.objects.filter(app_id=app_id).first()
    if app:
        cnt = SnsGroup.objects.filter(app=app).aggregate(Sum('group_user_count'))
        members = cnt['group_user_count__sum']
        cnt2 = SnsUserGroup.objects.filter(sns_user__app=app).aggregate(Sum('sns_group__group_user_count'))
        members2 = cnt2['sns_group__group_user_count__sum']
        return {
            'name': app.app_name,
            'qun_scan': SnsGroup.objects.filter(app=app).count(),
            'qun_scan_members': members if members else 0,
            'total_user': User.objects.filter(app=app).count(),
            'total_qq': SnsUser.objects.filter(type=0, app=app).count(),
            'total_wx': SnsUser.objects.filter(type=1, app=app).count(),
            'total_device': PhoneDevice.objects.filter(owner__app=app).count(),
            'qun_join': SnsUserGroup.objects.filter(sns_user__app=app).count(),
            'qun_join_members': members2 if members2 else 0
        }


@api_func_anonymous
def login(request, email, password):
    user = User.objects.filter(email=email).first()
    if user and password == user.passwd:
        request.session['user'] = email
        logger.info("User %s login." % user)
        return login_info(request)

    api_error(1001)


@api_func_anonymous
def login_info(request):
    email = _get_session_user(request)
    ret = {
        'email': email
    }

    if email:
        user = User.objects.filter(email=email).first()
        ret['app_id'] = user.app.app_id
        ret['app_name'] = user.app.app_name
        ret['username'] = user.name
    return ret


@api_func_anonymous
def logout(request):
    del request.session['user']
    return "ok"


@api_func_anonymous
def users(request, app_id):
    app = _get_session_app(request) if not app_id else app_id
    return [{'id': x.id, 'email': x.email, 'name': x.name} for x in User.objects.filter(app_id=app)]


@api_func_anonymous
def devices(request):
    email = _get_session_user(request)
    if email:
        return [{'id': x.id, 'label': x.label, 'num': x.phone_num}
                for x in PhoneDevice.objects.filter(owner__email=email)]


@api_func_anonymous
def accounts(request, device_id):
    email = _get_session_user(request)
    if email:
        return [_sns_user_to_json(x) for x in SnsUser.objects.filter(device_id=device_id)]


@api_func_anonymous
def account(sns_id):
    return _sns_user_to_json(SnsUser.objects.filter(id=sns_id).first())


@api_func_anonymous
def update_account(sns_id, password, name):
    sns_user = SnsUser.objects.filter(id=sns_id).first()
    if sns_user:
        sns_user.passwd = password
        if name:
            sns_user.name = name
        sns_user.save()

    return _sns_user_to_json(sns_user)


@api_func_anonymous
def task_types():
    return [{
        'id': x.id,
        'name': x.name,
        'memo': x.memo,
    } for x in SnsTaskType.objects.all()]


@api_func_anonymous
def create_task(type, params, phone, request):
    labels = re.split(';', phone)
    devices = model_manager.get_phones(labels)
    if devices:
        task_type = model_manager.get_task_type(type)
        task = SnsTask(name=task_type.name, type=task_type,
                       app_id=_get_session_app(request), status=0,
                       data=params, creator=model_manager.get_user(_get_session_user(request)))
        task.save()
        for device in devices:
            SnsTaskDevice(task=task, device=device, data=task.data).save()

        return "ok"
    api_error(1001, '不存在的手机')


TASK_STATUS_TEXT = ['已创建', '执行中', '已完成', '已中断']


@api_func_anonymous
def my_tasks(request):
    return [{
        'id': x.id,
        'name': x.name,
        'status': x.status,
        'type': x.type.name,
        'create_time': times.to_str(x.created_at),
        'creator': x.creator.name,
        'data': x.data,
        'status_text': TASK_STATUS_TEXT[x.status],
    } for x in SnsTask.objects.filter(creator__email=_get_session_user(request)).select_related(
        'creator', 'type').order_by('-pk')[:50]]


@api_func_anonymous
def task_devices(task_id):
    return [{
        'device': x.device.label,
        'create_time': times.to_str(x.created_at),
        'finish_time': times.to_str(x.finish_at),
        'status': x.status,
        'id': x.id,
        'status_text': TASK_STATUS_TEXT[x.status],
    } for x in SnsTaskDevice.objects.filter(task_id=task_id).select_related('device')]


@api_func_anonymous
def task_files(task_id, file_type):
    return [{
        'name': x.file_name,
        'id': x.id
    } for x in DeviceFile.objects.filter(device_task_id=task_id, type=file_type)]


@api_func_anonymous
def file_content(file_id):
    df = DeviceFile.objects.filter(id=file_id).first()
    if df and df.type != 'image':
        return _get_content(df.qiniu_key)

    return "" if not df else HttpResponseRedirect('%s%s' % (settings.QINIU_URL, df.qiniu_key))


@api_func_anonymous
def online_phones(request):
    return [_device_to_json(x.device) for x in model_manager.get_online(_get_session_user(request))]


def _device_to_json(x):
    return {
        'id': x.id,
        'label': x.label,
        'num': x.phone_num
    }


def _qun_to_json(x):
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


def _sns_user_to_json(sns_user):
    return {
        'id': sns_user.id,
        'name': sns_user.name,
        'type': sns_user.type,
        'login': sns_user.login_name,
        'password': sns_user.passwd,
        'phone': sns_user.phone,
        'memo': sns_user.memo
    } if sns_user else {}


def _after_upload_file(ftype, fid, local_file):
    pass


def _get_session_user(request):
    return request.session.get('user')


def _get_session_app(request):
    email = _get_session_user(request)
    user = User.objects.filter(email=email).first()
    if user:
        return user.app_id
    else:
        return DEFAULT_APP


def _upload_to_qiniu(device_id, task, type, name, file):
    q = Auth(settings.QINIU_AK, settings.QINIU_SK)
    ts = int(datetime.now().timestamp())
    key = 'sns/%s/%s/%s/%s/%s' % (task, device_id, type, ts, name)
    token = q.upload_token(settings.QINIU_BUCKET, key)
    ret, info = put_file(token, key, file)
    return key if ret['key'] == key and ret['hash'] == etag(file) else None


def _get_content(qiniu_key):
    return requests.get('%s%s' % (settings.QINIU_URL, qiniu_key)).text
