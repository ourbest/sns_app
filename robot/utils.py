import logging
from datetime import datetime

import pytz
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from logzero import setup_logger

try:
    tz = pytz.timezone(settings.TIME_ZONE)
except ImproperlyConfigured:
    tz = pytz.timezone('Asia/Shanghai')

logger = setup_logger('robot', logfile='logs/robot.log')
logger.setLevel(logging.INFO)


def today_zero():
    return datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
