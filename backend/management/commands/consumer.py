from django.conf import settings
from django.core.management import BaseCommand
from kafka import KafkaConsumer

from backend.log_parser import process_line
from backend.loggs import logger


class Command(BaseCommand):
    def handle(self, *args, **options):
        while True:
            self._consume()

    def _consume(self):
        try:
            consumer = KafkaConsumer(settings.WEIZHAN_LOG_TOPIC, group_id='tuiguang',
                                     bootstrap_servers=settings.BOOTSTRAP_SERVERS)

            while True:
                self.open_consumer(consumer)
        except Exception as e:
            logger.error('Consumer error', exc_info=True)
            if consumer:
                consumer.close()

    def open_consumer(self, consumer):
        try:
            for msg in consumer:
                line = msg.value.decode('utf-8')
                process_line(line)
        except Exception as e:
            self.stderr.write('error process {}'.format(e))
            logger.error('Consumer error', exc_info=True)
