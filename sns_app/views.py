from django.conf import settings
from django.http import HttpResponseRedirect
from django.shortcuts import render


def home(request):
    return render(request, 'home.html', context={
        'ver': settings.JS_VER
    })


def dist(request, page):
    return HttpResponseRedirect('%s://jwres.cutt.com/dist/%s' % (request.scheme, page))
