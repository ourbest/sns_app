from django.conf.urls import url

from backend import apis

app_name = 'backend'
urlpatterns = [
    url(r'^upload$', apis.upload),
    url(r'^task$', apis.task),
    url(r'^image$', apis.image),
    url(r'^qr$', apis.qq_qr),
    url(r'^import/qq$', apis.import_qq),
    # url(r'^import/split$', apis.import_split),
    url(r'^import/user$', apis.import_user),
    url(r'^import/qun$', apis.import_qun),
    url(r'^import/stat$', apis.import_qun_stat),
    url(r'^import/useless_qun$', apis.import_useless_qun),
    url(r'^import/phone$', apis.import_phone),
    url(r'^my/qun$', apis.my_qun),
    url(r'^my/qun/lost$', apis.my_lost_qun),
    url(r'^split/qq$', apis.split_qq),
    url(r'^users$', apis.users),
    url(r'^devices$', apis.devices),
    url(r'^split/phone/qq$', apis.split_qun_to_device),
    url(r'^qun$', apis.export_qun),
    url(r'^send/qq$', apis.send_qq),
    url(r'^login/submit$', apis.login),
    url(r'^login/info$', apis.login_info),
    url(r'^logout$', apis.logout),
    url(r'^apps$', apis.apps),
]
