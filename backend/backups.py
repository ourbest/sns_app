import os

import pandas as pd
from datetime import timedelta
from django_rq import job
from fastparquet import write

from backend import dates, model_manager
from backend.jobs import upload_to_qn
from backend.models import WeizhanClick, WeizhanDownClick


@job('default', timeout=1200)
def backup_weizhanclick(date=None):
    date = dates.get_date(date)

    for app in model_manager.get_dist_apps():
        weizhan_to_delete = WeizhanClick.objects.filter(app_id=app.app_id, ts__range=(
            date, date + timedelta(days=1) - timedelta(seconds=1)))
        df = pd.DataFrame(list(weizhan_to_delete.values()))
        filename = 'logs/{}.{}.parq'.format(app.app_id, date.strftime('%Y-%m-%d'))
        write(filename, df, compression='GZIP', file_scheme='simple')
        upload_to_qn(filename, 'weizhan/' + filename)
        os.remove(filename)
        weizhan_to_delete.delete()

        dl_to_delete = WeizhanDownClick.objects.filter(app_id=app.app_id, ts__range=(
            date, date + timedelta(days=1) - timedelta(seconds=1)))
        df = pd.DataFrame(list(dl_to_delete.values()))
        filename = 'logs/down.{}.{}.parq'.format(app.app_id, date.strftime('%Y-%m-%d'))
        write(filename, df, compression='GZIP', file_scheme='simple')
        upload_to_qn(filename, 'weizhan/' + filename)
        os.remove(filename)
        dl_to_delete.delete()
