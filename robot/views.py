from django.shortcuts import redirect, render
from . import decorator


def index(request):
    return redirect('/robot/search/')


@decorator.admin_login
def search(request):
    context = {}
    return render(request, 'robot/robot_search.html', context)
