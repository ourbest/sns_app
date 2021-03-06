from dj.utils import api_func_anonymous, api_error

from backend import api_helper, model_manager
from backend.models import UserDelegate, User, AppUser, UserFollowApp


@api_func_anonymous
def user_info(request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    return api_helper.user_to_json(user)


@api_func_anonymous
def disable_user(email):
    user = model_manager.get_user(email)
    if user and user.status != -1:
        user.status = -1
        model_manager.save_ignore(user, fields=['status'])


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

    try:
        user.save()
    except:
        pass

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
def all_users(request):
    query = User.objects.filter(status__in=(0, 1))
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    if not user or user.role == 2:
        query = query.filter(role__lt=3)
    return [api_helper.user_to_json(x) for x in query]


@api_func_anonymous
def update_user_status(email, i_status):
    user = model_manager.get_user(email)
    if user and user.status != i_status:
        user.status = i_status
        user.save()


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


@api_func_anonymous
def remove_majia(i_id, request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)

    db = AppUser.objects.filter(cutt_user_id=i_id, user=user).first()
    if db:
        db.type = -1
        db.save()
        AppUser.objects.filter(cutt_user_id=i_id, user=user).exclude(type=-1).delete()

    return 'ok'


@api_func_anonymous
def update_majia_type(i_id, i_type, request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)

    db = AppUser.objects.filter(cutt_user_id=i_id, user=user).first()
    if db:
        AppUser.objects.filter(cutt_user_id=i_id, user=user).update(type=i_type)

    return 'ok'


@api_func_anonymous
def api_my_follow(request, ids):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    user.userfollowapp_set.all().delete()
    for app_id in ids.split(';'):
        model_manager.save_ignore(UserFollowApp(user=user, app_id=app_id))
    return ''


@api_func_anonymous
def api_my_following(request):
    email = api_helper.get_session_user(request)
    user = model_manager.get_user(email)
    return [x.app_id for x in user.userfollowapp_set.all()]
