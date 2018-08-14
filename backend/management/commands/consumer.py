import re
from datetime import datetime
from django.conf import settings
from django.core.management import BaseCommand
from kafka import KafkaConsumer
from urllib.parse import unquote

from backend import model_manager
from backend.loggs import logger
from backend.models import WeizhanDownClick, WeizhanClick


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
                self.process_line(line)
        except:
            logger.error('Consumer error', exc_info=True)

    def process_line(self, line):
        match = re.match(
            r'([^\s]*) [^\s]* ([^\s]*) \[([^\]]*)\] "(POST|GET) ([^ ]*) HTTP\/1\.1" '
            r'(\d+) (\d+) "(.+?)" "(.+?)" "(.+?)" "(.+?)"',
            line)
        if match:
            ip, uid, tm, method, url, code, size, dm, ua, n, ref = match.groups()
            if url.startswith('/weizhan/tracking'):
                # self.stdout.write('line %s' % line)
                # tracking
                params = url.split('?', 1)[1]
                ps = params.split('&')
                down = WeizhanDownClick()
                for p in ps:
                    k, v = p.split('=', 1)
                    if k == 'app':
                        down.app_id = v
                        if int(v) not in model_manager.get_dist_app_ids():
                            return
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

                down.ip = ip
                down.ua = ua
                down.uuid = uid
                down.platform = 'android' if 'Android' in ua else 'iphone' if 'iPhone' in ua else 'other'
                down.net = 'wifi' if 'NetType/WIFI' in ua else '4G'
                down.ts = datetime.strptime(tm, '%d/%b/%Y:%H:%M:%S %z')
                down.save()
            elif url.startswith('/weizhan/article'):
                elems = url.split('?', 1)
                path = elems[0].split('/')
                if len(path) < 7:
                    return
                params = elems[1]
                click = WeizhanClick()
                click.app_id = path[5]

                if int(path[5]) not in model_manager.get_dist_app_ids():
                    return

                click.item_id = path[4]
                click.uid = path[6]
                click.ua = ua
                click.ts = datetime.strptime(tm, '%d/%b/%Y:%H:%M:%S %z')
                click.uuid = uid
                click.platform = 'android' if 'Android' in ua else 'iphone' if 'iPhone' in ua else 'other'
                click.net = 'wifi' if 'NetType/WIFI' in ua else '4G'

                ps = params.split('&')
                for p in ps:
                    k, v = p.split('=', 1)
                    if k == 'from':
                        click.from_param = v
                    elif k == 'isappinstalled':
                        click.is_installed = int(v)
                    elif k == 'q2':
                        click.qq = v
                    elif k == 'ts':
                        click.ts2 = v
                    elif k == 'dt':
                        click.tid = v
                click.save()
        else:
            self.stderr.write('wrong line: %s' % line)
