from concurrent.futures import ProcessPoolExecutor

from django_rq import job
from logzero import logger

from backend.models import User, SnsGroup, SnsGroupSplit, PhoneDevice

_executors = ProcessPoolExecutor(max_workers=1)


@job
def split_qun(app):
    #     _executors.submit(_split_qun, app)
    #
    #
    # def _split_qun(app):
    logger.info('Split qun of %s' % app)
    users = [x for x in User.objects.filter(app_id=app, status=0) if x.phonedevice_set.filter(status=0).count() > 0]

    if len(users) == 0:
        return 'ok'

    idx = 0
    forward = True
    for x in SnsGroup.objects.filter(app_id=app, status=0).order_by("-group_user_count"):
        if 0 < x.group_user_count <= 10:
            try:
                if x.status != -1:
                    x.status = -1
                    x.save(update_fields=['status'])
            except:
                pass

            continue

        if x.snsgroupsplit_set.filter(status__in=(0, 1, 2)).count():
            try:
                if x.status != 1:
                    x.status = 1
                    x.save(update_fields=['status'])
            except:
                pass

            continue

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
        try:
            x.save(update_fields=['status'])
        except:
            pass
    for u in users:
        split_qun_device(u.email)


def split_qun_device(email):
    phones = [x for x in PhoneDevice.objects.filter(owner__email=email, status=0) if
              x.snsuser_set.filter(friend=1).count() > 0]
    idx = 0
    forward = True
    for x in SnsGroupSplit.objects.filter(user__email=email, phone__isnull=True):
        phone = phones[idx]
        idx += 1 if forward else -1

        if idx == -1:
            idx = 0
            forward = not forward
        elif idx == len(phones):
            idx = idx - 1
            forward = not forward

        try:
            x.phone = phone
            x.save()
        except:
            pass


@job
def merge_split():
    groups = SnsGroup.objects.filter(status__in=(0, 1))
    for group in groups:
        merge_split_group(group)


def merge_split_group(group):
    splitters = group.snsusergroup_set.filter(status__in=(0, 1, 2))
    if len(splitters) > 0:
        if group.status == 0:
            group.status = 1
            group.save()

        has_done = False
        total = len(splitters)
        for idx, splitter in enumerate(splitters):
            if splitter.status == 0:
                if has_done or total != idx + 1:
                    logger.info("Remove dup %s" % splitter)
                    splitter.delete()
                else:
                    has_done = True
            else:
                has_done = True
