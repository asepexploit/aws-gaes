"""Centralized logging setup for visual_autoclicker."""
from __future__ import annotations

import logging
import sys
from pathlib import Path
from typing import Any, Dict


def setup_logger(config: Dict[str, Any]) -> logging.Logger:
    log_cfg = config.get("logging", {})
    level_name = log_cfg.get("level", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    fmt = log_cfg.get("format", "%(asctime)s [%(levelname)s] %(name)s: %(message)s")
    formatter = logging.Formatter(fmt)

    logger = logging.getLogger("visual_autoclicker")
    logger.setLevel(level)
    logger.handlers.clear()

    if log_cfg.get("console", True):
        ch = logging.StreamHandler(sys.stdout)
        ch.setLevel(level)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

    log_file = log_cfg.get("file")
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(level)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

    logger.propagate = False
    return logger


def get_logger(name: str = "visual_autoclicker") -> logging.Logger:
    return logging.getLogger(name)
