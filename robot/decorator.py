from backend.models import User
from django.http import JsonResponse
from django.shortcuts import redirect


def admin_login(func):
    def inner(*args, **kwargs):
        email = args[0].session.get('user')
        db_email = User.objects.filter(email=email)
        if email and db_email:
            if email == db_email.first().email:
                return func(*args, **kwargs)
        return redirect('/')

    return inner


def permission_update(func):
    def inner(*args, **kwargs):
        email = args[0].session.get('user')
        if email == 'dengke.li@cutt.com':
            return func(*args, **kwargs)
        return JsonResponse({'result': '你不能修改内容'})

    return inner
