import logging
import sys
from pythonjsonlogger import jsonlogger
from app.config import settings

class CustomJsonFormatter(jsonlogger.JsonFormatter):
    def add_fields(self, log_record, record, message_dict):
        super(CustomJsonFormatter, self).add_fields(log_record, record, message_dict)
        if not log_record.get('@timestamp'):
             log_record['@timestamp'] = self.formatTime(record)
        if log_record.get('level'):
            log_record['level'] = log_record['level'].upper()
        else:
            log_record['level'] = record.levelname

def configure_logging():
    logger = logging.getLogger()
    logHandler = logging.StreamHandler(sys.stdout)
    formatter = CustomJsonFormatter(
        "%(timestamp)s %(level)s %(name)s %(message)s %(request_id)s %(trace_id)s",
        rename_fields={"levelname": "level", "asctime": "@timestamp"}
    )
    logHandler.setFormatter(formatter)
    logger.addHandler(logHandler)
    logger.setLevel(settings.log_level)
