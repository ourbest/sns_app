from .models import Area, Keyword, Search
from backend.models import App
import datetime


def create_area(app_id, area_name):
    app = App.objects.filter(app_id=app_id)
    if app:
        area = Area()
        area.shq_id = app_id
        area.area = area_name
        area.app = app.first()
        area.save()
        return area
    return 'no'


def create_keyword(keyword):
    return Keyword.objects.create(keyword=keyword)


def create_search(area_relation, keyword_relation):
    keyword = keyword_relation.keyword
    area = area_relation.area
    words = (keyword + area, area + keyword)
    for word in words:
        old = Search.objects.filter(word=word)
        if old:
            old.update(status=0)
        else:
            if not keyword_relation.isDelete and not area_relation.isDelete:
                Search.objects.create(word=word, area=area_relation, keyword=keyword_relation)
            else:
                Search.objects.create(word=word, area=area_relation, keyword=keyword_relation, status=1)
