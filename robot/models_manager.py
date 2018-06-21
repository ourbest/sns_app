from random import choice
import re

from django.db.models import Count

from backend.models import PhoneDevice, SnsUser
from robot.models import Config, Plan, Task, Keyword, EventLog
from robot.utils import today_zero, logger


def get_config(user):
    return Config.objects.get_or_create(user=user)[0]


def get_managed_devices_by_user(user):
    return PhoneDevice.objects.filter(owner=user, in_trusteeship=True)


def get_managed_device_by_label(label):
    return PhoneDevice.objects.select_related('owner').filter(label=label, in_trusteeship=True).first()


def get_device_by_id(device_id):
    return PhoneDevice.objects.filter(id=device_id).first()


def get_plans(device):
    return Plan.objects.select_related('type', 'sns_user').filter(device=device).order_by('start_time').all()


def delete_plans_by_user(user):
    return Plan.objects.filter(device__owner=user).delete()


def delete_plans_by_device(device):
    return Plan.objects.filter(device=device).delete()


def get_tasks_at_today(device):
    return Task.objects.select_related('type', 'sns_user').filter(
        device=device, start_time__gte=today_zero()).order_by('start_time').all()


def get_task(pk):
    return Task.objects.filter(pk=pk).first()


def get_unfinished_task(device) -> Task:
    return Task.objects.filter(device=device, status=0).order_by('start_time').first()


def plan_change_to_task(plan: Plan) -> Task:
    plan.delete()
    return Task.objects.create(device=plan.device, type=plan.type, sns_user=plan.sns_user)


def get_keyword(app_name):
    ret = re.match(r'(.+)生活圈$', app_name)
    if ret:
        place_name = ret.group(1)
    else:
        ret = re.match(r'(.+)圈$', app_name)
        if ret:
            place_name = ret.group(1)
        else:
            return

    keywords = [x.keyword for x in Keyword.objects.all()]
    if keywords:
        return choice([
            *[x + place_name for x in keywords],
            *[place_name + x for x in keywords],
            place_name,
        ])


def get_applicable_qqs(device):
    return SnsUser.objects.filter(device_id=device, friend=1, status=0).all()


def get_applicable_qq(device_id):
    applied = EventLog.objects.filter(sns_user__device_id=device_id, sns_user__friend=1, sns_user__status=0,
                                      created_time__gte=today_zero(), type_id=2).values('sns_user').annotate(
        applied_num=Count('sns_user'))
    if applied:
        sns_user_id = min(applied, key=lambda obj: obj['applied_num'])['sns_user']
        return SnsUser.objects.filter(pk=sns_user_id).first()

    return SnsUser.objects.filter(device_id=device_id, friend=1, status=0).order_by('?').first()


def get_applied_num_at_today(sns_users):
    return EventLog.objects.filter(sns_user__in=sns_users, created_time__gte=today_zero(),
                                   type_id=2).aggregate(Count('pk'))['pk__count']


def get_searched_num_at_today(device):
    return EventLog.objects.filter(device=device, created_time__gte=today_zero(),
                                   type_id=1).aggregate(Count('pk'))['pk__count']


def get_counted_num_at_today(device):
    return EventLog.objects.filter(device=device, created_time__gte=today_zero(),
                                   type_id=4).aggregate(Count('pk'))['pk__count']


def get_last_apply_time(device):
    query = EventLog.objects.filter(device=device, type_id=2).order_by('-created_time').first()
    if query:
        return query.created_time


def record_event(device_id, type_id, task_id=None, sns_user_id=None, group_id=None):
    logger.debug('事件已记录<task_id=%s, type_id=%s, device_id=%s, sns_user_id=%s, group_id=%s>' %
                 (task_id, type_id, device_id, sns_user_id, group_id))
    return EventLog.objects.create(task_id=task_id, type_id=type_id, device_id=device_id, sns_user_id=sns_user_id,
                                   group_id=group_id)
