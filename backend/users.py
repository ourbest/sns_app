import logging

from dj.utils import api_func_anonymous, api_error

from backend import api_helper, model_manager

logger = logging.getLogger('backend')


@api_func_anonymous
def user_info(request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    return api_helper.user_to_json(user)


@api_func_anonymous
def update_user_info(request, name, app_id, qq_id, wx_id, i_role):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    user.name = name
    if app_id:
        user.app_id = app_id

    user.role = i_role

    user.save()

    if qq_id:
        api_helper.save_cutt_id(user, qq_id, 0)
    if wx_id:
        api_helper.save_cutt_id(user, wx_id, 1)

    return api_helper.user_to_json(user)


@api_func_anonymous
def change_password(request, old_pwd, new_pwd):
    email = api_helper.get_session_user(request)
    user = api_helper.auth(email, old_pwd)
    if user:
        api_helper.set_password(user, new_pwd)
        return "ok"

    api_error(1001)
