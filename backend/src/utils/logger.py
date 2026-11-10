"""统一日志（stdout，docker logs 可读）。"""
from __future__ import annotations

import logging
import os
import sys

_LEVEL = os.environ.get("LOG_LEVEL", "INFO").upper()
_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    logger.setLevel(_LEVEL)
    logger.propagate = False
    return logger


def log_event(event: str, **fields: object) -> None:
    logger = get_logger("crawlfq.event")
    payload = " ".join(f"{key}={value}" for key, value in fields.items())
    logger.info("%s %s", event, payload)
