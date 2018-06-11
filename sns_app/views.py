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
    r = requests.get('http://127.0.0.1:8000/api/daily/report')
    return HttpResponse(r.text)


def mj_js(request):
    return HttpResponse('''(function () {
    if (!window.JW) {
        var toURL = function (func, aa) {
            var url = "http://zhiyue.cutt.com/jsapi/" + func + "/";
            var a = [];
            for (var i = 0; i < aa.length; i++) {
                var s = aa[i];
                if (aa[i] === null || aa[i] === "" || aa[i] === undefined) {
                    s = "(null)";
                }
                a.push(encodeURIComponent(s));
            }

            url += a.join('/');
            window.location = url;
        };

        window.JW = {
            share: function(data) {
                toURL("share", [0, 0, '', data, '', ''])
            },

            pay: function() {
                toURL('newPage', ['https://baidu.com?view=nonav']);
            }
        }
    }
})();''', content_type='application/javascript')
