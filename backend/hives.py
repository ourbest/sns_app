from django.conf import settings
from pyhive import hive


def hive_cursor():
    return hive.connect(settings.HIVE_SERVER).cursor()
