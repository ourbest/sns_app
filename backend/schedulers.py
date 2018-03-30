from datetime import datetime, timedelta

import django_rq

scheduler = None


def get_scheduler():
    global scheduler
    if scheduler:
        return scheduler

    scheduler = django_rq.get_scheduler('default')
    return scheduler


def run_at(timestamp, func, *args, **kwargs):
    if isinstance(timestamp, datetime):
        timestamp = timestamp.timestamp()
    get_scheduler().enqueue_in(timedelta(seconds=datetime.now().timestamp() - timestamp), func, args, kwargs)
