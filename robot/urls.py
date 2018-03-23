from django.conf.urls import url
from . import views, search, task_api, robot_api

urlpatterns = [
    url(r'^$', views.index),

    # 查群
    url(r'^search/$', views.search),
    url(r'^search/api$', search.handle_request),
    url(r'^search/update$', search.update, name='search/update'),
    url(r'^search/data$', search.data, name='search/data'),

    url(r'^task/api$', task_api.get_task_api),
    url(r'^task/result$', task_api.task_result_api),
    url(r'^task/reset$', robot_api.reset),
    url(r'^device/trusteeship$', robot_api.trusteeship),
    url(r'^config/save$', robot_api.save_config),
    url(r'^config/load$', robot_api.load_config),
    url(r'^list$', robot_api.device_list),
    url(r'^tasks$', robot_api.task_list),

]
