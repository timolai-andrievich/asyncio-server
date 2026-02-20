import logging
import sys

from settings import get_settings


settings = get_settings()

logger = logging.getLogger("asyncio_server")
logger.setLevel(logging.DEBUG)

identity_formatter = logging.Formatter("%(message)s")
stdout_handler = logging.StreamHandler(sys.stdout)
file_handler = logging.FileHandler(settings.log_file)

logger.addHandler(stdout_handler)
logger.addHandler(file_handler)


def get_logger():
    return logger
