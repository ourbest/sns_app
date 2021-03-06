from cassandra.cluster import Cluster
from django.conf import settings

from backend import dates

cassandra_session = None
cassandra_cluster = None


def get_online_ids(app_id, user_ids, date=dates.yesterday()):
    date_str = date if isinstance(date, str) else date.strftime('%Y-%m-%d')

    session = get_session()
    cql = 'select userid from cassandra_OnlineUser where userId in (%s) and partnerId=%s and onlineDate=\'%s\'' \
          % (','.join([str(x) for x in user_ids]), app_id, date_str)
    rows = session.execute(cql)
    return [x[0] for x in rows]


def get_cluster():
    global cassandra_cluster
    if cassandra_cluster is None:
        cassandra_cluster = Cluster(settings.CASSANDRA_SERVERS)
    return cassandra_cluster


def get_session():
    global cassandra_session
    if cassandra_session is None:
        cassandra_session = get_cluster().connect("cutt")
    return cassandra_session


def get_online_time(app_id, user_ids, date):
    date_str = date if isinstance(date, str) else date.strftime('%Y-%m-%d')

    session = get_session()
    cql = 'select userid, firstup from cassandra_OnlineUser ' \
          'where userId in (%s) and partnerId=%s and onlineDate=\'%s\'' \
          % (','.join([str(x) for x in user_ids]), app_id, date_str)
    rows = session.execute(cql)
    return {x[0]: x[1] for x in rows}
