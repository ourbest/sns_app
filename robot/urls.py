from django.conf.urls import url

from robot import views

app_name = 'robot'

urlpatterns = [
    url(r'^task$', views.get_task),
    url(r'^result$', views.handle_task_result),
    url(r'^report$', views.handle_task_status),

    url(r'^device/trusteeship$', views.set_trusteeship),
    url(r'^config/save$', views.save_config),
    url(r'^config/load$', views.load_config),
    url(r'^list$', views.device_list),
    url(r'^tasks$', views.task_list),
]
