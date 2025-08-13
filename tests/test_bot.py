#!/usr/bin/env python3
"""
Basic tests for Yemen Net Bot
"""

import pytest
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_imports():
    """Test that all required modules can be imported"""
    try:
        from main_bot import YemenNetBot
        assert YemenNetBot is not None
    except ImportError as e:
        pytest.fail(f"Failed to import YemenNetBot: {e}")

def test_config():
    """Test that config can be loaded"""
    try:
        from bot.config import BOT_TOKEN, QUICK_COMMANDS
        assert QUICK_COMMANDS is not None
    except ImportError as e:
        pytest.fail(f"Failed to import config: {e}")

def test_database_connection():
    """Test database connection"""
    try:
        from bot.database.connection import db_manager
        assert db_manager is not None
    except ImportError as e:
        pytest.fail(f"Failed to import database manager: {e}")

if __name__ == "__main__":
    pytest.main([__file__])