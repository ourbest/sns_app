from dj.utils import api_func_anonymous
from django.shortcuts import redirect, render
from . import decorator


def index(request):
    return redirect('/robot/search/')


@decorator.admin_login
def search(request):
    context = {}
    return render(request, 'robot/robot_search.html', context)


@api_func_anonymous
def robot_list():
    return [{
        'phone': '1234',
        'online': '是',
        'status': 0,
        'id': 1
    }, {
        'phone': '3456',
        'online': '否',
        'status': 1,
        'id': 2
    }]


@api_func_anonymous
def robot_task_list(i_id):
    return [{
        'type': '类型%s' % i_id,
        'time': '12:22',
        'status': '状态',
        'qq': '12345',
        'result': '结果'
    }]


a = '12:00'


@api_func_anonymous
def save_robot_config(request, fromTime, toTime, max, interval, times):
    global a
    a = fromTime


@api_func_anonymous
def load_robot_config():
    return {
        'fromTime': a,
        'toTime': '13:00',
        'max': 2,
        'interval': 5,
        'times': 10
    }
