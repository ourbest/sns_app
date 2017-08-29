import logging
import re
from collections import defaultdict

from dj.utils import api_func_anonymous, api_error

from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice, SnsUser, SnsUserGroup, SnsGroupLost

logger = logging.getLogger(__name__)

DEFAULT_APP = 1519662


@api_func_anonymous
def upload(type, id, task_id):
    return "ok"


@api_func_anonymous
def task(id):
    print(id)
    return {
        'name': 'test.txt',
        'content': 'this is a test'
    }


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
            device = PhoneDevice.objects.filter(phone_num=account[4])
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
def my_qun(request):
    return [{
        'id': x.sns_group.id,
        'name': x.sns_group.group_name,
        'qq': {
            x.sns_user.login_name,
            x.sns_user.name
        },
        'device': {
            'label': x.sns_user.device.label,
            'phone': x.sns_user.device.phone_num
        },
        'member_count': x.sns_group.group_user_count
    } for x in
        SnsUserGroup.objects.filter(sns_user__owner__email=_get_session_user(request), active=1,
                                    status=0).select_related("sns_group", "sns_user", "sns_user__device")]


@api_func_anonymous
def my_lost_qun(request):
    return [{
        'id': x.sns_group.id,
        'name': x.sns_group.group_name,
        'qq': {
            x.sns_user.login_name,
            x.sns_user.name
        },
        'device': {
            'label': x.sns_user.device.label,
            'phone': x.sns_user.device.phone_num
        },
        'member_count': x.sns_group.group_user_count
    } for x in
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
            if len(account) == 4:
                total += 1
                to_save[account[3]].append((account[0], account[1], account[2]))

    for k, accounts in to_save.items():
        sns_user = SnsUser.objects.filter(login_name=k, type=0).first()
        if sns_user:
            all_groups = sns_user.snsusergroup_set.all()
            all_group_ids = set()
            for (qun_num, qun_name, qun_user_cnt) in accounts:
                all_group_ids.add(qun_num)
                found = None
                for group in all_groups:
                    if qun_num == group.group_id:
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
                if group.group_id not in all_group_ids:
                    # 被踢了
                    SnsGroupLost(group_id=group.group_id, sns_user=sns_user).save()
                    # SnsGroupSplit.objects.filter(group_id=group.group_id, status__gte=0).update(status=-1)
                    SnsGroupSplit.objects.filter(group_id=group.group_id).delete()
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
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            total += 1
            account = re.split('\s+', line)
            try:
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
    users = User.objects.filter(app_id=app)
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
def login(request, email, password):
    user = User.objects.filter(email=email).first()
    if user and password == user.passwd:
        request.session['user'] = email
        logger.info("User %s login." % user)
        return "ok"

    api_error(1001)


@api_func_anonymous
def login_info(request):
    return _get_session_user(request)


@api_func_anonymous
def logout(request):
    del request.session['user']
    return "ok"


@api_func_anonymous
def users(request):
    app = _get_session_app(request)
    return [{'id': x.id, 'email': x.email, 'name': x.name} for x in User.objects.filter(app_id=app)]


@api_func_anonymous
def devices(request):
    email = _get_session_user(request)
    if email:
        return [{'id': x.id, 'label': x.label, 'num': x.phone_num}
                for x in PhoneDevice.objects.filter(owner__email=email)]


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
