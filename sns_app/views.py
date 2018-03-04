import requests
from django.conf import settings
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render


def home(request):
    return render(request, 'home.html', context={
        'ver': settings.JS_VER
    })


def dist(request, page):
    return HttpResponseRedirect('%s://jwres.cutt.com/dist/%s' % (request.scheme, page))


def internal_report(request):
    r = requests.get('http://127.0.0.1:8001/api/daily/report')
    return HttpResponse(r.text)
