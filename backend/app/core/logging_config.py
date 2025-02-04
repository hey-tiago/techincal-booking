import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# Configure logging format
log_format = logging.Formatter(
    "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
    datefmt='%Y-%m-%d'
)

def setup_logger(name: str) -> logging.Logger:
    """
    Set up a logger with both file and console handlers.
    
    Args:
        name: The name of the logger (typically __name__)
        
    Returns:
        logging.Logger: Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    # Prevent adding handlers multiple times
    if not logger.handlers:
        # Create file handler
        file_handler = RotatingFileHandler(
            logs_dir / f"{name.split('.')[-1]}.log",
            maxBytes=1024 * 1024,  # 1MB
            backupCount=5
        )
        file_handler.setFormatter(log_format)
        logger.addHandler(file_handler)

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(log_format)
        logger.addHandler(console_handler)

    return logger