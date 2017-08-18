from django.conf.urls import url

from backend import apis

app_name = 'backend'
urlpatterns = [
    url(r'^upload$', apis.upload),
    url(r'^image$', apis.image),
    url(r'^qr$', apis.qq_qr),
    url(r'^import/qq$', apis.import_qq),
    url(r'^import/qun$', apis.import_qun),
    url(r'^split/qq$', apis.split_qq),
    url(r'^split/phone/qq$', apis.split_qun_to_device),
    url(r'^qun$', apis.export_qun),
    url(r'^send/qq$', apis.send_qq),
    url(r'^login/submit$', apis.login),
    url(r'^apps$', apis.apps),
]
