from django_rq import job
from .loggs import logger

from backend import model_manager
from backend.models import User, SnsGroup, SnsGroupSplit, PhoneDevice


@job("default", timeout=3600)
def split_qun(app):
    #     _executors.submit(_split_qun, app)
    #
    #
    # def _split_qun(app):
    logger.info('Split qun of %s' % app)
    users = get_split_to(app)

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
                    logger.info('%s ignore' % x)
            except:
                pass

            continue

        if x.snsgroupsplit_set.filter(status__in=(0, 1, 2)).count():
            try:
                if x.status != 1:
                    x.status = 1
                    x.save(update_fields=['status'])
                    logger.info('%s has been splitted, set status = 1' % x)
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

        if x.snsusergroup_set.filter(status=0).count() == 0:
            # 不重复分群
            logger.info("split %s(%s) to %s at %s" % (x.group_name, x.group_id, user.name, app))
            SnsGroupSplit(group=x, user=user, app_id=app).save()
            try:
                x.save(update_fields=['status'])
                logger.info('%s split to %s', x, user)
            except:
                pass
        else:
            x.status = 2
            model_manager.save_ignore(x)
    for u in users:
        split_qun_device(u.email)


def get_split_to(app):
    users = [x for x in User.objects.filter(app_id=app, status=0) if x.phonedevice_set.filter(status=0).count() > 0]
    return users


def split_qun_device(email):
    phones = [x for x in PhoneDevice.objects.filter(owner__email=email, status=0) if
              x.snsuser_set.filter(friend=1).count() > 0]
    total_phones = len(phones)
    if total_phones == 0:
        return

    idx = 0
    forward = True
    for x in SnsGroupSplit.objects.filter(user__email=email, phone__isnull=True):
        phone = phones[idx]
        idx += 1 if forward else -1

        if idx <= -1:
            idx = 0
            forward = not forward
        elif idx >= total_phones:
            idx = total_phones - 1
            forward = not forward

        try:
            x.phone = phone
            x.save()
            logger.info('%s has been splitted split to %s' % (x, phone))
        except:
            pass


@job
def re_split(email):
    SnsGroupSplit.objects.filter(user__email=email).update(phone=None)
    split_qun_device(email)


@job("default", timeout=600)
def re_split_app(app):
    for user in User.objects.filter(app_id=app, status=0):
        re_split(user.email)


@job
def merge_split():
    groups = SnsGroup.objects.filter(status__in=(0, 1))
    for group in groups:
        merge_split_group(group)


def reset_split(app):
    for x in SnsGroupSplit.objects.filter(app_id=app, status=0):
        group = x.group
        if group.status == 1:
            group.status = 0
            group.save()
        x.delete()


def merge_join():
    groups = SnsGroup.objects.filter(status=2)
    for group in groups:
        merge_split_group(group)


def merge_split_group(group):
    splitters = group.snsgroupsplit_set.filter(status__in=(0, 1, 2))
    if len(splitters) > 0:
        joined = group.snsusergroup_set.filter(status=0)

        if joined:
            if group.status != 2:
                group.status = 2
                model_manager.save_ignore(group, fields=['status'])

            splitters.delete()
            return

        if group.status == 0:
            group.status = 1
            model_manager.save_ignore(group, fields=['status'])

        has_done = False
        total = len(splitters)
        for idx, splitter in enumerate(splitters):
            if has_done or total != idx + 1:
                logger.info("Remove dup %s" % splitter)
                splitter.delete()
            else:
                has_done = True
