from django.http import HttpResponseRedirect

from backend.models import ShortenURL


def download(request, sid):
    if not sid:
        return None
    d = ShortenURL.objects.filter(pk=sid).first()
    return HttpResponseRedirect(d.url if d else 'https://baidu.com')
