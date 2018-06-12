"""sns_app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.10/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""

from django.conf.urls import url, include
from django.contrib import admin
from django.http import FileResponse

import backend.urls
from . import views


def asserts(request, file):
    return FileResponse(open('asserts/%s' % file, 'rb'))


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^api/', include(backend.urls)),
    url(r'^ir', views.internal_report),
    url(r'^js/mj.js', views.mj_js),
    url(r'^plist/(?P<app>.+)$', views.plist),
    url(r'^down/(?P<app>.+)$', views.down),
    url(r'^asserts/(?P<file>.+)$', asserts),
    url(r'^$', views.home),
    url(r'^dist/(?P<page>.+)$', views.dist),
    url(r'^robot/', include('robot.urls', namespace='robot')),
    url(r'^django-rq/', include('django_rq.urls')),
]
