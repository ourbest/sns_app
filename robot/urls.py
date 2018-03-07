from django.conf.urls import url
from . import views, search

urlpatterns = [
    url(r'^$', views.index),
    url(r'^search/$', views.search),

    # 查群
    url(r'^search/api$', search.handle_request),
    url(r'^search/update$', search.update, name='search/update'),
    url(r'^search/data$', search.data, name='search/data'),
]
