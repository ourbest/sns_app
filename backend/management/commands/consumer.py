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
        consumer = KafkaConsumer(settings.WEIZHAN_LOG_TOPIC, group_id='tuiguang',
                                 bootstrap_servers=settings.BOOTSTRAP_SERVERS)
        try:
            while True:
                self.open_consumer(consumer)
        except Exception as e:
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
                    except Exception:
                        logger.error('Error process line %s' % line, exc_info=True)
