#!/usr/bin/env python3
"""
Structured logging configuration for the Pro Telegram Bot.
- Uses a consistent, minimal format with timestamp, level, logger name, and message
- Exposes a setup function to initialize logging according to settings
"""

import logging
from typing import Optional


def setup_logging(level: str = "INFO") -> None:
    """Initialize root logging configuration.

    Args:
        level: Logging level name (e.g., DEBUG, INFO, WARNING, ERROR).
    """
    level_value = getattr(logging, level.upper(), logging.INFO)

    # Avoid duplicate handlers if called multiple times
    root = logging.getLogger()
    if root.handlers:
        for h in root.handlers:
            root.removeHandler(h)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    root.setLevel(level_value)
    root.addHandler(handler)