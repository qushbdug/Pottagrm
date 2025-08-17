#!/usr/bin/env python3
"""
Configuration management for the Pro Telegram Bot.
- Loads settings from environment variables (optionally from a .env file if present)
- Validates critical configuration (e.g., BOT_TOKEN)
- Provides a single source of truth for application-wide settings
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import List, Optional

# Optional dotenv support for local development
try:
    from dotenv import load_dotenv  # type: ignore
    _DOTENV_AVAILABLE = True
except Exception:
    _DOTENV_AVAILABLE = False


@dataclass(frozen=True)
class Settings:
    """Strongly-typed application settings.

    Attributes:
        bot_token: Telegram bot token (REQUIRED).
        admin_user_ids: Optional list of Telegram user IDs who have admin privileges.
        log_level: Python logging level name (e.g., INFO, DEBUG).
    """

    bot_token: str
    admin_user_ids: List[int]
    log_level: str = "INFO"

    @staticmethod
    def _parse_admin_ids(raw: Optional[str]) -> List[int]:
        if not raw:
            return []
        ids: List[int] = []
        for chunk in raw.split(","):
            chunk = chunk.strip()
            if not chunk:
                continue
            try:
                ids.append(int(chunk))
            except ValueError:
                # Ignore invalid entries silently to avoid startup failure
                continue
        return ids

    @classmethod
    def from_env(cls) -> Settings:
        """Load settings from environment variables, optionally via .env.

        Raises:
            RuntimeError: If required settings are missing or invalid.
        """
        if _DOTENV_AVAILABLE:
            # Load .env if present; do not fail if missing
            load_dotenv(override=False)

        bot_token = os.getenv("BOT_TOKEN", "").strip()
        if not bot_token:
            raise RuntimeError(
                "Missing BOT_TOKEN in environment. Set BOT_TOKEN or create a .env file."
            )

        admin_ids_raw = os.getenv("ADMIN_USER_IDS", "").strip()
        log_level = os.getenv("LOG_LEVEL", "INFO").strip().upper() or "INFO"

        return cls(
            bot_token=bot_token,
            admin_user_ids=cls._parse_admin_ids(admin_ids_raw),
            log_level=log_level,
        )