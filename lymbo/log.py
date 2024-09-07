from enum import Enum
from functools import cache
import logging
import os
from pathlib import Path
from typing import Union
import sys

from lymbo.env import LYMBO_LOG_LEVEL
from lymbo.env import LYMBO_LOG_PATH


class LogLevel(Enum):
    NOTSET = "notset"
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


def set_env_for_logging(log_level: LogLevel, path: Union[Path, None]):

    os.environ[LYMBO_LOG_LEVEL] = str(
        {
            "NOTSET": logging.NOTSET,
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
            "CRITICAL": logging.CRITICAL,
        }[log_level.value.upper()]
    )

    if path:
        os.environ[LYMBO_LOG_PATH] = str(path)

@cache
def logger() -> logging.Logger:

    logger = logging.getLogger()
    log_level = int(os.environ.get(LYMBO_LOG_LEVEL, logging.WARNING))
    logger.setLevel(log_level)

    formatter = logging.Formatter(
        "¤ %(asctime)s.%(msecs)03d (%(process)d) [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    if LYMBO_LOG_PATH in os.environ:
        file_handler = logging.FileHandler(os.environ[LYMBO_LOG_PATH])
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    return logger


def trace_call(fnc):
    
    def wrapper(*args, **kwargs):

        log_level = int(os.environ.get(LYMBO_LOG_LEVEL, logging.WARNING))

        if log_level == logging.DEBUG:
            logger().debug(f"{fnc.__name__} | begin args={args} kwargs={kwargs}")
        
        r = fnc(*args, **kwargs)

        if log_level == logging.DEBUG:
            logger().debug(f"{fnc.__name__} |end r={r}")

        return r
    
    return wrapper    