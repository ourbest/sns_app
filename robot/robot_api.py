from dj.utils import api_func_anonymous
from backend.models import PhoneDevice, User
from robot.models import ScheduledTasks, Config, TaskLog
from django.http import HttpResponse
from .robot import Robot
import datetime
from django.utils import timezone
from dj import times


def reset(req):
    """ 24 : 00 """
    Robot.clear()
    config_queryset = Config.objects.all()
    for config in config_queryset:
        robot = Robot(config=config)
        robot.create_scheduled_tasks()

    return HttpResponse('ok')


def trusteeship(request):
    post = request.POST
    device_id = post.get('device_id')
    value = post.get('value')

    try:
        device = PhoneDevice.objects.get(id=device_id)
    except PhoneDevice.DoesNotExist:
        return HttpResponse('no')

    if value == '1':
        # 开
        device.in_trusteeship = True
        device.save()

        robot = Robot(user=device.owner)
        robot.create_scheduled_tasks(device)

    elif value == '0':
        # 关
        device.in_trusteeship = False
        device.save()

        ScheduledTasks.objects.filter(device=device).delete()
    else:
        return HttpResponse('no')

    return HttpResponse('ok')


@api_func_anonymous
def load_config(request):
    email = request.session.get('user')
    user = User.objects.filter(email=email).first()
    if user:
        config = Config.objects.get_or_create(owner=user)[0]

        return {
            'fromTime': config.opening_time.strftime('%H:%M'),
            'toTime': config.closing_time.strftime('%H:%M'),
            'max': config.max_num_of_apply,
            'interval': config.shortest_interval_apply_of_device // 60,
            'times': config.max_num_of_search,
        }


@api_func_anonymous
def save_config(request, fromTime, toTime, max, interval, times):
    email = request.session.get('user')
    try:
        config = Config.objects.get(owner__email=email)
    except Config.DoesNotExist:
        pass
    else:
        config.opening_time = datetime.time(*[int(x) for x in fromTime.split(':')])
        config.closing_time = datetime.time(*[int(x) for x in toTime.split(':')])
        config.max_num_of_apply = int(max)
        config.shortest_interval_apply_of_device = int(interval) * 60
        config.max_num_of_search = int(times)
        config.save()

        robot = Robot(config=config)
        robot.update_scheduled_tasks()

    return 'ok'


@api_func_anonymous
def device_list(request):
    email = request.session.get('user')
    user = User.objects.filter(email=email).first()
    if user:
        device_queryset = PhoneDevice.objects.filter(owner=user, in_trusteeship=True)
        data = []
        for device in device_queryset:
            if device.activedevice_set.exists():
                online = '是'
            else:
                online = '否'

            data.append({
                'phone': device.phone_num,
                'online': online,
                'status': None,
                'id': device.id
            })

        return data


@api_func_anonymous
def task_list(request, i_id):
    data = []

    today = times.localtime(timezone.now()).replace(hour=0, minute=0, second=0, microsecond=0)
    task_list1 = TaskLog.objects.select_related('type', 'sns_user').filter(device_id=i_id,
                                                                           start_time__gte=today).order_by(
        'start_time')
    status = {0: '正在执行', 1: '已完成', -1: '已中断', -2: '被打断', }
    for task in task_list1:
        data.append({
            'type': task.type.name,
            'time': times.to_str(task.start_time, '%H:%M:%S'),
            'status': status[task.status],
            'qq': task.sns_user.login_name if task.sns_user else None,
            'result': task.result,
        })

    task_list2 = ScheduledTasks.objects.select_related('type', 'sns_user').filter(device_id=i_id).order_by(
        'estimated_start_time')
    if task_list2.exists():
        if Robot.check_timeout(task_list2.first().estimated_start_time) == -1:
            user = User.objects.filter(email=request.session.get('user')).first()
            device = PhoneDevice.objects.filter(id=i_id).first()
            if user and device:
                Robot(user=user).update_scheduled_tasks(device)

    for task in task_list2:
        data.append({
            'type': task.type.name,
            'time': times.to_str(task.estimated_start_time, '%H:%M:%S'),
            'status': '等待执行',
            'qq': task.sns_user.login_name if task.sns_user else None,
            'result': None,
        })
    return data
