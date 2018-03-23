from backend.models import SnsGroupSplit, SnsGroup
from django.http import HttpResponse
from .models import ScheduledTasks, Search
from robot.robot import Robot, TASK_TIMEOUT
from django.utils import timezone
from random import choice
from . import models_manager


def get_task_api(request):
    get = request.GET
    device_id = get.get('id')

    task = ScheduledTasks.objects.select_related('owner', 'device').filter(device__phone_num=device_id,
                                                                           status__in=[0, 1]).order_by(
        'estimated_start_time').first()

    if task:
        time_diff = (timezone.now() - task.estimated_start_time).total_seconds()
        if 0 <= time_diff <= TASK_TIMEOUT:
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

        elif time_diff > TASK_TIMEOUT:
            # 超时
            user = task.owner
            device = task.device
            robot = Robot(user=user)
            ScheduledTasks.objects.filter(device=device, status__in=[0, 1]).delete()
            if robot.create_scheduled_tasks(device):
                return get_task_api(request)

    return HttpResponse(None)


def get_apply_content(task: ScheduledTasks):
    task_type = task.type_id
    provider = task.sns_user.provider
    login_name = task.sns_user.login_name

    device_id = task.device_id
    group_queryset = SnsGroupSplit.objects.filter(phone_id=device_id, status=0).order_by('?')
    if group_queryset.exists():
        group_id = group_queryset.first().group_id
    else:
        task.status = -1
        task.save()
        return None

    task.status = 1
    task.save()

    # 任务类型 客户端 帐号 密码 群号
    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={task_type}\n' \
           'client={provider}\n' \
           'account={login_name}\n' \
           'group={group_id}\n'.format(task_type=task_type,
                                       provider=provider,
                                       login_name=login_name,
                                       group_id=group_id,
                                       task_id=task.id)


def get_search_content(task_query: ScheduledTasks):
    search_queryset = Search.objects.filter(status=0)
    if not search_queryset.exists():
        task_query.status = -2
        task_query.save()
        return None

    search = choice(search_queryset)

    models_manager.update_search(search=search)

    task_query.status = 1
    task_query.save()

    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={type}\n' \
           'word={word}\n'.format(type=task_query.type_id, word=search.word, task_id=task_query.id)


def get_statistics_content(task_query: ScheduledTasks):
    task_query.status = 1
    task_query.save()

    return '[RobotTask]\n' \
           'id={task_id}\n' \
           'type={type}\n'.format(type=task_query.type_id, task_id=task_query.id)


def task_result_api(request):
    post = request.POST
    task_type = post.get('type')

    if task_type == '1':
        search_result(post)
    elif task_type == '2':
        apply_result(post)
    elif task_type == '4':
        pass

    return HttpResponse('ok')


def search_result(data):
    word = data.get('word')
    group_id = data.get('group_id')
    group_name = data.get('group_name')
    group_user_count = data.get('group_user_count')

    if models_manager.update_search(word, group_id, group_name, group_user_count):
        task_id = data.get('task_id')
        try:
            task_query = ScheduledTasks.objects.get(id=task_id)
        except ScheduledTasks.DoesNotExist:
            pass
        else:
            group_user_count = data.get('group_user_count')
            result = task_query.result
            if result:
                lis = result.split('/')
                result = str(int(lis[0]) + 1) + '/' + str(int(lis[1]) + int(group_user_count))
            else:
                result = '1/' + group_user_count
            task_query.result = result
            task_query.save()


def apply_result(data):
    task_id = data.get('task_id')
    result = data.get('result')
    """
    结果：
    -2帐号被封了
    -1没有找到帐号
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
