import logging

from dependency_injector import resources
from ml.common.elk_logstash_logging.handler import get_elk_logstash_handler


class LoggerResource(resources.Resource):
    def init(self, logger_name: str, logger_level: str, logstash_host: str,
             logstash_port: int) -> logging.Logger:
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        handler = get_elk_logstash_handler(
            logstash_host=logstash_host,
            logstash_port=logstash_port
        )
        logger.addHandler(handler)

        return logger
