#logging_config.py
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging(level=logging.DEBUG):
    # Get the absolute path of the directory where the current script is located
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # Define the log directory relative to the base_dir
    log_dir = os.path.join(base_dir, 'logs')
    os.makedirs(log_dir, exist_ok=True)  # Create the log directory if it doesn't exist

    # Define the full path to the log file
    log_file = os.path.join(log_dir, 'secure_chat.log')

    # Initialize a logger with the name 'secure_chat'
    logger = logging.getLogger('secure_chat')
    logger.setLevel(level)

    #  Rotating file handler with UTF-8 encoding for emoji support
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10**6,
        backupCount=5,
        encoding='utf-8'  # This allows logging emojis!
    )
    file_handler.setLevel(level)

    # Console handler (stdout)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)

    # Log format
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add both handlers
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
