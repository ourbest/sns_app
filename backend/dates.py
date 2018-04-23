from datetime import datetime, timedelta

from dj import times


def get_date(date=None):
    if date and isinstance(date, str):
        return times.localtime(datetime.strptime(date[0:10], '%Y-%m-%d'))

    if not date:
        return times.localtime(datetime.now()).replace(hour=0, second=0, minute=0, microsecond=0)

    else:
        return times.localtime(date).replace(hour=0, second=0, minute=0, microsecond=0)


def today():
    return get_date()


def yesterday():
    return today() - timedelta(days=1)


def delta(date_str, days):
    dt = datetime.strptime(date_str, '%Y-%m-%d') + timedelta(days=days)
    return dt.strftime('%Y-%m-%d')


def current_week():
    now = today()
    if now.weekday() == 7:
        return now, now + timedelta(days=7)
    sunday = now - timedelta(now.weekday() + 1)
    return sunday, sunday + timedelta(6)


def plus_week(delta):
    f, t = current_week()
    return f + timedelta(7 * delta), t + timedelta(7 * delta)


def to_str(week, format='%Y-%m-%d'):
    (from_dt, to_dt) = week
    return '%s - %s' % (from_dt.strftime(format), to_dt.strftime(format))