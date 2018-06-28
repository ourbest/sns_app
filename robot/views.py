import datetime

from dj.utils import api_func_anonymous
from django.http import HttpResponse
from django.shortcuts import redirect

from backend.api_helper import get_session_user
from backend import model_manager
from robot import models_manager
from robot.robot import Robot, PlanManager, TaskManager
from robot.utils import tz, logger


def login_check(func):
    def wrapper(*args, **kwargs):
        user = model_manager.get_user(get_session_user(args[0]))
        if not user:
            return redirect('/')
        return func(*args, **kwargs)

    return wrapper


def get_task(request):
    label = request.GET.get('id')
    device = models_manager.get_managed_device_by_label(label)
    if device:
        task = Robot(device).get_task()
        return HttpResponse(task)
    return HttpResponse(None)


def handle_task_result(request):
    pk = request.POST.get('task_id')
    task = models_manager.get_task(pk)
    if task:
        result = request.POST.get('result')
        TaskManager(task).handle_result(result)
    return HttpResponse('ok')


def handle_task_status(request):
    pk = request.GET.get('task_id')
    task = models_manager.get_task(pk)
    if task:
        status = request.GET.get('status')
        error_msg = request.GET.get('error_msg')
        TaskManager(task).handle_status(status, error_msg)
    return HttpResponse('ok')


@api_func_anonymous
def load_config(request):
    user = model_manager.get_user(get_session_user(request))
    if user:
        config = models_manager.get_config(user)

        return {
            'fromTime': config.from_time.strftime('%H:%M'),
            'toTime': config.to_time.strftime('%H:%M'),
            'max': config.apply_max,
            'interval': config.apply_interval // 60,
            'times': config.search_max,
        }


@api_func_anonymous
def save_config(request, fromTime, toTime, max, interval, times):
    user = model_manager.get_user(get_session_user(request))
    if user:
        config = models_manager.get_config(user)

        config.from_time = datetime.time(*[int(x) for x in fromTime.split(':')])
        config.to_time = datetime.time(*[int(x) for x in toTime.split(':')])
        config.apply_max = int(max)
        config.search_max = int(times)
        config.apply_interval = int(interval) * 60
        config.save()

        models_manager.delete_plans_by_user(user)

    return 'ok'


@api_func_anonymous
def device_list(request):
    email = get_session_user(request)
    user = model_manager.get_user(email)
    if user:
        devices = models_manager.get_managed_devices_by_user(user)
        online = [x.device_id for x in model_manager.get_online(email)]

        return [{
            'phone': x.phone_num,
            'online': '是' if x.id in online else '否',
            'status': None,
            'id': x.id
        } for x in devices]


@api_func_anonymous
def task_list(request, i_id):
    device = models_manager.get_device_by_id(i_id)
    if device:
        tasks = models_manager.get_tasks_at_today(device)
        plans = PlanManager(device).refresh_plans()

        status = {0: '正在执行', 1: '已完成', -1: '已中断', -2: '被打断'}

        return [*[{
            'type': x.type.name,
            'time': x.start_time.astimezone(tz).strftime('%H:%M:%S'),
            'status': status[x.status],
            'qq': x.sns_user.login_name if x.sns_user else None,
            'result': x.result,
        } for x in tasks],
                *[{
                    'type': x.type.name,
                    'time': x.start_time.astimezone(tz).strftime('%H:%M:%S'),
                    'status': '等待执行',
                    'qq': x.sns_user.login_name if x.sns_user else None,
                    'result': None,
                } for x in plans]]


def set_trusteeship(request):
    device_id = request.POST.get('device_id')
    val = request.POST.get('value')

    device = models_manager.get_device_by_id(device_id)
    if device:
        if val == '1':
            device.in_trusteeship = True
        elif val == '0':
            device.in_trusteeship = False
            PlanManager(device).delete_device_plans()

        device.save()

    return HttpResponse('ok')
