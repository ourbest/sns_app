"""
新用户留存分析
"""
import requests
from datetime import timedelta
from django.db import connections

from backend import model_manager, dates
from backend.models import DeviceUserExtra
from backend.zhiyue_models import UserLocation


def sync_device_user():
    query = 'insert ignore into backend_deviceuserextra (user_id, app_id, created_at, ip, city, location, platform) ' \
            '(select deviceUserId,partnerId,createTime,ip,city,location, ' \
            'if(instr(extStr, \'iPhone\'), \'iphone\', \'android\') ' \
            'from datasystem_DeviceUser where (partnerId in (965004, 1619662, 1564395) or partnerId > 1564395) ' \
            'and createTime between current_date - interval 1 day and current_date)'

    with connections['zhiyue_rw'].cursor() as cursor:
        cursor.execute(query)

    today = dates.today()
    yesterday = (today - timedelta(1), today)
    extra = list(model_manager.query(DeviceUserExtra).filter(
        created_at__range=yesterday, lbs_flag=-1))
    ids = [x.user_id for x in extra]
    d = {x.userId: x.enabled for x in model_manager.query(UserLocation).filter(userId__in=ids)}
    for x in extra:
        if x.user_id in d:
            x.enabled = d[x.user_id]
            model_manager.save_ignore(extra, fields=['lbs_flag'])

    extra = list(model_manager.query(DeviceUserExtra).filter(area='', created_at__range=yesterday,
                                                             area_type=-1, location__isnull=False))

    for x in extra:
        name = get_area_name(x)
        if name:
            x.area = name
            if x.app_id != 965004 and '外地' in x.area:
                x.area_type = 2
                model_manager.save_ignore(extra, fields=['area', 'area_type'])


def get_area_name(user):
    response = requests.post('http://10.9.21.184/api/lbs/region',
                             {'appId': user.app_id, 'lbs': user.location})
    if response.status_code == 200:
        return response.json()['data']
