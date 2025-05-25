import logging
import sys
from datetime import datetime

class CogLogger:
    """Modified version for more transparent usage"""
    def __init__(self, name: str, level: int = logging.INFO):
        self._logger = logging.getLogger(f"bronxbot.{name}")
        self._logger.setLevel(level)
        
        if not self._logger.handlers:
            handler = logging.StreamHandler(sys.stdout)
            formatter = ColoredFormatter(
                '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            self._logger.addHandler(handler)
    
    # Delegate logging methods to make usage cleaner
    def info(self, msg, *args, **kwargs):
        self._logger.info(msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._logger.error(msg, *args, **kwargs)

class ColoredFormatter(logging.Formatter):
    """Custom formatter that adds colors to log levels"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m'  # Magenta
    }
    RESET = '\033[0m'
    
    def format(self, record):
        levelname = record.levelname
        if levelname in self.COLORS:
            record.levelname = f"{self.COLORS[levelname]}{levelname}{self.RESET}"
        
        return super().format(record)