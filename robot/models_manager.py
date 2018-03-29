from .models import Area, Keyword, Search, OperationDevice, OperationSnsUser
from backend.models import App, SnsGroup, PhoneDevice, SnsUser
import datetime
from django.utils import timezone


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


def update_search(word=None, group_id=None, group_name=None, group_user_count=None, search: Search = None):
    if word and group_id and group_name and group_user_count and group_id.isdigit() and group_user_count.isdigit():
        search_query = Search.objects.select_related('area__app').filter(word=word).first()

        if search_query:
            app = search_query.area.app
            old_group = SnsGroup.objects.filter(group_id=group_id)
            if old_group:
                old_group.update(group_name=group_name, group_user_count=int(group_user_count))
            else:
                SnsGroup.objects.create(group_id=group_id, group_name=group_name,
                                        group_user_count=int(group_user_count),
                                        app=app)

                search_query.group_increment += 1
                search_query.group_user_increment += int(group_user_count)
                search_query.save()
                return True
    elif search:
        search.search_count += 1
        search.last_time = datetime.datetime.now()
        search.save()


def update_operation_device(device, today_search=False, today_statistics=False):
    operation = OperationDevice.objects.filter(device=device).first()
    if operation:
        if today_search:
            operation.today_search += 1
            operation.last_apply = timezone.now()
        if today_statistics:
            operation.today_statistics += 1

        operation.save()


def update_operation_sns_user(sns_user, today_apply: bool or int = False):
    operation = OperationSnsUser.objects.filter(sns_user=sns_user).first()
    if operation:
        if isinstance(today_apply, bool) and today_apply:
            operation.today_apply += 1
        elif isinstance(today_apply, int):
            operation.today_apply = today_apply

        operation.save()


def operation_of_sns_user(sns_user: SnsUser):
    return OperationSnsUser.objects.get_or_create(sns_user=sns_user)[0]


def operation_of_device(device: PhoneDevice):
    return OperationDevice.objects.get_or_create(device=device)[0]
