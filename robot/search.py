from django.http import JsonResponse, HttpResponse
from robot.models import Keyword, Area, Search
from backend.models import SnsGroup
import random
import re
from . import models_manager
import datetime
from .decorator import permission_update


def handle_request(request):
    post = request.POST
    my_type = post.get('type')

    # 0 - 请求搜索词， 1 - 搜索结果
    if my_type == '0':
        # 随机抽取一条[状态为0]的数据
        search_queryset = Search.objects.filter(status=0)
        if search_queryset:
            search = random.choice(search_queryset)
            word = search.word

            search.search_count += 1
            search.last_time = datetime.datetime.now()
            search.save()

            return HttpResponse('[ok]' + word)
        else:
            return HttpResponse('[none]')
    elif my_type == '1':
        word = post.get('word')
        group_id = post.get('group_id')
        group_name = post.get('group_name')
        group_user_count = post.get('group_user_count')

        search_queryset = Search.objects.select_related('area__app').filter(word=word)
        if search_queryset:
            app = search_queryset.first().area.app
        else:
            app = None

        if group_id and group_name and group_user_count and app:
            if group_id.isdigit() and group_user_count.isdigit():
                old_group = SnsGroup.objects.filter(group_id=group_id)
                if old_group:
                    # 群存在,更新一下数据
                    old_group.update(group_name=group_name, group_user_count=int(group_user_count))
                else:
                    # 群不存在，创建并更新Search数据
                    SnsGroup.objects.create(group_id=group_id, group_name=group_name,
                                            group_user_count=int(group_user_count),
                                            app=app)

                    search = search_queryset.first()
                    search.group_increment += 1
                    search.group_user_increment += int(group_user_count)
                    search.save()

        return HttpResponse('ok')


@permission_update
def update(request):
    """
    处理Search更改数据的请求
    """
    post = request.POST
    my_type = post.get('type')
    area = post.get('area').replace(' ', '')
    keyword = post.get('keyword').replace(' ', '')

    result = ''

    if area:
        res = re.match(r'^(?P<id>\d*)(?P<name>.*)', area)
        app_id, area_name = res.group('id', 'name')  # 拆解area获得生活圈id和地区名
        if app_id and area_name:
            area_query = Area.objects.filter(area=area_name)
            if my_type == 'add':
                if area_query:  # 该数据已存在
                    if area_query.first().isDelete:  # 该数据为逻辑删除
                        area_query.update(isDelete=False)  # 恢复为未删除
                        search = Search.objects.select_related('keyword').filter(area=area_query)
                        if search:  # 并将该数据对应的Search数据状态改为0
                            search.filter(keyword__isDelete=False).update(status=0)
                        result += '地区名添加成功 '
                    else:  # 数据没有被标记为删除
                        result += '地区名已存在 '
                else:  # 该数据不存在
                    area_relation = models_manager.create_area(int(app_id), area_name)
                    if area_relation == 'no':
                        result += '地区名ID错误 '
                    else:
                        result += '地区名添加成功 '
                        auto_create_search('area', area_relation)
            elif my_type == 'del':
                if area_query:
                    auto_forbidden_search('area', area_query.first())
                    area_query.update(isDelete=True)
                    result += '地区名删除成功 '
                else:
                    result += '地区名不存在 '
        else:
            result += '地区名格式错误 '

    if keyword:
        keyword_query = Keyword.objects.filter(keyword=keyword)
        if my_type == 'add':
            if keyword_query:  # 有数据
                if keyword_query.first().isDelete:  # 且没有没逻辑删除
                    keyword_query.update(isDelete=False)  # 恢复
                    search = Search.objects.select_related('area').filter(keyword=keyword_query)
                    if search:
                        search.filter(area__isDelete=False).update(status=0)
                    result += '关键词添加成功 '
                else:
                    result += '关键词已存在 '
            else:
                keyword_relation = models_manager.create_keyword(keyword)
                result += '关键词添加成功 '
                auto_create_search('keyword', keyword_relation)
        elif my_type == 'del':
            if keyword_query:
                auto_forbidden_search('keyword', keyword_query.first())
                keyword_query.update(isDelete=True)
                result += '关键词删除成功 '
            else:
                result += '关键词不存在 '

    return JsonResponse({'result': result})


def auto_create_search(my_type, relation):
    if my_type == 'area':
        for keyword in Keyword.objects.all():
            models_manager.create_search(relation, keyword)
    elif my_type == 'keyword':
        for area in Area.objects.all():
            models_manager.create_search(area, relation)


def auto_forbidden_search(my_type, relation):
    if my_type == 'area':
        Search.objects.filter(area=relation).update(status=1)
    if my_type == 'keyword':
        Search.objects.filter(keyword=relation).update(status=1)


def data(request):
    """
    Ajax请求，将search的数据返回
    """
    area_data = Area.objects.filter(isDelete=False).order_by('-id')
    keyword_data = Keyword.objects.filter(isDelete=False).order_by('-id')
    search_queryset = Search.objects.select_related('area__app').all()
    search_data = search_queryset.filter(search_count__gt=0).order_by('-last_time')

    data1 = '<tr><th>生活圈ID</th><th>地区名</th><th>创建时间</th></tr>'
    for i in area_data:
        data1 += '<tr>'
        data1 += '<td>' + str(i.shq_id) + '</td>'
        data1 += '<td>' + i.area + '</td>'
        data1 += '<td>' + str(i.created_time.strftime('%m-%d %H:%M')) + '</td>'
        data1 += '</tr>'
    data1 = '<table>' + data1 + '</table>'

    data2 = '<tr><th>关键词</th><th>创建时间</th></tr>'
    for i in keyword_data:
        data2 += '<tr>'
        data2 += '<td>' + i.keyword + '</td>'
        data2 += '<td>' + str(i.created_time.strftime('%m-%d %H:%M')) + '</td>'
        data2 += '</tr>'
    data2 = '<table>' + data2 + '</table>'

    data3 = '<tr><th>搜索词</th><th>群增量</th><th>群人数增量</th><th>搜索次数</th><th>状态</th><th>最近一次的搜索时间</th></tr>'
    for i in search_data:
        data3 += '<tr>'
        data3 += '<td>' + i.word + '</td>'
        data3 += '<td>' + str(i.group_increment) + '</td>'
        data3 += '<td>' + str(i.group_user_increment) + '</td>'
        data3 += '<td>' + str(i.search_count) + '</td>'
        if i.status == 0:
            status = '使用'
        elif i.status == 1:
            status = '禁用'
        else:
            status = 'error'
        data3 += '<td>' + status + '</td>'
        if i.last_time:
            data3 += '<td>' + str(i.last_time.strftime('%m-%d %H:%M')) + '</td>'
        else:
            data3 += '<td>' + '' + '</td>'
        data3 += '</tr>'
    data3 = '<table>' + data3 + '</table>'

    data4 = '<tr><th>生活圈</th><th>群增量</th><th>群人数增量</th></tr>'
    apps = []
    for search in search_queryset:
        app = search.area.app
        if app not in apps:
            apps.append(app)
            group_increment = 0
            group_user_increment = 0
            for i in search_queryset.filter(area__app=app):
                group_increment += i.group_increment
                group_user_increment += i.group_user_increment
            data4 += '<tr><td>' + app.app_name + '</td><td>' + str(group_increment) + '</td><td>' + str(
                group_user_increment) + '</td></tr>'
    data4 = '<table>' + data4 + '</table>'

    return JsonResponse({'table1': data1, 'table2': data2, 'table3': data3, 'table4': data4})
