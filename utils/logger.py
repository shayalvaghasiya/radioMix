import logging
import os
from logging.handlers import RotatingFileHandler
from config.settings import settings

def setup_logging():
    log_dir = os.path.dirname(settings.log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    logging.basicConfig(
        level=settings.log_level.upper(),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            RotatingFileHandler(settings.log_file, maxBytes=1048576, backupCount=5),
            logging.StreamHandler()
        ]
    )