from datetime import datetime
from dj.utils import api_func_anonymous
from django.db import connections
from django.http import HttpResponse


@api_func_anonymous
def export_data(id, from_date, to_date, app):
    query = queries.get(id)

    if not query:
        return ''

    if '/' in from_date:
        from_date = datetime.strptime(from_date, '%Y/%m/%d').strftime('%Y-%m-%d')
        to_date = datetime.strptime(to_date, '%Y/%m/%d').strftime('%Y-%m-%d')

    html = ['<table>']
    with connections['default'].cursor() as cursor:
        cursor.execute(query, (from_date, to_date, app))
        field_names = [i[0] for i in cursor.description]
        html.append('<tr>' + (''.join(['<th>' + x + '</th>' for x in field_names])) + '</tr>')
        for row in cursor.fetchall():
            line = ['<tr>']
            for col in row:
                line.append('<td>%s</td>' % col)
            line.append('</tr>')
            html += line

    html.append('</table>')
    return HttpResponse(''.join(html))


# 查询分发pv/安装数据
queries = {
    'daily': '''select
  app_id 'APP',
  item_id '文章ID',
  sns_type '微信/QQ',
  title '标题',
  category '类型',
  `date` '日期',
  total_user '总安装',
  android_user '安装安装',
  iphone_user '苹果安装',
  total_pv '总PV',
  android_pv '安卓PV',
  iphone_pv '苹果PV',
  total_down '总下载页',
  android_down '安卓下载页',
  iphone_down '苹果下载页',
  total_remain '留存数',
  android_remain '安卓留存',
  iphone_remain '苹果留存'
from
  backend_dailydetaildata
where `date` between %s and %s and app_id = %s
'''}
