from dj.utils import api_func_anonymous, api_error

from backend import api_helper, model_manager
from backend.models import UserDelegate, User


@api_func_anonymous
def user_info(request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    return api_helper.user_to_json(user)


@api_func_anonymous
def update_user_info(request, name, app_id, qq_id, wx_id, i_role, phone, i_notify):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    user.name = name
    if app_id:
        user.app_id = app_id
        model_manager.add_user_auth(user, app_id)

    user.role = i_role
    user.notify = i_notify
    user.phone = phone

    user.save()

    if qq_id:
        api_helper.save_cutt_id(user, qq_id, 0)
    if wx_id:
        api_helper.save_cutt_id(user, wx_id, 1)

    return api_helper.user_to_json(user)


@api_func_anonymous
def delegates(request):
    return [api_helper.user_to_json(x.delegate) for x in
            UserDelegate.objects.filter(owner__email=api_helper.get_session_user(request))]


@api_func_anonymous
def delegated(request):
    return [api_helper.user_to_json(x.owner) for x in
            UserDelegate.objects.filter(delegate__email=api_helper.get_session_user(request))]


@api_func_anonymous
def all_users():
    return [api_helper.user_to_json(x) for x in User.objects.all()]


@api_func_anonymous
def change_password(request, old_pwd, new_pwd):
    email = api_helper.get_session_user(request)
    user = api_helper.auth(email, old_pwd)
    if user:
        api_helper.set_password(user, new_pwd)
        return "ok"

    api_error(1001)


@api_func_anonymous
def set_delegates(delegates, request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    ids = delegates.split(';')
    if ids and ids[0] != '':
        UserDelegate.objects.filter(owner=user).exclude(delegate_id__in=ids).delete()
        for user_id in ids:
            try:
                UserDelegate(owner=user, delegate_id=user_id).save()
            except:
                pass
    else:
        UserDelegate.objects.filter(owner=user).delete()

    return 'ok'
