from django.conf.urls import url
from . import views, search


app_name = 'robot'

urlpatterns = [
    url(r'^$', views.index),
    url(r'^search/$', views.search),

    # 查群
    url(r'^search/api$', search.handle_request),
    url(r'^search/update$', search.update, name='search/update'),
    url(r'^search/data$', search.data, name='search/data'),

    ## test
    url(r'^list$', views.robot_list),
    url(r'^tasks$', views.robot_task_list),
    url(r'^config/save$', views.save_robot_config),
    url(r'^config/load$', views.load_robot_config),
]
