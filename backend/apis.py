import logging
import re

from dj.utils import api_func_anonymous, api_error

from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice, SnsUser

logger = logging.getLogger(__name__)

DEFAULT_APP = 1519662


@api_func_anonymous
def upload(ftype, fid):
    uploaded_file = None
    print(ftype, fid)


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
def import_user(request, ids):
    """
    email name app
    :return:
    """
    total = 0
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            db = User.objects.filter(email=account[0]).first()
            if not db:
                app = account[2] if len(account) > 2 else _get_session_app(request)
                User(email=account[0], name=account[1], status=0, passwd='testpwd', app_id=app).save()
                total += 1
            else:
                db.name = account[1]
                if len(account) > 2:
                    db.app_id = account[2]
                db.save()

    return {
        'total': total,
        'message': '成功'
    }


@api_func_anonymous
def import_sns():
    pass


@api_func_anonymous
def import_qun(app, ids, request):
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
                    SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                             group_user_count=account[2]).save()
                    cnt += 1
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
def export_qun(request, email, filter):
    user = email if email else _get_session_user(request)
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
def login(request, email):
    user = User.objects.filter(email=email).first()
    if user:
        request.session['user'] = email
        logger.info("User %s login." % user)
        return "ok"

    api_error(1001)


@api_func_anonymous
def logout(request):
    del request.session['user']


@api_func_anonymous
def users(request):
    app = _get_session_app(request)
    return [{x.email, x.name} for x in User.objects.filter(app_id=app)]


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
