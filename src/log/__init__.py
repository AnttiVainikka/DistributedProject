import logging
import logging.config

logging.config.fileConfig('src/log/logging.conf')

getLogger = logging.getLogger
