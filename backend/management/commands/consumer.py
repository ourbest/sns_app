import time

from django.conf import settings
from django.core.management import BaseCommand
from kafka import KafkaConsumer

from backend.log_parser import process_line
from backend.loggs import logger


class Command(BaseCommand):
    def __init__(self):
        super().__init__(stdout=None, stderr=None, no_color=False)
        self.total_records = 0

    def handle(self, *args, **options):

        while True:
            self._consume()

    def _consume(self):
        begin_time = time.time()
        last_records = self.total_records
        consumer = KafkaConsumer(settings.WEIZHAN_LOG_TOPIC, group_id='tuiguang',
                                 bootstrap_servers=settings.BOOTSTRAP_SERVERS)
        try:
            while True:
                self.open_consumer(consumer)
                if time.time() - begin_time > 60 * 30:
                    delta = self.total_records - last_records
                    if delta == 0:
                        logger.warn('No record in 30 mins, sth wrong?')
                    begin_time = time.time()
                    last_records = self.total_records
        except:
            logger.error('Consumer error', exc_info=True)
            consumer.close()

    def open_consumer(self, consumer):
        messages = consumer.poll(500)
        if messages:
            for topic_messages in messages.values():
                for message in topic_messages:
                    line = message.value.decode('utf-8')
                    try:
                        process_line(line)
                        self.total_records += 1
                        if self.total_records % 5000 == 0:
                            logger.info('Process %s lines' % self.total_records)

                    except Exception:
                        logger.error('Error process line %s' % line, exc_info=True)
