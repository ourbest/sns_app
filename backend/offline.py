from dj.utils import api_func_anonymous
from django.db import connection
from django.db.models import Count, Sum

from backend import api_helper
from backend.models import OfflineUser


@api_func_anonymous
def api_owners(request):
    app = api_helper.get_session_app(request)
    return [x for x in OfflineUser.objects.filter(app_id=app).values('owner').annotate(total=Count('user_id')) if
            x['total'] >= 30]


@api_func_anonymous
def api_owner_remain(owner):
    return OfflineUser.objects.filter(owner=owner).values('owner').annotate(
        total=Count('user_id'),
        remain=Sum('remain'))[0] if owner else []


@api_func_anonymous
def api_owner_detail(owner, date):
    if not owner:
        return []

    query = OfflineUser.objects.filter(owner=owner)
    if date:
        query = query.extra(where=['date(created_at) =\'%s\'' % date])

    return [x.json for x in query]


@api_func_anonymous
def api_owner_date(owner):
    if not owner:
        return []

    sql = 'select owner, date(created_at), count(*), sum(remain) from backend_offlineuser ' \
          'where owner = %s group by owner, date(created_at)' % owner

    with connection.cursor() as cursor:
        cursor.execute(sql)
        rows = cursor.fetchall()
        return [{
            'owner': owner,
            'date': date,
            'total': total,
            'remain': remain
        } for owner, date, total, remain in rows]
