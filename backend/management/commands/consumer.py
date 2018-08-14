import re
from datetime import datetime
from django.conf import settings
from django.core.management import BaseCommand
from kafka import KafkaConsumer
from urllib.parse import unquote

from backend.loggs import logger
from backend.models import WeizhanDownClick


class Command(BaseCommand):
    def handle(self, *args, **options):
        consumer = KafkaConsumer(settings.WEIZHAN_LOG_TOPIC, group_id='tuiguang',
                                 bootstrap_servers=settings.BOOTSTRAP_SERVERS)

        while True:
            self.open_consumer(consumer)

    def open_consumer(self, consumer):
        try:
            for msg in consumer:
                line = msg.value.decode('utf-8')
                match = re.match(
                    r'([^\s]*) [^\s]* ([^\s]*) \[([^\]]*)\] "(POST|GET) ([^ ]*) HTTP\/1\.1" '
                    r'(\d+) (\d+) "(.+?)" "(.+?)" "(.+?)" "(.+?)"',
                    line)
                if match:
                    ip, uid, tm, method, url, code, size, dm, ua, n, ref = match.groups()
                    if url.startswith('/weizhan/tracking'):
                        self.stdout.write('line %s' % line)
                        # tracking
                        params = url.split('?', 1)[1]
                        ps = params.split('&')
                        down = WeizhanDownClick()
                        for p in ps:
                            k, v = p.split('=', 1)
                            if k == 'app':
                                down.app_id = v
                            elif k == 'itemId':
                                down.item_id = v
                            elif k == 'uid':
                                down.uid = v
                            elif k == 'img':
                                down.img = unquote(v) if v else ''
                            elif k == 'href':
                                down.href = unquote(v) if v else ''
                            elif k == 'type':
                                down.type = v
                            elif k == 'idx':
                                down.idx = v
                            elif k == 'tid':
                                down.tid = v

                            down.uuid = uid
                            down.ip = ip

                            down.platform = 'android' if 'Android' in ua else 'iphone'
                            down.net = 'wifi' if 'NetType/WIFI' in ua else '4G'
                            down.ts = datetime.strptime(tm, '%d/%b/%Y:%H:%M:%S %z')
                            down.save()
                else:
                    self.stderr.write('wrong line: %s' % line)
        except:
            logger.error('Consumer error', exc_info=True)
