from django.conf.urls import url

from backend import apis

app_name = 'backend'
urlpatterns = [
    url(r'^upload$', apis.upload),
    url(r'^image$', apis.image),
    url(r'^qr$', apis.qq_qr),
    url(r'^import/qq$', apis.import_qq),
    url(r'^split/qq$', apis.split_qq),
    url(r'^send/qq$', apis.send_qq),
]
