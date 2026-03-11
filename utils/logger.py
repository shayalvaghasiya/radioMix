# d:\PROJECTS\RadioMix\utils\logger.py
import logging
import os
from logging.handlers import RotatingFileHandler
from config.settings import settings

def setup_logging():
    """Configures logging to file and console."""
    log_dir = os.path.dirname(settings.log_path)
    os.makedirs(log_dir, exist_ok=True)

    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # File handler for logging to a rotating file
    file_handler = RotatingFileHandler(
        settings.log_path, maxBytes=5*1024*1024, backupCount=2, encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.INFO)

    # Console handler for displaying logs in the terminal (useful for debugging)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.DEBUG)

    # Configure the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Clear existing handlers to avoid duplicates
    if root_logger.hasHandlers():
        root_logger.handlers.clear()
        
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)

    logging.info("Logging initialized. Log file at: %s", settings.log_path)
