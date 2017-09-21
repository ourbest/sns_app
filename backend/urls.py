from django.conf.urls import url

from backend import apis, users

app_name = 'backend'
urlpatterns = [
    url(r'^upload$', apis.upload),
    url(r'^task$', apis.task),
    # url(r'^image$', apis.image),
    url(r'^qr$', apis.qq_qr),
    url(r'^menu$', apis.get_menu),

    # imports ====
    url(r'^import/qq$', apis.import_qq),
    # url(r'^import/split$', apis.import_split),
    url(r'^import/user$', apis.import_user),
    url(r'^import/qun$', apis.import_qun),
    url(r'^import/stat$', apis.import_qun_stat),
    url(r'^import/useless_qun$', apis.import_useless_qun),
    url(r'^import/phone$', apis.import_phone),

    # my ====
    url(r'^my/qq$', apis.my_qq),
    url(r'^my/qun$', apis.my_qun),
    url(r'^my/pending/qun$', apis.my_pending_qun),
    url(r'^my/quiz/qun$', apis.my_quiz_qun),
    url(r'^my/qun/lost$', apis.my_lost_qun),
    url(r'^my/tasks$', apis.my_tasks),
    url(r'^my/online$', apis.online_phones),

    url(r'^device/qun$', apis.device_qun),
    url(r'^device/create$', apis.device_create),
    url(r'^device/tasks$', apis.device_tasks),

    url(r'^qq/create$', apis.qq_create),
    url(r'^split/qq$', apis.split_qq),
    url(r'^users$', apis.users),
    url(r'^devices$', apis.devices),
    url(r'^accounts$', apis.accounts),
    url(r'^account/info$', apis.account),
    url(r'^account/update$', apis.update_account),
    url(r'^account/qun$', apis.account_qun),
    url(r'^split/phone/qq$', apis.split_qun_to_device),
    url(r'^reset/phone/qq$', apis.reset_phone_split),
    url(r'^qun$', apis.export_qun),
    url(r'^send/qq$', apis.send_qq),
    url(r'^login/submit$', apis.login),
    url(r'^login/info$', apis.login_info),
    url(r'^logout$', apis.logout),
    url(r'^apps$', apis.apps),
    url(r'^app/summary$', apis.app_summary),
    url(r'^task/types$', apis.task_types),
    url(r'^task/create$', apis.create_task),
    url(r'^task/devices$', apis.task_devices),
    url(r'^task/files$', apis.task_files),
    url(r'^file/content$', apis.file_content),
    url(r'^image$', apis.file_content),
    url(r'^user/info$', users.user_info),
    url(r'^user/update$', users.update_user_info),
    url(r'^user/pwd$', users.change_password),
    url(r'^user/all$', users.all_users),
    url(r'^user/delegates$', users.delegates),
    url(r'^user/delegated$', users.delegated),
    url(r'^user/delegate/update$', users.set_delegates),
]
