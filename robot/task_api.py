from backend.models import SnsGroupSplit
from django.http import HttpResponse
from .models import ScheduledTasks, Search, TaskLog
from robot.robot import Robot
from . import models_manager
from django.utils import timezone
import re


def get_task_api(request):
    get = request.GET
    phone_num = get.get('id')

    task = TaskLog.objects.select_related('device').filter(status=0, device__phone_num=phone_num).first()
    if task:
        check = Robot.check_timeout(task.start_time)
        if check == 1:
            return get_task_content(task)
        elif check == -1:
            task.status = -1
            task.result = '超时'
            task.save()

            device = task.device
            user = device.owner
            Robot(user=user).update_scheduled_tasks(device)

    task = ScheduledTasks.objects.select_related('device').filter(device__phone_num=phone_num).order_by(
        'estimated_start_time').first()
    if task:
        check = Robot.check_timeout(task.estimated_start_time)
        if check == 1:
            return get_task_content(task)
        elif check == -1:
            device = task.device
            user = device.owner
            robot = Robot(user=user)
            if robot.update_scheduled_tasks(device=device):
                return get_task_api(request)

    return HttpResponse(None)


def get_task_content(task):
    if not isinstance(task, TaskLog):
        device = task.device
        task_type = task.type
        sns_user = task.sns_user
        task.delete()

        task = TaskLog.objects.create(device=device, type=task_type, sns_user=sns_user)

    task_type = task.type_id
    if task_type == 1:
        # 查群
        return HttpResponse(get_search_content(task))
    elif task_type == 2:
        # 加群
        return HttpResponse(get_apply_content(task))
    elif task_type == 4:
        # 统计
        return HttpResponse(get_statistics_content(task))


def get_apply_content(task):
    group = SnsGroupSplit.objects.filter(phone_id=task.device_id, status=0).order_by('?').first()
    if group:
        group_id = group.group_id
        # group.status = 1
        # group.save()
    else:
        task.status = -1
        task.result = '无群号'
        task.save()
        return None

    # 任务类型 客户端 帐号 密码 群号
    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={task_type}\n' \
           'client={provider}\n' \
           'account={login_name}\n' \
           'group={group_id}\n'.format(task_type=task.type_id,
                                       provider=task.sns_user.provider,
                                       login_name=task.sns_user.login_name,
                                       group_id=group_id,
                                       task_id=task.id)


def get_search_content(task):
    search = Search.objects.filter(status=0, area__app_id=task.device.owner.app_id).order_by('?').first()
    if not search:
        task.status = -1
        task.result = '无搜索词'
        task.save()
        return None

    models_manager.update_search(search=search)

    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={type}\n' \
           'word={word}\n'.format(type=task.type_id, word=search.word, task_id=task.id)


def get_statistics_content(task):
    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={type}\n'.format(type=task.type_id, task_id=task.id)


# 接收手机端任务结果
def task_result_api(request):
    post = request.POST
    task_id = post.get('task_id')
    try:
        task = TaskLog.objects.get(id=task_id)
    except TaskLog.DoesNotExist:
        pass
    else:
        status = post.get('status')
        task_type = task.type_id
        if status == '1':
            if task_type == 1:
                models_manager.update_operation_device(today_search=True)
            elif task_type == 2:
                models_manager.update_operation_sns_user(today_apply=True)
            elif task_type == 4:
                models_manager.update_operation_device(today_statistics=True)

            task.finish_time = timezone.now()
            task.status = int(status)
            result = post.get('result')
            if result:
                task.result = result
            task.save()
        elif status == '-1' or status == '-2':
            task.status = int(status)
            result = post.get('result')
            if result:
                task.result = result
            task.save()

        if task_type == 1:
            search_result(request, task)
        elif task_type == 2:
            apply_result(request, task)
        elif task_type == 4:
            pass

    return HttpResponse('ok')


def search_result(request, task):
    data = request.POST

    word = data.get('word')
    group_id = data.get('group_id')
    group_name = data.get('group_name')
    group_user_count = data.get('group_user_count')

    if models_manager.update_search(word, group_id, group_name, group_user_count):
        group_user_count = data.get('group_user_count')
        result = task.result
        if re.match('^\d+/\d+$', result):
            lis = result.split('/')
            result = str(int(lis[0]) + 1) + '/' + str(int(lis[1]) + int(group_user_count))
        else:
            result = '1/' + group_user_count
        task.result = result
        task.save()


def apply_result(request, task):
    """
    结果：
    0申请入群（不是最后结果）
    1不存在
    2已加群
    3付费群
    4无需验证（不是最后结果）
    5无需验证已加入
    6无需验证未加入
    7需要验证（不是最后结果）
    8已发送验证
    9发送验证失败
    10回答问题
    11满员群
    12不允许加入
    """
    data = request.POST
    apply_ret = data.get('apply_ret')
    group = data.get('group')
    if apply_ret:
        if apply_ret == '1' or apply_ret == '3' or apply_ret == '10' or apply_ret == '11' or apply_ret == '12':
            update_sns_group_split_status(group, -1)
        elif apply_ret == '2':
            update_sns_group_split_status(group, 3)
        elif apply_ret == '5':
            update_sns_group_split_status(group, 3)
            task.result = group
            task.save()

        elif apply_ret == '6' or apply_ret == '9':
            update_sns_group_split_status(group, 0)
            task.result = '加群受限'
            task.save()

            robot = Robot(user=task.device.owner)
            models_manager.update_operation_sns_user(today_apply=robot.config.max_num_of_apply)
            robot.update_scheduled_tasks(task.device)
        elif apply_ret == '8':
            update_sns_group_split_status(group, 2)
            task.result = group
            task.save()
        else:
            raise ValueError('error apply_ret=' + apply_ret)
    else:
        update_sns_group_split_status(group, 0)


def update_sns_group_split_status(group_id, status):
    try:
        group = SnsGroupSplit.objects.get(group_id=group_id)
    except SnsGroupSplit.DoesNotExist:
        pass
    else:
        group.status = status
        group.save()
        return group