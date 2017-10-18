import random
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone
from logzero import logger

from backend import caches
from backend.models import PhoneDevice, SnsTaskType, App, User, ActiveDevice, SnsUser, SnsGroup, UserAuthApp, \
    MenuItemPerm, SnsGroupLost, Tag, GroupTag
from backend.models import SnsUserGroup, SnsGroupSplit


def get_phone(label):
    return PhoneDevice.objects.filter(label=label).first()


def get_phones(labels):
    return PhoneDevice.objects.filter(label__in=labels)


def get_task_type(type):
    return SnsTaskType.objects.filter(id=type).first()


def get_app(app_id):
    return App.objects.filter(app_id=app_id).first()


def get_user(email):
    return User.objects.filter(email=email).first()


def get_online(email):
    return ActiveDevice.objects.filter(device__owner__email=email).filter(
        Q(active_at__gt=(timezone.now() - timedelta(seconds=300))) | Q(status=1))


def get_team_online(app):
    return ActiveDevice.objects.filter(device__owner__app_id=app).filter(
        Q(active_at__gt=(timezone.now() - timedelta(seconds=300))) | Q(status=1))


def get_online_by_id(uid):
    return ActiveDevice.objects.filter(device__owner_id=uid).filter(
        Q(active_at__gt=(timezone.now() - timedelta(seconds=300))) | Q(status=1))


def get_qq(qq_id):
    return SnsUser.objects.filter(login_name=qq_id, type=0).first()


def get_qun(qun_num, type=0):
    return SnsGroup.objects.filter(group_id=qun_num, type=type).first()


def get_active_device(device):
    return ActiveDevice.objects.filter(device=device).first()


def mark_task_finish(device_task):
    _set_task_status(device_task, 2)

    from backend import api_helper
    api_helper.webhook(device_task, '执行完毕, 共耗时%s秒' %
                       (device_task.finish_at - device_task.started_at).total_seconds())


def mark_task_cancel(device_task):
    _set_task_status(device_task, 3)
    from backend import api_helper
    api_helper.webhook(device_task, '已放弃, 共耗时%s秒' %
                       (device_task.finish_at - device_task.started_at).total_seconds(), force=True)


def _set_task_status(device_task, status):
    device_task.status = status
    device_task.finish_at = timezone.now()
    device_task.save()
    device_task.device.status = 0
    device_task.device.save()
    check_task_status(device_task.task)


def check_task_status(task):
    in_prog = False
    for x in task.snstaskdevice_set.all():
        if x.status <= 1:
            in_prog = True
            break
    if not in_prog:
        task.status = 2
        task.finish_at = timezone.now()
        task.save()
        from backend import api_helper
        api_helper.webhook_task(task, '执行完毕, 共耗时%s秒' % (
            task.finish_at - task.started_at).total_seconds() if task.started_at else 'N/A')
    elif task.status == 2:
        task.status = 0
        task.save()


def set_qun_useless(db):
    db.status = -2
    db.save()
    # db = SnsGroup()
    # 删除无效群的数据
    db.snsgroupsplit_set.all().delete()


def set_qun_join(qq_id, qun):
    qq = get_qq(qq_id)
    if qun.status != 2:
        qun.status = 2
        qun.save()

    try:
        qun.snsgroupsplit_set.filter(user=qq.owner).update(status=3)
        sug = SnsUserGroup(sns_group=qun, sns_user=qq, status=0, active=1)
        sug.save()
    except:
        pass

    return sug


def reset_qun_status(device_task):
    """
    将未处理的群重置成未发送
    :param device_task:
    :return:
    """
    SnsGroupSplit.objects.filter(phone=device_task.device, status=1).update(status=0)


def set_qun_applying(device, qun):
    """
    将群状态改写成申请中
    :param device:
    :param qun:
    :return:
    """
    SnsGroupSplit.objects.filter(phone=device, group=qun).update(status=2)


def set_qun_manual(qun):
    """
    需要输入问题
    :param qun:
    :return:
    """
    qun.status = -1
    qun.save()
    # db = SnsGroup()
    # 删除无效群的数据
    qun.snsgroupsplit_set.update(status=-1)


def mark_qun_cancel():
    SnsGroupSplit.objects.filter(status=0, group__group_user_count__range=[1, 10]).update(status=-1)


def get_qun_idle(user, size, device):
    ret = SnsGroupSplit.objects.filter(phone=device, status=0).order_by("-group__group_user_count")[:size]
    ids = [x.pk for x in ret]

    SnsGroupSplit.objects.filter(pk__in=ids).update(status=1)
    return ret


def get_or_create_qq(device, qq):
    db = SnsUser.objects.filter(login_name=qq).first()
    if not db:
        db = SnsUser(login_name=qq, name=qq, phone=device.phone, device=device,
                     owner=device.owner, app_id=device.owner.app_id)
        db.save()
    return db


def set_qun_kicked(sns_user_group):
    """
    被踢
    :param sns_user_group:
    :return:
    """
    logger.info('群%s被踢了', sns_user_group.sns_group_id)
    SnsGroupLost(group_id=sns_user_group.sns_group_id, sns_user=sns_user_group.sns_user).save()
    # SnsGroupSplit.objects.filter(group_id=group.group_id, status__gte=0).update(status=-1)
    SnsGroupSplit.objects.filter(group_id=sns_user_group.sns_group_id).delete()
    sns_user_group.status = -1
    sns_user_group.active = 0
    sns_user_group.save()


def deal_kicked(owner):
    """
    被踢了的群重新分配账号去加
    :return:
    """
    devices = list(PhoneDevice.objects.filter(owner=owner, status=0))
    q = SnsGroupLost.objects.filter(status=0, sns_user__owner=owner).select_related('sns_user')
    all = {x.group_id for x in SnsGroupSplit.objects.filter(user=owner, status=0)}
    for x in q:
        if x.group_id in all:
            continue

        device = random.choice(devices)
        if len(devices) > 1:
            while device.pk == x.sns_user.device_id:
                device = random.choice(devices)

        if x.group.group_user_count >= 10 or x.group.group_user_count == 0:
            try:
                SnsGroupSplit(group_id=x.group_id, user_id=device.owner_id, phone=device).save()
            except:
                pass

    q.update(status=1)


def get_or_create_qun(device, qun_num):
    db = SnsGroup.objects.filter(group_id=qun_num).first()
    if not db:
        db = SnsGroup(group_id=qun_num, group_name=qun_num, type=0, app_id=device.owner.app_id,
                      group_user_count=0, status=1, created_at=timezone.now(), from_user_id=device.owner_id)
        db.save()
        process_tag(db)
    return db


def mark_qun_useless(group):
    group.status = -2
    group.save()
    # db = SnsGroup()
    # 删除无效群的数据
    group.snsgroupsplit_set.all().delete()


def add_user_auth(user, app_id):
    if not UserAuthApp.objects.filter(app_id=app_id, user=user).first():
        UserAuthApp(user=user, app_id=app_id).save()


def get_user_menu(user):
    ret = defaultdict(list)

    for item in MenuItemPerm.objects.filter(role__lte=user.role).order_by('menu__show_order').select_related('menu'):
        items = ret[item.menu.menu_category]
        menu = item.menu
        items.append({
            'title': menu.menu_name,
            'name': menu.menu_route,
            'icon': menu.menu_icon,
            'group': menu.menu_category,
        })

    return ret


def process_tag(qun):
    tags = caches.get_tag_names()
    old = {x.tag for x in qun.grouptag_set.all()}
    for tag in tags:
        if tag not in old and tag in qun.group_name:
            GroupTag(tag=tag, group=qun).save()
            old.add(tag)


def create_new_tag(name):
    if name not in caches.get_tag_names():
        Tag(name).save()
        caches.reload_cache(Tag)
    for g in SnsGroup.objects.all():
        if name in g.group_name:
            GroupTag(tag=name, group=g).save()


def query(clz):
    return clz.objects.using(clz.db_name())


def mark_task_started(device_task):
    if device_task.task.status == 0:
        device_task.task.status = 1
        device_task.task.started_at = timezone.now()
        device_task.task.save()
        from backend import api_helper
        api_helper.webhook_task(device_task.task, '开始执行')

    device_task.status = 1
    device_task.started_at = timezone.now()
    device_task.save()
