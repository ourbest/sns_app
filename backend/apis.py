import os
import re
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from urllib.parse import quote

import requests
from dj import times
from dj.utils import api_func_anonymous, api_error
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import Sum
from django.http import HttpResponseRedirect
from django.utils import timezone
from logzero import logger
from qiniu import Auth, put_file, etag

from backend import model_manager, api_helper
from backend.api_helper import get_session_user, get_session_app, sns_user_to_json, device_to_json, qun_to_json
from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice, SnsUser, SnsUserGroup, SnsTaskDevice, \
    DeviceFile, SnsTaskType, SnsTask, ActiveDevice, SnsApplyTaskLog, DistTaskLog, UserActionLog, SnsGroupLost

executor = ThreadPoolExecutor(max_workers=2)


@api_func_anonymous
def get_menu(request):
    return model_manager.get_user_menu(model_manager.get_user(api_helper.get_session_user(request)))


@api_func_anonymous
def upload(type, id, task_id, request):
    logger.info("upload %s %s %s" % (type, id, task_id))
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
    device = model_manager.get_phone(id)
    device_task = None
    if device:
        ad = model_manager.get_active_device(device)
        if not ad:
            ad = ActiveDevice(device=device, status=0, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = 0
        ad.save()

        if task_id.isdigit():
            device_task = SnsTaskDevice.objects.filter(device__label=id, task_id=task_id).first()
            if device_task:
                logger.debug("find device task %s" % device_task.id)
                if device_task.status != 2:
                    model_manager.mark_task_finish(device_task)

                device_file = DeviceFile(device=device, task_id=device_task.task_id, qiniu_key=key,
                                         file_name=name, type=type, device_task=device_task)
                device_file.save()

                # if device_task.task.type_id == 4:  # 统计
                #     with open(tmp_file, 'rt', encoding='utf-8') as f:
                #         import_qun_stat(f.read(), id)
                # elif device_task.task.type_id == 1:  # 查群
                #     with open(tmp_file, 'rt', encoding='utf-8') as f:
                #         import_qun(device_task.task.app_id, f.read(), None)
                # elif device_task.task.type_id == 2:  # 加群
                #     with open(tmp_file, 'rt', encoding='utf-8') as f:
                #         import_add_result(device_task, f.read())
                # elif device_task.task.type_id == 3: # 分发
                #     with open(tmp_file, 'rt', encoding='utf-8') as f:
                #         import_add_result(device_task, f.read())

    executor.submit(_after_upload, device_task, task_id, tmp_file, device)
    return "ok"


def _after_upload(device_task, task_id, tmp_file, device):
    logger.info('after upload import temp file %s' % tmp_file)
    if device_task:
        if device_task.task.type_id == 4:  # 统计
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_qun_stat(f.read(), device.label)
        elif device_task.task.type_id == 1:  # 查群
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_qun(device_task.task.app_id, f.read(), None)
        elif device_task.task.type_id == 2:  # 加群
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_add_result(device_task, f.read())
        elif device_task.task.type_id == 3:  # 分发
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_dist_result(device_task, f.read())
    if type == 'result':
        if task_id == 'stat':
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_qun_stat(f.read(), None)
        elif task_id == 'qun':
            with open(tmp_file, 'rt', encoding='utf-8') as f:
                import_qun(device.owner.app_id, f.read())
    os.remove(tmp_file)


def import_dist_result(device_task, lines):
    """
    1列群号，2列结果，3列QQ号，结果：已分发、被禁言、被踢出
    :param device_task:
    :param lines:
    :return:
    """
    for line in lines.split('\n'):
        line = line.strip()
        try:
            [qun_id, status, qq_id] = re.split('\s+', line)
            qun = model_manager.get_qun(qun_id)
            qq = model_manager.get_qq(qq_id)

            DistTaskLog(task=device_task, group=qun, sns_user=qq, status=status,
                        success=1 if status == '已分发' else 0).save()

            if status == '被踢出':
                ug = qun.snsusergroup_set.filter(sns_user=qq).first()
                if ug:
                    model_manager.set_qun_kicked(ug)
        except:
            logger.warning('error import line %s' % line, exc_info=1)


def import_add_result(device_task, lines):
    """
    1列 群号，2列 属性，3列QQ号
    属性有这些：付费群，不存在，不允许加入，需要回答问题，已发送验证，满员群，已加群，无需验证已加入
    :param device_task:
    :param lines:
    :return:
    """
    for line in lines.split('\n'):
        line = line.strip()
        try:
            [qun_id, status, qq_id] = re.split('\s+', line)
            qun = model_manager.get_qun(qun_id)
            qq = model_manager.get_qq(qq_id)
            SnsApplyTaskLog(device=device_task.device, device_task=device_task, account=qq, memo=status,
                            group=qun).save()
            if status in ('付费群', '不存在', '不允许加入'):
                model_manager.set_qun_useless(qun)
            elif status in ('已加群', '无需验证已加入'):
                model_manager.set_qun_join(qq, qun)
            elif status in ('已发送验证',):
                model_manager.set_qun_applying(device_task.device, qun)
            elif status in ('需要回答问题',):
                model_manager.set_qun_manual(qun)
            elif status in ('无需验证未加入',):
                pass
        except:
            logger.warning('error import line %s' % line, exc_info=1)

    model_manager.reset_qun_status(device_task)


def _make_task_content(device_task):
    data = device_task.data
    if device_task.task.type_id == 2:
        # 加群
        model_manager.reset_qun_status(device_task)
        data = api_helper.add_add_qun(device_task)
    elif device_task.task.type_id == 3:
        # 分发
        data = api_helper.to_share_url(device_task.device.owner, data,
                                       label=device_task.device.label) + api_helper.add_dist_qun(device_task)
    return '[task]\nid=%s\ntype=%s\n[data]\n%s' % (device_task.task_id, device_task.task.type_id, data)


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

        for x in SnsTaskDevice.objects.filter(device__label=id, status=1):
            model_manager.mark_task_cancel(x)

        device_task = SnsTaskDevice.objects.filter(device__label=id, status=0,
                                                   schedule_at__lte=timezone.now()).first()
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
        email = get_session_user(request)

    return [sns_user_to_json(x) for x in SnsUser.objects.filter(owner__email=email).order_by("phone")]


@api_func_anonymous
def my_qun(request, i_page, i_size, keyword):
    query = SnsUserGroup.objects.filter(sns_user__owner__email=get_session_user(request),
                                        status=0).select_related("sns_group", "sns_user", "sns_user__device")
    if i_page != 0:
        if i_size == 0:
            i_size = 50

    if keyword:
        query = query.filter(sns_group__group_id__contains=keyword)

    query = query[(i_page - 1) * i_size:i_page * i_size]

    return [qun_to_json(x) for x in query]


@api_func_anonymous
def my_kicked_qun(request, i_page, i_size, keyword):
    query = SnsGroupLost.objects.filter(sns_user__owner__email=get_session_user(request),
                                        status=0).order_by("-pk").select_related("group", "sns_user",
                                                                                 "sns_user__device")
    if i_page != 0:
        if i_size == 0:
            i_size = 50

    if keyword:
        query = query.filter(group__group_id__contains=keyword)

    cnt = query.count()
    query = query[(i_page - 1) * i_size:i_page * i_size]

    return {
        'total': cnt,
        'items': [api_helper.lost_qun_to_json(x) for x in query],
    }


@api_func_anonymous
def my_qun_cnt(request):
    return str(SnsUserGroup.objects.filter(sns_user__owner__email=get_session_user(request), status=0).count())


@api_func_anonymous
def my_pending_qun(request, i_size, i_page, keyword):
    if i_size == 0:
        i_size = 50

    if i_page == 0:
        i_page = 1

    i_page -= 1

    query = SnsGroupSplit.objects.filter(user__email=get_session_user(request),
                                         status__in=(0, 1, 2)).select_related("group")
    if keyword:
        query = query.filter(group__group_id__contains=keyword)
    return {
        'total': len(query),
        'page': i_page + 1,
        'items': [api_helper.sns_group_to_json(x.group) for x in query[i_page * i_size:(i_page + 1) * i_size]]
    }


@api_func_anonymous
def my_quiz_qun(request, i_size, i_page, keyword):
    if i_size == 0:
        i_size = 50

    if i_page == 0:
        i_page = 1

    i_page -= 1

    query = SnsGroupSplit.objects.filter(user__email=get_session_user(request),
                                         status=-1).select_related("group")

    if keyword:
        query = query.filter(group__group_id__contains=keyword)
    return {
        'total': len(query),
        'page': i_page + 1,
        'items': [api_helper.sns_group_to_json(x.group) for x in query[i_page * i_size:(i_page + 1) * i_size]]
    }


@api_func_anonymous
def device_qun(device):
    return [qun_to_json(x) for x in SnsUserGroup.objects.filter(active=1, status=0,
                                                                sns_user__device__label=device).select_related(
        "sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def device_create(request, phone):
    dev = model_manager.get_phone(phone)
    if not dev:
        email = get_session_user(request)
        if email:
            owner = User.objects.filter(email=email).first()
            if owner:
                PhoneDevice(label=phone, phone_num=phone, owner=owner).save()
    return "ok"


@api_func_anonymous
def device_transfer(label, to_user):
    user = model_manager.get_user(to_user)
    if not user:
        api_error(1, '错误的邮箱')

    dev = model_manager.get_phone(label)
    if dev:
        owner = dev.owner
        if owner.email != to_user:
            dev.owner = user
            dev.save()

            SnsUser.objects.filter(device=dev).update(owner=user)

            UserActionLog(action='转交', memo='%s转交给%s' % (label, user.name), user=owner).save()

    return 'ok'


@api_func_anonymous
def qq_transfer(qq, phone):
    """
    转移
    :param qq:
    :param phone:
    :return:
    """
    device = model_manager.get_phone(phone)
    sns_user = model_manager.get_qq(qq)

    if not sns_user:
        api_error(1, '错误的QQ')
    elif not device:
        api_error(1, '没找到电话记录')

    if sns_user.phone != phone:
        old_phone = sns_user.phone
        owner = sns_user.owner
        sns_user.phone = phone
        sns_user.device = device
        sns_user.owner = device.owner

        sns_user.save()

        UserActionLog(action='转绑', memo='从%s变成%s' % (old_phone, phone), user=owner).save()

    return 'ok'


@api_func_anonymous
def qq_create(request, qq, name, phone, password):
    dev = PhoneDevice.objects.filter(label=phone).first()
    db = SnsUser.objects.filter(login_name=qq, type=0).first()
    if not db and dev:
        email = get_session_user(request)
        if email:
            owner = User.objects.filter(email=email).first()
            SnsUser(login_name=qq, device=dev, name=name, passwd=password,
                    type=0, phone=phone, owner=owner, app_id=owner.app_id).save()

    return "ok"


@api_func_anonymous
def account_qun(sns_id):
    return [qun_to_json(x) for x in
            SnsUserGroup.objects.filter(sns_user_id=sns_id, active=1,
                                        status=0).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def my_lost_qun(request):
    return [qun_to_json(x) for x in
            SnsUserGroup.objects.filter(sns_user__owner__email=get_session_user(request), active=0,
                                        status=-1).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def import_qun_join(request, ids):
    """
    qun
    :param request:
    :param ids:
    :return:
    """
    self = model_manager.get_user(get_session_user(request))
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            if len(account) == 2 and account[0].isdigit():
                [qun_num, phone] = account
                split = SnsGroupSplit.objects.filter(group_id=qun_num, user=self).first()
                device = model_manager.get_phone(phone)
                if not split:
                    split = SnsGroupSplit(group_id=qun_num, user=self, status=2, phone=device)
                else:
                    split.user = self
                    split.phone = device
                    if split.status <= 1:
                        split.status = 2
                split.save()
                total += 1

    return {
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def import_phone(request, ids):
    """
    device_id phone owner
    :param request:
    :param ids:
    :return:
    """
    self = get_session_user(request)
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = PhoneDevice.objects.filter(label=account[0]).first()
            user = User.objects.filter(email=account[2]).first() if len(account) > 2 else  self

            label = account[0]
            phone_num = label if len(account) == 1 else account[1]

            if not db:
                device = PhoneDevice(label=label, phone_num=phone_num, status=0)
                if user:
                    device.owner_id = user.id

                device.save()
                total += 1
            else:
                device.phone_num = phone_num
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
        app = get_session_app(request)
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
                model_manager.set_qun_useless(db)


@api_func_anonymous
def import_qun_stat(ids, device_id):
    """
    导入群的统计数据
    这个是完整的，如果之前在的群没了，说明被踢了
    :param ids:
    :return:
    """
    logger.info('import stat of %s', device_id)
    to_save = defaultdict(list)
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            if len(account) == 4 and account[0].isdigit():
                total += 1
                to_save[account[3]].append((account[0], account[1], account[2]))

    device = model_manager.get_phone(device_id)

    for k, accounts in to_save.items():
        sns_user = SnsUser.objects.filter(login_name=k, type=0).first()
        logger.info("Sns user %s not found device is %s", k, device_id)
        if device and not sns_user:
            sns_user = SnsUser(name=k, login_name=k, passwd='_',
                               phone=device.phone_num, device=device,
                               owner=device.owner, app=device.owner.app)
            sns_user.save()

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
                    qun.group_name = qun_name
                    qun.group_user_count = qun_user_cnt
                    qun.save()

            for group in all_groups:
                lost = 0
                if group.sns_group_id not in all_group_ids:
                    # 被踢了
                    model_manager.set_qun_kicked(group)
                    lost += 1
                logger.info("total lost %s", lost)

    logger.info('Import done total %s', total)


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
        app = get_session_app(request)
    cnt = 0
    total = 0
    exists = {x.group_id for x in SnsGroup.objects.filter(app_id=app)}
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = re.split('\s+', line)
            try:
                if not account[0].isdigit() and account[0] in exists:
                    continue

                db = SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                              group_user_count=account[2])
                db.save()
                cnt += 1

                if len(account) > 3:
                    if not db:
                        db = model_manager.get_qun(account[0])
                    qq_num = account[3]
                    su = SnsUser.objects.filter(login_name=qq_num, type=0).first()
                    if db and su:
                        sug = SnsUserGroup.objects.filter(sns_user=su, sns_group=db).first()
                        if not sug:
                            sug = SnsUserGroup(sns_group=db, sns_user=su, status=0)
                        sug.active = 1
                        sug.save()
                        db.status = 2
                        db.snsgroupsplit_set.filter(status=0).update(status=3)
                        db.save()
            except:
                logger.warning("error save %s" % account)

    return {
        'count': cnt,
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def import_qun_split(app, ids, request):
    """
    群号 邮箱 手机号 群名 群人数
    :param app:
    :param ids:
    :param request:
    :return:
    """
    if not app:
        app = get_session_app(request)
    cnt = 0
    total = 0
    exists = {x.group_id for x in SnsGroup.objects.filter(app_id=app)}
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = re.split('\s+', line)
            qun_id = account[0]
            qun_name = 'NA' if len(account) < 4 else account[3]
            member_cnt = 0 if len(account) < 5 or not account[4].isdigit() else int(account[4])
            user_email = get_session_user(request) if len(account) < 2 else account[1]
            phone = None if len(account) < 3 else account[2]

            try:
                if not qun_id.isdigit() and qun_id in exists:
                    continue

                qun_id = account[0]
                db = SnsGroup(group_id=qun_id, group_name=qun_name, type=0, app_id=app,
                              group_user_count=member_cnt)
                db.save()
                cnt += 1
            except:
                logger.warning("error save %s" % account, exc_info=1)
                db = None

            # if not db:
            #     db = model_manager.get_qun(qun_id)
            split = SnsGroupSplit(group_id=qun_id, user=model_manager.get_user(user_email))
            if phone:
                split.phone = model_manager.get_phone(phone)

            try:
                split.save()
            except:
                logger.warning('error save split %s' % split, exc_info=1)

    return {
        'count': cnt,
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def split_qq(app, request):
    if not app:
        app = get_session_app(request)
    users = [x for x in User.objects.filter(app_id=app, status=0) if x.phonedevice_set.filter(status=0).count() > 0]
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
    user = get_session_user(request)
    app = get_session_app(request)
    # if user:
    #     db = User.objects.filter(email=email).first()
    #     if db:
    #         app = db.app_id

    if filter == '所有':
        db = SnsGroup.objects.filter(app_id=app).order_by("-pk")
        return ['%s\t%s\t%s' % (x.group_id, x.group_name, x.group_user_count) for x in db]
    elif filter == '分配情况':
        db = SnsGroupSplit.objects.filter(group__app_id=app).select_related('group', 'user').order_by("-pk")
        return ['%s\t%s\t%s\t%s' % (x.group.group_id, x.group.group_name, x.group.group_user_count, x.user.email) for x
                in db]
    elif filter == '未分配':
        db = SnsGroup.objects.filter(app_id=app, status=0).order_by("-pk")
        return ['%s\t%s\t%s' % (x.group_id, x.group_name, x.group_user_count) for x in db]
    elif filter == '特定手机':
        if not device:
            return []
        db = SnsGroupSplit.objects.filter(phone_id=device).select_related("group").order_by("-pk")
        return ['%s\t%s\t%s' % (x.group.group_id, x.group.group_name, x.group.group_user_count) for x in db]
    elif filter == '分配给':
        if not others:
            return []
        db = SnsGroupSplit.objects.filter(user__email=others).select_related("group").order_by("-pk")
        return ['%s\t%s\t%s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]

    elif user:
        db = SnsGroupSplit.objects.filter(user__email=user).select_related("group").order_by("-pk")
        if filter == '未指定手机':
            db = db.filter(phone__isnull=True)
            # db = db.filter(status=0)
        # if not full and len(db):
        #     SnsGroupSplit.objects.filter(user__email=user, status=0).update(status=1)
        return ['%s\t%s\t%s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]


@api_func_anonymous
def split_qun_to_device(request, email):
    user = email if email else get_session_user(request)
    if user:
        phones = PhoneDevice.objects.filter(owner__email=user, status=0)
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
def reset_phone_split(request):
    user = get_session_user(request)
    if user:
        phones = PhoneDevice.objects.filter(owner__email=user, status=0)
        idx = 0
        forward = True
        for x in SnsGroupSplit.objects.filter(user__email=user, status=0):
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
def apps(request):
    user = model_manager.get_user(get_session_user(request))
    apps = user.userauthapp_set.all()
    ret = [{'id': user.app.app_id, 'name': user.app.app_name}]
    ret += [{'id': x.app.app_id, 'name': x.app.app_name} for x in apps if x.app_id != user.app_id]

    return ret  # [{'id': x.app_id, 'name': x.app_name} for x in App.objects.all()]


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
    if api_helper.auth(email, password):
        request.session['user'] = email
        logger.info("User %s login." % email)
        return login_info(request)

    api_error(1001)


@api_func_anonymous
def login_info(request):
    email = get_session_user(request)
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
    app = get_session_app(request) if not app_id else app_id
    return [{'id': x.id, 'email': x.email, 'name': x.name, 'role': x.role} for x in User.objects.filter(app_id=app)]


@api_func_anonymous
def devices(request, email, i_uid, i_active):
    if i_uid:
        online = {x.device_id for x in model_manager.get_online_by_id(i_uid)}
        query = PhoneDevice.objects.filter(owner_id=i_uid)
        if i_active:
            query = query.filter(status=0)
        return [{'id': x.id, 'label': x.label, 'num': x.phone_num, 'online': x.id in online, 'status': x.status}
                for x in query]

    email = email if email else get_session_user(request)
    if email:
        online = {x.device_id for x in model_manager.get_online(email)}
        query = PhoneDevice.objects.filter(owner__email=email)
        if i_active:
            query = query.filter(status=0)
        return [{'id': x.id, 'label': x.label, 'num': x.phone_num, 'online': x.id in online, 'status': x.status}
                for x in query]


@api_func_anonymous
def accounts(request, device_id):
    email = get_session_user(request)
    if email:
        return [sns_user_to_json(x) for x in SnsUser.objects.filter(device_id=device_id)]


@api_func_anonymous
def account(sns_id):
    return sns_user_to_json(SnsUser.objects.filter(id=sns_id).first())


@api_func_anonymous
def update_account(sns_id, password, name):
    sns_user = SnsUser.objects.filter(id=sns_id).first()
    if sns_user:
        sns_user.passwd = password
        if name:
            sns_user.name = name
        sns_user.save()

    return sns_user_to_json(sns_user)


@api_func_anonymous
def update_account_attr(sns_id, name, value):
    if value.isdigit():
        value = int(value)

    sns_user = SnsUser.objects.filter(id=sns_id).first()
    if sns_user:
        setattr(sns_user, name, value)
        sns_user.save()

    return sns_user_to_json(sns_user)


@api_func_anonymous
def update_device_attr(i_device_id, name, value):
    if value.isdigit():
        value = int(value)

    device = PhoneDevice.objects.filter(id=i_device_id).first()
    if device:
        setattr(device, name, value)
        device.save()

    return 'ok'


@api_func_anonymous
def update_user_group_attr(sns_id, name, value):
    if value.isdigit():
        value = int(value)

    sns_user = SnsGroup.objects.filter(group_id=sns_id).first()
    if sns_user:
        setattr(sns_user, name, value)
        sns_user.save()

    return 'ok'


@api_func_anonymous
def task_types():
    return [{
        'id': x.id,
        'name': x.name,
        'memo': x.memo,
    } for x in SnsTaskType.objects.all()]


@api_func_anonymous
def update_task_status(device_task_id, i_status):
    db = SnsTaskDevice.objects.filter(pk=device_task_id).first()
    if db and db.status != i_status:
        db.status = i_status
        db.save()
        model_manager.check_task_status(db.task)


@api_func_anonymous
def create_task(type, params, phone, request, date):
    labels = re.split(';', phone)
    devices = model_manager.get_phones(labels)
    scheduler_date = timezone.make_aware(datetime.strptime(date, '%Y-%m-%d %H:%M')) if date else None
    if devices:
        task_type = model_manager.get_task_type(type)
        task = SnsTask(name=task_type.name, type=task_type,
                       app_id=get_session_app(request), status=0, schedule_at=scheduler_date,
                       data=params, creator=model_manager.get_user(get_session_user(request)))
        task.save()
        for device in devices:
            SnsTaskDevice(task=task, device=device, schedule_at=scheduler_date, data=task.data).save()

        return "ok"
    api_error(1001, '不存在的手机')


TASK_STATUS_TEXT = ['等待执行', '执行中', '已完成', '已中断', '已取消']


@api_func_anonymous
def my_tasks(request):
    return [{
        'id': x.id,
        'name': x.name,
        'status': x.status,
        'type': x.type.name,
        'create_time': times.to_str(x.created_at),
        'schedule_time': times.to_str(x.schedule_at),
        'creator': x.creator.name,
        'data': x.data,
        'status_text': TASK_STATUS_TEXT[x.status],
    } for x in SnsTask.objects.filter(creator__email=get_session_user(request)).select_related(
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
def device_tasks(device):
    return [{
        'id': x.id,
        'name': x.task.name,
        'status': x.status,
        'type': x.task.type.name,
        'started_at': times.to_str(x.started_at),
        'finish_at': times.to_str(x.finish_at),
        'data': x.data,
        'status_text': TASK_STATUS_TEXT[x.status],
    } for x in SnsTaskDevice.objects.filter(device__label=device).select_related(
        'task', 'task__type').order_by('-pk')[:50]]


@api_func_anonymous
def task_files(i_task_id, file_type):
    return [{
        'name': x.file_name,
        'id': x.id
    } for x in DeviceFile.objects.filter(device_task_id=i_task_id, type=file_type)]


@api_func_anonymous
def file_content(i_file_id, i_att):
    df = DeviceFile.objects.filter(id=i_file_id).first()
    if i_att != 1 and df and df.type != 'image':
        return _get_content(df.qiniu_key)

    return "" if not df else HttpResponseRedirect('%s%s%s'
                                                  % (settings.QINIU_URL, df.qiniu_key,
                                                     '?attname=' + quote(df.file_name) if i_att else ''))


@api_func_anonymous
def online_phones(request):
    return [device_to_json(x.device) for x in model_manager.get_online(get_session_user(request))]


def _upload_to_qiniu(device_id, task, type, name, file):
    q = Auth(settings.QINIU_AK, settings.QINIU_SK)
    ts = int(datetime.now().timestamp())
    key = 'sns/%s/%s/%s/%s/%s' % (task, device_id, type, ts, name)
    token = q.upload_token(settings.QINIU_BUCKET, key)
    ret, info = put_file(token, key, file)
    return key if ret['key'] == key and ret['hash'] == etag(file) else None


def _get_content(qiniu_key):
    resp = requests.get('%s%s' % (settings.QINIU_URL, qiniu_key))
    resp.encoding = 'utf-8'
    return resp.text
