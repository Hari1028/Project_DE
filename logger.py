import logging
from config import LOG_FILE

def setup_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(module)s - %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, mode="a"), # Append mode
            logging.StreamHandler() # Also prints to console
        ]
    )
    return logging.getLogger(__name__)

logger = setup_logger()