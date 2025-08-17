#!/usr/bin/env python3
import os
import pytest

from app.config import Settings


def test_settings_from_env(monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123:ABC")
    monkeypatch.setenv("ADMIN_USER_IDS", "1, 2,foo,3")
    s = Settings.from_env()
    assert s.bot_token == "123:ABC"
    assert s.admin_user_ids == [1, 2, 3]
    assert s.log_level == "INFO"


def test_missing_token(monkeypatch):
    monkeypatch.delenv("BOT_TOKEN", raising=False)
    with pytest.raises(RuntimeError):
        Settings.from_env()