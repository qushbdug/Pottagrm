#!/usr/bin/env python3
"""
Tests for configuration management.
"""

import unittest
import os
from unittest.mock import patch, MagicMock
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from core.config import ConfigManager, DatabaseConfig, BotConfig, BusinessConfig


class TestConfigManager(unittest.TestCase):
    """Test configuration manager functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Clear environment variables
        self.env_vars = {}
        for key in ['BOT_TOKEN', 'DB_PATH', 'CARD_COMMISSION_RATE']:
            if key in os.environ:
                self.env_vars[key] = os.environ[key]
                del os.environ[key]
    
    def tearDown(self):
        """Clean up test environment."""
        # Restore environment variables
        for key, value in self.env_vars.items():
            os.environ[key] = value
    
    @patch('core.config.load_dotenv')
    def test_config_manager_initialization(self, mock_load_dotenv):
        """Test ConfigManager initialization."""
        # Set required environment variable
        os.environ['BOT_TOKEN'] = 'test_token_123'
        
        config = ConfigManager()
        
        # Verify dotenv was loaded
        mock_load_dotenv.assert_called_once()
        
        # Verify configurations were created
        self.assertIsInstance(config.database, DatabaseConfig)
        self.assertIsInstance(config.bot, BotConfig)
        self.assertIsInstance(config.business, BusinessConfig)
    
    def test_missing_bot_token(self):
        """Test error when BOT_TOKEN is missing."""
        with self.assertRaises(EnvironmentError) as context:
            ConfigManager()
        
        self.assertIn("BOT_TOKEN is required", str(context.exception))
    
    def test_database_config_defaults(self):
        """Test database configuration defaults."""
        os.environ['BOT_TOKEN'] = 'test_token_123'
        
        config = ConfigManager()
        
        self.assertEqual(config.database.timeout, 30.0)
        self.assertEqual(config.database.journal_mode, "WAL")
        self.assertEqual(config.database.synchronous, "NORMAL")
        self.assertEqual(config.database.cache_size, 1000)
        self.assertEqual(config.database.temp_store, "memory")
    
    def test_bot_config_values(self):
        """Test bot configuration values."""
        os.environ['BOT_TOKEN'] = 'test_token_123'
        os.environ['WEBHOOK_URL'] = 'https://example.com/webhook'
        os.environ['WEBHOOK_PORT'] = '8080'
        
        config = ConfigManager()
        
        self.assertEqual(config.bot.token, 'test_token_123')
        self.assertEqual(config.bot.webhook_url, 'https://example.com/webhook')
        self.assertEqual(config.bot.webhook_port, 8080)
        self.assertEqual(config.bot.webhook_listen, '0.0.0.0')
    
    def test_business_config_defaults(self):
        """Test business configuration defaults."""
        os.environ['BOT_TOKEN'] = 'test_token_123'
        
        config = ConfigManager()
        
        self.assertEqual(config.business.card_commission_rate, 0.10)
        self.assertEqual(config.business.agent_commission_rate, 0.05)
        self.assertEqual(config.business.max_transfer_amount, 10000.0)
        self.assertEqual(config.business.min_transfer_amount, 1.0)
    
    def test_business_config_custom_values(self):
        """Test business configuration with custom values."""
        os.environ['BOT_TOKEN'] = 'test_token_123'
        os.environ['CARD_COMMISSION_RATE'] = '0.15'
        os.environ['AGENT_COMMISSION_RATE'] = '0.08'
        os.environ['MAX_TRANSFER_AMOUNT'] = '50000.0'
        
        config = ConfigManager()
        
        self.assertEqual(config.business.card_commission_rate, 0.15)
        self.assertEqual(config.business.agent_commission_rate, 0.08)
        self.assertEqual(config.business.max_transfer_amount, 50000.0)


class TestConstants(unittest.TestCase):
    """Test configuration constants."""
    
    def test_account_types(self):
        """Test account types constants."""
        from core.config import ACCOUNT_TYPES
        
        expected_types = ['asset', 'liability', 'equity', 'revenue', 'expense']
        for account_type in expected_types:
            self.assertIn(account_type, ACCOUNT_TYPES)
    
    def test_user_roles(self):
        """Test user roles constants."""
        from core.config import USER_ROLES
        
        expected_roles = ['customer', 'agent', 'supplier', 'admin', 'super_admin']
        for role in expected_roles:
            self.assertIn(role, USER_ROLES)
    
    def test_emojis(self):
        """Test emojis constants."""
        from core.config import EMOJIS
        
        expected_emojis = ['success', 'error', 'warning', 'info', 'loading']
        for emoji in expected_emojis:
            self.assertIn(emoji, EMOJIS)
    
    def test_conversation_states(self):
        """Test conversation states constants."""
        from core.config import CONVERSATION_STATES
        
        expected_states = ['GET_FULL_NAME', 'GET_PHONE', 'CHOOSE_ROLE']
        for state in expected_states:
            self.assertIn(state, CONVERSATION_STATES)


if __name__ == '__main__':
    unittest.main()