from django.conf import settings
from pyhive import hive

from backend import dates


def hive_cursor():
    return hive.connect(settings.HIVE_SERVER).cursor()


def get_online_ids(app_id, user_ids, date=dates.yesterday(), device=False):
    cursor = hive_cursor()
    try:
        query = ("""select DISTINCT userid from userstartup where partnerid=%s and dt = '%s' and userid in (%s)"""
                 if not device else
                 """select DISTINCT deviceuserid from userstartup 
                    where partnerid=%s and dt = '%s' and deviceuserid in (%s)""") \
                % (str(app_id), date if isinstance(date, str) else date.strftime('%Y-%m-%d'),
                   ','.join([str(x) for x in user_ids]))
        cursor.execute(query)
        rows = cursor.fetchall()
        return [x[0] for x in rows]
    finally:
        cursor.close()
