import csv
import os
import re
import threading
from collections import defaultdict
from datetime import datetime, timedelta
from shutil import copyfile
from urllib.parse import quote

import requests
from dj import times
from dj.utils import api_func_anonymous, api_error
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.db.models import Sum
from django.http import HttpResponseRedirect, HttpResponse
from django.utils import timezone
from logzero import logger
from qiniu import Auth, put_file, etag

from backend import model_manager, api_helper, caches, stats, group_splitter
from backend.api_helper import get_session_user, get_session_app, sns_user_to_json, device_to_json, qun_to_json, \
    deal_dist_result, deal_add_result, ADD_STATUS, parse_dist_article
from backend.model_manager import save_ignore
from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice, SnsUser, SnsUserGroup, SnsTaskDevice, \
    DeviceFile, SnsTaskType, SnsTask, ActiveDevice, SnsApplyTaskLog, UserActionLog, SnsGroupLost, GroupTag, \
    TaskWorkingLog, AppUser, DeviceTaskData, SnsUserKickLog, DistArticle, UserAuthApp, WxDistLog, DistTaskLog
from backend.zhiyue_models import ZhiyueUser, ClipItem


@api_func_anonymous
def get_menu(request):
    return model_manager.get_user_menu(model_manager.get_user(api_helper.get_session_user(request)))


@api_func_anonymous
def upload(type, id, task_id, content, name, request):
    logger.info("upload %s %s %s" % (type, id, task_id))

    tmp_file = "/tmp/%s/%s" % (task_id, name)
    if content:
        with open(tmp_file, "wt") as out:
            out.write(content)
    elif 'file' not in request.FILES:
        api_error(1000, '没有上传的文件')
    else:
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
    device_file = None
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
                if device_task.status not in (3, 2):
                    if device_task.status == 12:
                        model_manager.mark_task_cancel(device_task)
                    else:
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

    if device_file:
        thread = threading.Thread(target=re_import, args=(device_file.id,))
        thread.start()
    else:
        dest = '/tmp/%s' % timezone.now().timestamp()
        copyfile(tmp_file, dest)
        thread = threading.Thread(target=_after_upload, args=(device_task, task_id, dest, device, type))
        thread.start()

    return "ok"


def _after_upload(device_task, task_id, tmp_file, device, file_type):
    if file_type == 'result':
        logger.info('after upload import temp file %s task_id is %s file type is %s' % (tmp_file, task_id, file_type))
        with open(tmp_file, 'rt', encoding='utf-8') as f:
            upload_file_content = f.read()
            if device_task:
                logger.info('The type is %s', device_task.task.type_id)
                if device_task.task.type_id == 4:  # 统计
                    import_qun_stat(upload_file_content, device.label, device_task.status)
                elif device_task.task.type_id == 1:  # 查群
                    logger.info('查群结果')
                    import_qun(device_task.task.app_id, upload_file_content,
                               None, device_task.device.owner.email, None, None, False)
                elif device_task.task.type_id == 2:  # 加群
                    import_add_result(device_task, upload_file_content)
                elif device_task.task.type_id == 3:  # 分发
                    import_dist_result(device_task, upload_file_content)
                elif device_task.task.type_id == 5:  # 微信分发
                    import_wx_dist_result(device_task, upload_file_content)
                api_helper.merge_task_result(device_task.task, upload_file_content)

            if task_id == 'stat':
                import_qun_stat(upload_file_content, None, 2)
            elif task_id == 'qun':
                import_qun(device.owner.app_id, upload_file_content, None, device.owner.email, None, None, False)
    os.remove(tmp_file)


def import_wx_dist_result(device_task, lines):
    reg = r'(.+)\t\((\d+)\)$'
    for line in lines.split('\n'):
        match = re.match(reg, line)
        if match:
            (name, cnt) = match.groups()
            log = WxDistLog(task=device_task, group_name=name if len(name) < 100 else (name[0:90] + '...'),
                            user_count=cnt)
            log.save()


def import_dist_result(device_task, lines):
    """
    1列群号，2列结果，3列QQ号，结果：已分发、被禁言、被踢出
    :param device_task:
    :param lines:
    :return:
    """
    kicked = 0
    add = False
    dist_ed_qq = set()

    content = get_task_content(device_task)
    should_done = set()

    has_unknown = 0

    removed = list()

    for line in content.split('\n'):
        line = line.strip()
        if line.find('QQ_') == 0:
            should_done.add(line.split('=')[1])

    for line in lines.split('\n'):
        line = line.strip()
        if line:
            if line.find('删除帐号=') == 0:
                qq_id = line[len('删除帐号='):]
                if qq_id in should_done:
                    SnsUserKickLog(sns_user=model_manager.get_qq(qq_id), device_task=device_task).save()
                    dist_ed_qq.add(qq_id)
                    removed.append(qq_id)
                else:
                    has_unknown += 1
                continue
            try:
                values = re.split('\s+', line)
                if len(values) == 3:
                    [qun_id, status, qq_id] = values
                    qun = model_manager.get_qun(qun_id)
                    if not qun:
                        logger.warning('日志中的群号没有记录%s' % qun_id)
                        continue
                    qq = model_manager.get_qq(qq_id)

                    if status in ADD_STATUS:
                        add = True
                        deal_add_result(device_task, qq, qun, status)
                    else:
                        dist_ed_qq.add(qq_id)
                        if deal_dist_result(device_task, qq, qun, status):
                            kicked += 1
            except:
                logger.warning('error import line %s' % line, exc_info=1)

    message = ''
    if add:
        model_manager.reset_qun_status(device_task)

    if has_unknown:
        #     should_done.discard(dist_ed_qq)
        #     if has_unknown == len(should_done):
        #         for qq_id in should_done:
        #             SnsUserKickLog(sns_user=model_manager.get_qq(qq_id), device_task=device_task).save()
        #             removed.add(qq_id)
        # else:
        removed.append('%s个未知QQ' % has_unknown)

    if len(removed):
        message += '（%s）账号从QQ移除了😭，' % (' '.join(removed))

    if kicked:
        model_manager.deal_kicked(device_task.device.owner)
        message += '此次分发检测到被踢了%s个群😢，' % kicked

    if message:
        api_helper.webhook(device_task, '注意：' + message + '请检查', force=len(removed) > 0)

    return kicked


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
            values = re.split('\s+', line)
            if len(values) == 3:
                [qun_id, status, qq_id] = values
                qun = model_manager.get_qun(qun_id)
                qq = model_manager.get_qq(qq_id)
                db = SnsApplyTaskLog.objects.filter(device=device_task.device,
                                                    device_task=device_task,
                                                    account=qq, group=qun).first()
                if not db:
                    deal_add_result(device_task, qq, qun, status)
        except:
            logger.warning('error import line %s' % line, exc_info=1)

    model_manager.reset_qun_status(device_task)


def _make_task_content(device_task):
    data = device_task.data
    task_type = device_task.task.type_id
    if task_type == 2:
        # 加群
        model_manager.reset_qun_status(device_task)
        data = api_helper.add_add_qun(device_task)
    elif task_type == 3:
        # 分发
        data = api_helper.to_share_url(device_task.device.owner, data,
                                       label=device_task.device.label) + api_helper.add_dist_qun(device_task)
    elif task_type == 5:
        data = api_helper.to_share_url(device_task.device.owner, data,
                                       label=device_task.device.label,
                                       share_type=1) + api_helper.add_wx_params(device_task)

    if task_type in (3, 5) and not device_task.task.article:
        parse_dist_article(data, device_task.task)

    return '[task]\nid=%s\ntype=%s\n[data]\n%s' % (device_task.task_id, task_type, data)


@api_func_anonymous
def task(id, i_text=0):
    device = model_manager.get_phone(id)
    if device:
        ad = model_manager.get_active_device(device)
        if not ad:
            ad = ActiveDevice(device=device, status=0, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = 0

        for x in SnsTaskDevice.objects.filter(device__label=id, status__in=(1, 10, 11, 12)):
            model_manager.mark_task_cancel(x)

        device_task = SnsTaskDevice.objects.filter(device__label=id, status=0,
                                                   schedule_at__lte=timezone.now()).first()
        if device_task:
            try:
                content = get_task_content(device_task)
                ad.status = 1
                ad.save()

                logger.info("发送任务%s - %s" % (device_task.id, id))

                return {
                    'name': 'task.txt',
                    'content': content
                } if i_text == 0 else HttpResponse(content, content_type='application/octet-stream')
            except:
                logger.warning('Error process task %s' % id, exc_info=1)

        else:
            ad.status = 0
        ad.save()

    return {} if i_text == 0 else HttpResponse('', content_type='application/octet-stream')


def get_task_content(device_task):
    old_db = DeviceTaskData.objects.filter(device_task=device_task).first()
    if old_db:
        content = old_db.lines
    else:
        content = _make_task_content(device_task)
        DeviceTaskData(device_task=device_task, lines=content).save()
    return content


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
            device = PhoneDevice.objects.filter(label=account[3]).first()
            if not db:
                db = SnsUser(passwd=account[1], type=0, login_name=account[0],
                             owner=device.owner, app_id=device.owner.app_id,
                             name=account[2], phone=account[3], device=device)
                # if device:
                #     db.owner = device.owner
                #     db.app_id = device.owner.app_id
                db.save()
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
def team_qq(request):
    return [sns_user_to_json(x, owner=1) for x in
            SnsUser.objects.filter(owner__app_id=get_session_app(request)).select_related("owner").order_by("phone")]


@api_func_anonymous
def team_qun_stat(request):
    app_id = get_session_app(request)
    total = SnsUserGroup.objects.filter(sns_user__owner__app=app_id, status=0).count()
    distinct = SnsUserGroup.objects.filter(sns_user__owner__app=app_id, status=0).values(
        'sns_group').distinct().count()
    total_user = SnsGroup.objects.filter(app_id=app_id).extra(where=["""
    NOT EXISTS (SELECT 1 FROM backend_snsusergroup g WHERE status = 0 and g.parent_id = backend_snsgroup.id)
"""])


@api_func_anonymous
def my_qun(request, i_page, i_size, keyword, qq, phone, tag):
    query = SnsUserGroup.objects.filter(sns_user__owner__email=get_session_user(request),
                                        status=0).select_related("sns_group", "sns_user", "sns_user__device")
    if i_page != 0:
        if i_size == 0:
            i_size = 50

    if keyword:
        query = query.filter(sns_group__group_id__contains=keyword)

    if qq:
        query = query.filter(sns_user__login_name=qq)

    if phone:
        query = query.filter(sns_user__device__label=phone)

    if tag:
        query = query.filter(sns_group_id__in=[x.group_id for x in GroupTag.objects.filter(tag=tag)])

    query = query[(i_page - 1) * i_size:i_page * i_size]

    return [qun_to_json(x) for x in query]


@api_func_anonymous
def team_known_qun(request, i_page, i_size, keyword):
    query = SnsGroup.objects.filter(app_id=get_session_app(request), status__gte=0)
    if i_page != 0:
        if i_size == 0:
            i_size = 50

    if keyword:
        query = query.filter(group_name__contains=keyword)

    query = query[(i_page - 1) * i_size:i_page * i_size]
    total = query.count()
    return {
        'total': total,
        'items': [api_helper.sns_group_to_json(x) for x in query],
    }


@api_func_anonymous
def team_qun(request, i_page, i_size, keyword, owner, qq, phone):
    query = SnsUserGroup.objects.filter(sns_user__owner__app_id=get_session_app(request),
                                        status=0).select_related("sns_group", "sns_user", "sns_user__owner",
                                                                 "sns_user__device")
    if owner:
        query = query.filter(sns_user__owner__name=owner)
    if i_page != 0:
        if i_size == 0:
            i_size = 50

    if keyword:
        query = query.filter(sns_group__group_id__contains=keyword)

    if phone:
        query = query.filter(sns_user__device__label=phone)

    if qq:
        query = query.filter(sns_user__login_name=qq)

    total = query.count()
    distinct = query.values('sns_group_id').distinct().count()
    query = query[(i_page - 1) * i_size:i_page * i_size]

    return {
        'total': total,
        'distinct': distinct,
        'items': [qun_to_json(x, owner=1) for x in query],
    }


@api_func_anonymous
def my_kicked_qun(request, i_page, i_size, keyword):
    query = SnsGroupLost.objects.filter(sns_user__owner__email=get_session_user(request)).order_by(
        "-pk").select_related("group", "sns_user",
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
def my_qun_cnt(request, qq, phone, tag):
    query = SnsUserGroup.objects.filter(sns_user__owner__email=get_session_user(request), status=0)
    if qq:
        query = query.filter(sns_user__login_name=qq)

    if phone:
        query = query.filter(sns_user__device__label=phone)

    if tag:
        query = query.filter(sns_group_id__in=[x.group_id for x in GroupTag.objects.filter(tag=tag)])

    return {
        'total': query.count(),
        'distinct': query.values('sns_group_id').distinct().count()
    }


@api_func_anonymous
def my_apply_log(request, i_size, i_page, keyword):
    user = api_helper.get_login_user(request)
    if i_size == 0:
        i_size = 50

    if i_page == 0:
        i_page = 1

    i_page -= 1

    query = SnsApplyTaskLog.objects.filter(device__owner=user).order_by("-pk")
    if keyword:
        query = query.filter(group_id=keyword)

    total = query.count()

    rows = query.select_related('group', 'device')[i_page * i_size:(i_page + 1) * i_size]

    return {
        'total': total,
        'page': i_page + 1,
        'items': [{
            'id': x.group_id,
            'name': x.group.group_name,
            'member_count': x.group.group_user_count,
            'memo': x.memo,
            'status': x.status,
            'qq': x.account.login_name,
            'device': x.device.friend_text
        } for x in rows],
    }


@api_func_anonymous
def my_pending_remove(ids):
    SnsGroupSplit.objects.filter(pk__in=ids.split(';')).update(status=-1)
    return 'ok'


@api_func_anonymous
def my_pending_purge(email, request):
    user = api_helper.get_login_user(request, email)
    api_helper.remove_dup_split(user)
    return ""


@api_func_anonymous
def my_pending_rearrange(email, request, phone, toPhone):
    user = api_helper.get_login_user(request, email)
    # 重新分配手机phone是的加群
    groups = SnsGroupSplit.objects.filter(phone__label=phone, status__in=(0, 1))
    phones = [x for x in PhoneDevice.objects.filter(owner=user, status=0).exclude(label=phone) if
              x.snsuser_set.filter(friend=1).count() > 0] if not toPhone else [model_manager.get_phone(toPhone)]
    idx = 0
    forward = True
    if len(phones) == 1:
        phone = phones[0]
        for x in groups:
            x.phone = phone
            x.save()
    elif len(phones):
        for x in groups:
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
    else:
        logger.warning('没有可供选择的号')


@api_func_anonymous
def my_pending_qun(email, request, i_size, i_page, keyword, i_export, phone):
    if i_size == 0:
        i_size = 50

    if i_page == 0:
        i_page = 1

    i_page -= 1

    if not email:
        email = get_session_user(request)

    values = (0, 1) if i_export == 0 else (0,)
    query = SnsGroupSplit.objects.filter(user__email=email,
                                         status__in=values).select_related("group")

    if phone:
        query = query.filter(phone__label=phone)

    if i_export == 1:
        resp = HttpResponse(content_type='text/csv')
        resp['Content-Disposition'] = 'attachment; filename="pending.csv"'

        writer = csv.writer(resp)
        for x in query:
            writer.writerow([x.group_id])
        return resp

    if keyword:
        query = query.filter(group__group_id__contains=keyword)

    pending = query[i_page * i_size:(i_page + 1) * i_size]
    group_splits = {x.group_id: x for x in pending}

    def to_data(group):
        ret = api_helper.sns_group_to_json(group)
        ret['apply_status'] = group_splits.get(group.group_id).status
        phone = group_splits.get(group.group_id).phone
        if phone:
            ret['device'] = phone.friend_text  # '%s%s' % (phone.label, '' if not phone.memo else '[%s]' % phone.memo)
        ret['internal_id'] = group_splits.get(group.group_id).id
        return ret

    return {
        'total': len(query),
        'page': i_page + 1,
        'items': [to_data(x.group) for x in pending]
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

            SnsGroupSplit.objects.filter(phone=dev).update(user=user)

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
    elif not phone or not device:
        api_error(1, '没找到电话记录')

    if sns_user.phone != phone:
        old_phone = sns_user.phone
        owner = sns_user.owner
        sns_user.phone = phone
        sns_user.device = device
        sns_user.owner = device.owner

        sns_user.save()

        UserActionLog(action='转绑', memo='%s从%s变成%s' % (qq, old_phone, phone), user=owner).save()

    return 'ok'


@api_func_anonymous
def get_qq_password(qq):
    db = model_manager.get_qq(qq)
    return HttpResponse(db.passwd if db else '')


@api_func_anonymous
def update_qq_provider(qq, provider):
    db = model_manager.get_qq(qq)
    if db:
        db.provider = provider
        db.save()

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
    elif db and dev != db.device:
        pass

    return "ok"


@api_func_anonymous
def qq_drop(request, qq):
    """
    放弃QQ号，将相关群放入资源池
    :param request:
    :param qq:
    :return:
    """
    db = model_manager.get_qq(qq)
    # db.active = 0
    db.status = -1
    db.friend = 0
    db.dist = 0
    db.search = 0
    db.save()

    for group in db.snsusergroup_set.filter(status=0).select_related('sns_group'):
        group.sns_group.status = 0
        group.sns_group.save()

    split_qq(None, request)

    return 'ok'


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
    self = model_manager.get_user(get_session_user(request))
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = PhoneDevice.objects.filter(label=account[0]).first()
            user = User.objects.filter(email=account[2]).first() if len(account) > 2 else self

            label = account[0]
            phone_num = label if len(account) == 1 else account[1]

            if not db:
                device = PhoneDevice(label=label, phone_num=phone_num, status=0)
                if user:
                    device.owner_id = user.id

                device.save()
                total += 1
            else:
                db.phone_num = phone_num
                if user:
                    db.owner_id = user.id

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
def import_qun_stat(ids, device_id, status):
    """
    导入群的统计数据
    这个是完整的，如果之前在的群没了，说明被踢了
    :param ids:
    :return:
    """
    logger.info('import stat of %s', device_id)
    if not status:
        status = 2

    to_save = defaultdict(list)
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = line.split('\t')
            if len(account) == 4 and account[0].isdigit():
                total += 1
                to_save[account[3]].append((account[0], account[1], account[2]))

    device = model_manager.get_phone(device_id)

    for k, accounts in to_save.items():
        sns_user = SnsUser.objects.filter(login_name=k, type=0).first()
        if device and not sns_user:
            logger.info("Sns user %s not found device is %s", k, device_id)
            sns_user = SnsUser(name=k, login_name=k, passwd='_',
                               phone=device.phone_num, device=device,
                               owner=device.owner, app=device.owner.app)
            sns_user.save()

        if sns_user:

            if not device:
                device = sns_user.device

            if sns_user.device != device:
                sns_user.device = device
                sns_user.owner = device.owner
                sns_user.phone = device.label
                sns_user.save()

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
                    qun_user_cnt = 0 if not qun_user_cnt.isdigit() else int(qun_user_cnt)
                    if not qun:
                        qun = SnsGroup(group_id=qun_num, group_name=qun_name, type=0, app_id=sns_user.app_id,
                                       group_user_count=qun_user_cnt, status=2, created_at=timezone.now(),
                                       from_user_id=device.owner_id)
                        qun.save()
                        model_manager.process_tag(qun)
                    else:
                        if qun.status != 2:
                            qun.status = 2

                        qun.group_user_count = qun_user_cnt
                        qun.name = qun_name
                        qun.save()
                        qun.snsgroupsplit_set.filter(phone=device).update(status=3)

                    SnsUserGroup(sns_group=qun, sns_user=sns_user, status=0, active=1).save()
                    SnsApplyTaskLog.objects.filter(account=sns_user, memo='已发送验证', group=qun).update(status=1)
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
                    save_ignore(qun)
                    # qun.save()

                    qun.snsgroupsplit_set.filter(phone=device).update(status=3)

            if status == 2:
                for group in all_groups:
                    lost = 0
                    if group.sns_group_id not in all_group_ids:
                        # 被踢了
                        model_manager.set_qun_kicked(group)
                        lost += 1
                    logger.info("total lost %s", lost)

                    if lost:
                        model_manager.deal_kicked(device.owner)

    SnsGroupSplit.objects.filter(phone=device, status=1).update(status=0)
    SnsGroupSplit.objects.filter(phone=device, status=2, updated_at=timezone.now() - timedelta(days=2)).update(status=0)
    logger.info('Import done total %s', total)


@api_func_anonymous
def import_qun(app, ids, request, email, phone, edit_method, i_ignore_dup):
    """
    群号 群名 群人数 qq号[可选]
    :param app:
    :param ids:
    :param request:
    :return:
    """
    logger.info('Import qun of %s', app)
    if not app:
        app = get_session_app(request)

    if not email:
        email = get_session_user(request)

    login_user = None
    if email:
        login_user = model_manager.get_user(email)

    cnt = 0
    total = 0
    exists = {x.group_id for x in SnsGroup.objects.filter(app_id=app)}

    the_app = model_manager.get_app(app)

    device = model_manager.get_phone(phone) if phone else None

    if "edit" == edit_method and device:
        to_delete = SnsGroupSplit.objects.filter(user=login_user, phone=device)
        if not i_ignore_dup:
            to_delete = to_delete.exclude(group__in=exists)

        to_delete.delete()

    split_to_self = login_user.snsuser_set.filter(app=the_app, friend=1).count() if login_user else 0

    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = line.split('\t')  # re.split('\s+', line) ## 群名称有可能有空格
            try:
                if not account[0].isdigit():
                    continue
                if account[0] in exists:
                    if device and i_ignore_dup == 0:
                        qun = model_manager.get_qun(account[0])
                        if "new" == edit_method:
                            SnsGroupSplit.objects.filter(group=qun, user=login_user, status__in=(0, 1)).delete()

                        SnsGroupSplit(group=qun, user=login_user, phone=device).save()

                    continue

                logger.info('找到了新群 %s' % line)

                db = SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                              group_user_count=account[2], created_at=timezone.now(), from_user=login_user)
                db.save()
                model_manager.process_tag(db)
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
                elif split_to_self and login_user and (
                        device or (the_app and the_app.self_qun == 1)) and login_user.app == the_app:
                    SnsGroupSplit(group=db, user=login_user, phone=device).save()
            except:
                logger.warning("error save %s" % line, exc_info=1)

    logger.info('共%s个新群' % cnt)

    if not device:
        if split_to_self and the_app and the_app.self_qun == 1 and login_user.app == the_app:
            split_qun_to_device(request, email)

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
                              group_user_count=member_cnt, created_at=timezone.now())
                db.save()
                model_manager.process_tag(db)
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
def split_qq_all():
    def func():
        for app in App.objects.all():
            try:
                do_split_app(app.app_id)
            except:
                logger.warn('err', exc_info=1)
                pass

    # thread = threading.Thread(target=func)
    # thread.start()
    pid = os.fork()
    if pid == 0:
        func()
        os._exit(0)


@api_func_anonymous
def split_qq(app, request):
    if not app:
        app = get_session_app(request)
    return do_split_app(app)


def do_split_app(app):
    group_splitter.split_qun(app)
    return 'ok'


@api_func_anonymous
def export_qun_csv(request):
    app = get_session_app(request)
    db = SnsGroup.objects.filter(app_id=app, status__gte=0).order_by("-pk")

    response = HttpResponse('\n'.join(['%s\t%s\t%s' % (x.group_id, x.group_name, x.group_user_count) for x in db]),
                            content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=qun.csv'

    return response


@api_func_anonymous
def export_phone_qun_csv(request):
    app = get_session_app(request)
    db = SnsUserGroup.objects.filter(sns_group__app__app_id=app,
                                     status=0).select_related("sns_group",
                                                              "sns_user", "sns_user__device").order_by("-pk")

    response = HttpResponse('\n'.join(['%s\t%s\t%s\t%s\t%s' % (x.sns_group.group_id,
                                                               x.sns_group.group_name,
                                                               x.sns_group.group_user_count,
                                                               x.sns_user.login_name,
                                                               x.sns_user.device.label if x.sns_user.device else '') for
                                       x in db]),
                            content_type='application/octet-stream')
    response['Content-Disposition'] = 'attachment; filename=qun.csv'

    return response


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
        group_splitter.split_qun_device(email)
    return 'ok'


@api_func_anonymous
def reset_applying():
    model_manager.return_applying_to_normal()
    return ''


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
def apps(request, i_dist, email):
    if i_dist:
        return [{'id': x.app_id, 'name': x.app_name} for x in
                App.objects.filter(stage__in=['分发期', '留守期'])]

    user = model_manager.get_user(email if email else get_session_user(request))
    ret = []
    if not user:
        return []
    if user.role <= 2 or user.role > 10:
        apps = user.userauthapp_set.all()
        if user.app_id:
            ret += [{'id': user.app.app_id, 'name': user.app.app_name}]
        ret += [{'id': x.app.app_id, 'name': x.app.app_name} for x in apps if x.app_id != user.app_id]
    else:
        ret = [{'id': x.app_id, 'name': x.app_name} for x in App.objects.all()]

    return ret  # [{'id': x.app_id, 'name': x.app_name} for x in App.objects.all()]


@api_func_anonymous
def app_summary(app_id, request):
    app = App.objects.filter(app_id=app_id).first()
    if app:
        cnt = SnsGroup.objects.filter(app=app).aggregate(Sum('group_user_count'))
        members = cnt['group_user_count__sum']
        # cnt2 = SnsUserGroup.objects.filter(sns_user__app=app, status=0).aggregate(Sum('sns_group__group_user_count'))
        # members2 = cnt2['sns_group__group_user_count__sum']
        t = sum_app_team(app_id)
        return {
            'name': app.app_name,
            'qun_scan': SnsGroup.objects.filter(app=app).count(),
            'qun_scan_members': members if members else 0,
            'total_user': User.objects.filter(app=app).count(),
            'total_qq': SnsUser.objects.filter(type=0, app=app).count(),
            'total_wx': SnsUser.objects.filter(type=1, app=app).count(),
            'total_device': PhoneDevice.objects.filter(owner__app=app).count(),
            'qun_join': t['count'],
            'qun_join_members': t['sum'],
            'add': t['add'],
            'dist': t['dist'],
            'add_count': t['add_count'],
            'add_sum': t['add_sum'],
            'dist_count': t['dist_count'],
            'dist_sum': t['dist_sum'],
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
        ret['app_id'] = user.app.app_id if user.app else 0
        ret['app_name'] = user.app.app_name if user.app else '没有'
        ret['username'] = user.name
        ret['role'] = user.role
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
        return [{'id': x.id, 'label': x.label, 'memo': x.memo, 'num': x.phone_num,
                 'display': x.friend_text,
                 'online': x.id in online,
                 'status': x.status}
                for x in query]

    email = email if email else get_session_user(request)
    if email:
        online = {x.device_id for x in model_manager.get_online(email)}
        query = PhoneDevice.objects.filter(owner__email=email).select_related('owner')
        if i_active:
            query = query.filter(status=0)
        return [{'id': x.id, 'label': x.label, 'owner': x.owner.name, 'memo': x.memo,
                 'display': x.friend_text,
                 'num': x.phone_num, 'online': x.id in online, 'status': x.status}
                for x in query]


@api_func_anonymous
def team_devices(request):
    app = get_session_app(request)
    online = {x.device_id for x in model_manager.get_team_online(app)}
    query = PhoneDevice.objects.filter(owner__app_id=app).select_related('owner')
    return [{'id': x.id, 'label': x.label, 'owner': x.owner.name, 'memo': x.memo,
             'num': x.phone_num, 'online': x.id in online, 'status': x.status}
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
def update_qun_app(sns_ids, i_app_id):
    sns_users = SnsGroup.objects.filter(group_id__in=re.split(';', sns_ids))
    if sns_users:
        for sns_user in sns_users:
            if sns_user.app_id != i_app_id:
                sns_user.app_id = i_app_id
                sns_user.save(update_fields=['app_id'])

    return "ok"


@api_func_anonymous
def update_qun_attr(sns_ids, name, value):
    if value.isdigit():
        value = int(value)

    sns_users = SnsGroup.objects.filter(group_id__in=re.split(';', sns_ids))
    if sns_users:
        for sns_user in sns_users:
            if getattr(sns_user, name) != value:
                setattr(sns_user, name, value)
                sns_user.save(update_fields=[name])

    return "ok"


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
def task_data(device_task_id):
    data = DeviceTaskData.objects.filter(device_task_id=device_task_id).last()
    if data:
        return data.lines


@api_func_anonymous
def update_task_status(device_task_id, i_status):
    db = SnsTaskDevice.objects.filter(pk=device_task_id).first()
    if db and db.status != i_status:
        db.status = i_status
        db.save()
        model_manager.check_task_status(db.task)


@api_func_anonymous
def create_task(type, params, phone, request, date):
    if not type:
        return 'error'

    labels = re.split(';', phone)
    devices = model_manager.get_phones(labels)
    scheduler_date = timezone.make_aware(datetime.strptime(date, '%Y-%m-%d %H:%M')) if date else None
    if devices:
        task_type = model_manager.get_task_type(type)

        user = model_manager.get_user(get_session_user(request))
        if not user:
            user = devices[0].owner

        task = SnsTask(name=task_type.name, type=task_type,
                       app_id=get_session_app(request), status=0, schedule_at=scheduler_date,
                       data=params, creator=user)
        task.save()

        # if '分发' in task_type.name:
        #     pass

        for device in devices:
            SnsTaskDevice(task=task, device=device, schedule_at=scheduler_date, data=task.data).save()

        return "ok"
    api_error(1001, '不存在的手机')


TASK_STATUS_TEXT = ['等待执行', '执行中', '已完成', '已中断', '已取消', '', '', '', '', '', '暂停中', '等待继续', '取消中']


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
        'creator', 'type').order_by('-pk')[:50] if x and x.creator and x.type]


@api_func_anonymous
def team_users(request):
    return [{
        'id': x.id,
        'email': x.email,
        'name': x.name,
    } for x in User.objects.filter(app_id=get_session_app(request), status=0)]


@api_func_anonymous
def team_dist_info(item_id):
    db = DistArticle.objects.filter(item_id=item_id).first()
    ret = list()
    if db:
        tasks = db.snstask_set.all()
        for ts in tasks:
            devices = ts.snstaskdevice_set.all()
            for device in devices:
                if ts.type_id == 3:
                    cnt = device.disttasklog_set.filter(success=1).count()
                    sum = device.disttasklog_set.filter(success=1).aggregate(Sum('group__group_user_count')).get(
                        'group__group_user_count__sum', 0) if cnt else 0
                    obj = {'owner': ts.creator.name, 'qun': cnt, 'type': 'QQ', 'user': sum,
                           'phone': device.device.friend_text, 'time': times.to_str(device.started_at)}
                    ret.append(obj)
                else:
                    obj = {'owner': ts.creator.name, 'qun': 0, 'type': '微信', 'user': 0,
                           'phone': device.device.friend_text, 'time': times.to_str(device.started_at)}
                    ret.append(obj)

    return ret


@api_func_anonymous
def team_tasks(request):
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
    } for x in SnsTask.objects.filter(creator__app_id=get_session_app(request)).select_related(
        'creator', 'type').order_by('-pk')[:50]]


@api_func_anonymous
def task_devices(task_id):
    return [{
        'device': x.device.friend_text,
        # '%s%s' % (x.device.label, '' if not x.device.memo else '(%s)' % x.device.memo),
        'create_time': times.to_str(x.created_at),
        'finish_time': times.to_str(x.finish_at),
        'status': x.status,
        'id': x.id,
        'status_text': TASK_STATUS_TEXT[x.status],
    } for x in SnsTaskDevice.objects.filter(task_id=task_id).select_related('device')]


@api_func_anonymous
def device_articles(device):
    return [{
        'title': x.task.article.title if x.task.article else '',
        'url': x.data.split('\n')[0],
        'type': 'QQ' if x.task.type_id == 3 else '微信',
        'time': times.to_str(x.started_at),
    } for x in SnsTaskDevice.objects.filter(device_id=device, task__article__isnull=False,
                                            task__type_id__in=(3, 5)).select_related("task", "task__article").order_by(
        "-pk")[0:20]]


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
def file_content(i_file_id, i_att, i_result_id):
    if i_result_id:
        return HttpResponse(api_helper.get_result_content(i_result_id))
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


@api_func_anonymous
def temp_func(request):
    date = datetime(year=2017, month=9, day=1)
    day1 = timedelta(days=1)
    while date < datetime.today() - day1:
        # daemons.daily_stat(date.strftime('%Y-%m-%d'))
        date = date + day1


@api_func_anonymous
def re_import(i_file_id):
    file = DeviceFile.objects.filter(id=i_file_id).first()
    if file:
        text = _get_content(file.qiniu_key)
        file_name = '/tmp/tmp_%s.qn' % i_file_id
        with open(file_name, 'wt', encoding='utf-8') as out:
            out.write(text)

        _after_upload(file.device_task, file.device_task.id, file_name, file.device, file.type)

    return ''


@api_func_anonymous
def report_result(id, task_id, line):
    response = HttpResponse('')
    if not id or not task_id:
        return response
    device_task = SnsTaskDevice.objects.filter(device__label=id, task_id=task_id).first()
    if device_task:
        api_helper.deal_result_line(device_task, line)

    return response


@api_func_anonymous
def report_progress(id, q, task_id, p, i_status, i_r, nickname):
    response = HttpResponse('')
    if not id or not q or not task_id:
        return response
    device_task = SnsTaskDevice.objects.filter(device__label=id, task_id=task_id).first()

    qq = model_manager.get_qq(q)

    if qq and nickname and qq.name != nickname:
        qq.name = nickname
        try:
            qq.save(update_fields=['name'])
        except:
            pass

    if device_task:
        if device_task.status == 0:
            model_manager.mark_task_started(device_task)

        if p.isdigit() and device_task.progress != int(p) and p != '0' and q != '0':
            device_task.progress = int(p)
            device_task.save()
            twl = TaskWorkingLog.objects.filter(device_task=device_task, account__login_name=q).first()
            if not twl:
                twl = TaskWorkingLog(device_task=device_task, account=qq)

            try:
                twl.progress = device_task.progress
                twl.save()
            except:
                pass

        if i_status == 1:
            if device_task.status != 3:
                model_manager.mark_task_cancel(device_task, notify=False)
                api_helper.webhook(device_task, '任务出现异常，本机下线，请检查日志', force=True)

        ad = model_manager.get_active_device(device_task.device)
        if not ad:
            ad = ActiveDevice(device=device_task.device, status=1, active_at=timezone.now())
        else:
            ad.active_at = timezone.now()
            ad.status = 1
        ad.save()

        if device_task.status == 10:
            response = HttpResponse('command=暂停')
        elif device_task.status == 11:
            response = HttpResponse('command=继续')
        elif device_task.status == 12 or device_task.status == 3:
            response = HttpResponse('command=停止')

        if device_task.status == 11 and p != '0' and i_r == 1:
            if device_task.status != 1:
                device_task.status = 1
                device_task.save()
        elif device_task.status < 10 and i_r == 2:
            if device_task.status != 10:
                device_task.status = 10
                device_task.save()
        elif device_task.status == 12 and i_r == 3:
            model_manager.mark_task_cancel(device_task)

    return response


@api_func_anonymous
def change_js_version(ver):
    if ver and len(ver) == len('6f88563ddfbfa6fbca5e'):
        settings.JS_VER = ver
    return "ok"


@api_func_anonymous
def save_perm(ids, email):
    user = model_manager.get_user(email)
    user.userauthapp_set.all().delete()
    for x in ids.split(';'):
        if x:
            UserAuthApp(user=user, app_id=x).save()


@api_func_anonymous
def tag_names():
    return caches.get_tag_names()


@api_func_anonymous
def get_share_items(date, email, request):
    if not email:
        email = get_session_user(request)

    the_user = model_manager.get_user(email)
    date = timezone.make_aware(datetime.strptime(date[0:10], '%Y-%m-%d')) if date else timezone.now()
    date = date.replace(microsecond=0, second=0, hour=0, minute=0)
    return stats.get_user_share_stat(date, the_user)


@api_func_anonymous
def user_majia(request, filter):
    return {
        'items': [{
            'id': x.cutt_user_id,
            'name': x.name,
            'type': '微信' if x.type == 1 else 'QQ'
        } for x in (AppUser.objects.filter(user__email=get_session_user(request), type__in=(0, 1))
        if not filter else AppUser.objects.filter(type=filter,
                                                  user__email=get_session_user(request)))]
    }


@api_func_anonymous
def add_user_majia(i_cutt_id, i_type, request):
    if not i_cutt_id:
        return 'none'
    user = api_helper.get_login_user(request)
    zhiyue_user = model_manager.query(ZhiyueUser).filter(userId=i_cutt_id).first()

    if not zhiyue_user:
        api_error(101, '用户不存在')

    AppUser(cutt_user_id=i_cutt_id, type=i_type, user=user, name=zhiyue_user.name).save()

    return 'ok'


@api_func_anonymous
def sum_team_qun(request):
    app = get_session_app(request)

    return sum_app_team(app)


def sum_app_team(app):
    query = SnsGroup.objects.filter(app_id=app) \
        .extra(where=['exists (select 1 from backend_snsusergroup '
                      'where status=0 and sns_group_id=backend_snsgroup.group_id)'])

    query_add = SnsGroup.objects.filter(app_id=app) \
        .extra(where=['exists (select 1 from backend_snsusergroup g, backend_snsuser u '
                      'where g.sns_user_id=u.id and u.app_id=%s and u.friend=1 and u.dist=0 and '
                      'g.status=0 and sns_group_id=backend_snsgroup.group_id)' % app])

    query_dist = SnsGroup.objects.filter(app_id=app) \
        .extra(where=['exists (select 1 from backend_snsusergroup g, backend_snsuser u '
                      'where g.sns_user_id=u.id and u.app_id=%s and u.dist=1 and '
                      'g.status=0 and sns_group_id=backend_snsgroup.group_id)' % app])
    return {
        'add': SnsUser.objects.filter(app_id=app, friend=1).count(),
        'dist': SnsUser.objects.filter(app_id=app, dist=1).count(),
        'sum': query.aggregate(Sum('group_user_count'))['group_user_count__sum'],
        'total': SnsUserGroup.objects.filter(sns_user__app_id=app, status=0).count(),
        'count': query.count(),
        'add_count': query_add.count(),
        'add_sum': query_add.aggregate(Sum('group_user_count'))['group_user_count__sum'],
        'dist_sum': query_dist.aggregate(Sum('group_user_count'))['group_user_count__sum'],
        'dist_count': query_dist.count(),
        'users': [
            sum_app_user(app, x.id, lambda y: y.update({'name': x.name})) for x in
            User.objects.filter(app_id=app, status=0)
        ]
    }


def sum_app_user(app, user_id, callback=None):
    query = SnsGroup.objects.filter(app_id=app) \
        .extra(where=['exists (select 1 from backend_snsusergroup, backend_snsuser '
                      'where backend_snsusergroup.status=0 and '
                      'sns_user_id=backend_snsuser.id and backend_snsuser.owner_id=%s '
                      'and sns_group_id=backend_snsgroup.group_id)' % user_id])
    ret = {
        'sum': query.aggregate(Sum('group_user_count'))['group_user_count__sum'],
        'total': SnsUserGroup.objects.filter(sns_user__app_id=app, sns_user__owner_id=user_id, status=0).count(),
        'count': query.count(),
    }
    if callback:
        callback(ret)
    return ret


@api_func_anonymous
def set_article_attr(article_id, key, value):
    db = DistArticle.objects.filter(pk=article_id).first()
    setattr(db, key, value)
    db.save()


def redirect(request):
    item_id = request.GET.get('id')
    app_id = api_helper.get_session_app(request)
    db = DistArticle.objects.filter(pk=item_id).first()
    item = model_manager.query(ClipItem).filter(itemId=item_id).first()

    if not item:
        return HttpResponse("error", status_code=404)
    if db:
        app_id = db.app_id
    else:
        app_id = item.fromEntity

    return HttpResponseRedirect(
        'http://www.cutt.com/weizhan/article/%s/%s/%s' % (item.clipId, item_id, app_id))


@api_func_anonymous
def task_groups(task_id, i_page):
    db = SnsTaskDevice.objects.filter(id=task_id).first()
    items = []
    total = 0
    if db:
        task = db.task
        if task.type_id == 3:
            if i_page <= 0:
                i_page = 1

            offset = (i_page - 1) * 50
            query = DistTaskLog.objects.filter(task=db, success=1).select_related("group")
            items = [{
                'name': x.group.group_name,
                'num': x.group.group_id,
                'count': x.group.group_user_count
            } for x in
                query[offset:offset + 50]]
            total = query.count()

        elif task.type_id == 5:
            if i_page <= 0:
                i_page = 1

            query = WxDistLog.objects.filter(task=db)

            offset = (i_page - 1) * 50
            items = [{
                'name': x.group_name,
                'num': '(N/A)',
                'count': x.user_count
            } for x in
                query[offset:offset + 50]]
            total = query.count()

    return {
        'total': total,
        'items': items
    }
