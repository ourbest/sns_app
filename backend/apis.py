import logging
import re

from dj.utils import api_func_anonymous, api_error

from backend.models import User, App, SnsGroup, SnsGroupSplit, PhoneDevice

logger = logging.getLogger(__name__)


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
def import_qq():
    pass


@api_func_anonymous
def import_qun(app, ids):
    for line in ids.split('\n'):
        line = line.strip()
        if line:
            account = re.split('\s+', line)
            try:
                db = SnsGroup.objects.filter(group_id=account[0]).first()
                if not db:
                    SnsGroup(group_id=account[0], group_name=account[1], type=0, app_id=app,
                             group_user_count=account[2]).save()
            except:
                logger.warning("error save %s" % account)


@api_func_anonymous
def split_qq(app):
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
    user = email if email else request.session['user']
    app = '1564395'
    if user:
        db = User.objects.filter(email=email).first()
        if db:
            app = db.app_id

    if filter == '所有':
        db = SnsGroup.objects.filter(app_id=app)
        return ['%s %s %s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]
    elif filter == '未分配':
        db = SnsGroup.objects.filter(app_id=app, status=0)
        return ['%s %s %s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]
    elif user:
        db = SnsGroupSplit.objects.filter(user__email=user).select_related("group")
        if filter == '未指定手机':
            db = db.filter(phone__isnull=True)
            # db = db.filter(status=0)
        # if not full and len(db):
        #     SnsGroupSplit.objects.filter(user__email=user, status=0).update(status=1)
        return ['%s %s %s' % (x.group_id, x.group.group_name, x.group.group_user_count) for x in db]


@api_func_anonymous
def split_qun_to_device(request, email):
    user = email if email else request.session['user']
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


def _after_upload_file(ftype, fid, local_file):
    pass
