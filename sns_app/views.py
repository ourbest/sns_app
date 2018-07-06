import time

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
            var url = "https://zhiyue.cutt.com/jsapi/" + func + "/";
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


def plist(request, app):
    return HttpResponse('''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
    <dict>
        <key>items</key>
        <array>
            <dict>
                <key>assets</key>
                <array>
                    <dict>
                        <key>kind</key>
                        <string>software-package</string>
                        <key>url</key>
                        <string>https://pkg.appresource.net/app%s.ipa?v=%s</string>
                    </dict>
                    <dict>
                        <key>kind</key>
                        <string>display-image</string>
                        <key>needs-shine</key>
                        <false/>
                        <key>url</key>
                        <string>https://www.cutt.com/icon/app/%s</string>
                    </dict>
                </array>
                <key>metadata</key>
                <dict>
                    <key>bundle-identifier</key>
                    <string>com.cutt.app%s</string>
                    <key>bundle-version</key>
                    <string>1.0</string>
                    <key>kind</key>
                    <string>software</string>
                    <key>title</key>
                    <string>生活圈</string>
                </dict>
            </dict>
        </array>
    </dict>''' % (app, int(time.time()), app, app), content_type='application/x-plist', charset='utf-8')


def down(request, app):
    return HttpResponse('''<!DOCTYPE html><html>
<head>
    <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
    <meta http-equiv="Content-Type" content="text/html; charset=gb2312"/>
    <title>应用下载</title>
</head>

<body>
<div id='ios'>
<a href="http://cms.cutt.com/preview/iphone/%s">安装iPhone版</a>

<div>信任证书位置：设置 => 通用 => 设备管理 => BEIJING DENTSU... => 信任"..."</div>
</div>
</body>
</html>''' % (app,), charset='utf-8')
