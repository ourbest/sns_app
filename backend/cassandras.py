from cassandra.cluster import Cluster
from django.conf import settings

cassandra_session = None
cassandra_cluster = None


def is_online(app_id, user_ids, date):
    session = get_session()
    cql = 'select userid from cassandra_OnlineUser where userId in (%s) and partnerId=%s and onlineDate=\'%s\''
    rows = session.execute(cql % (','.join([str(x) for x in user_ids]), app_id, date))
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
