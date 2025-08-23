"""
Core configuration module for Yemen Net Bot
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path

class Config:
    """Configuration management with environment variables and defaults"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self._load_config()
    
    def _load_config(self):
        """Load configuration from environment variables and defaults"""
        # Bot configuration
        self.BOT_TOKEN = os.getenv('BOT_TOKEN') or self._get_bot_token_from_file()
        if not self.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not found in environment or config files")
        
        # Database configuration
        self.DATABASE_PATH = os.getenv('DATABASE_PATH', 'yemen_net.db')
        self.DATABASE_POOL_SIZE = int(os.getenv('DATABASE_POOL_SIZE', '10'))
        self.DATABASE_TIMEOUT = int(os.getenv('DATABASE_TIMEOUT', '30'))
        
        # Rate limiting configuration
        self.RATE_LIMIT_ENABLED = os.getenv('RATE_LIMIT_ENABLED', 'true').lower() == 'true'
        self.RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '10'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        
        # Cache configuration
        self.CACHE_ENABLED = os.getenv('CACHE_ENABLED', 'true').lower() == 'true'
        self.CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))  # 5 minutes default
        self.CACHE_MAX_SIZE = int(os.getenv('CACHE_MAX_SIZE', '1000'))
        
        # Performance configuration
        self.MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '50'))
        self.REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))
        
        # Logging configuration
        self.LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
        self.LOG_FILE = os.getenv('LOG_FILE', 'bot.log')
        self.LOG_MAX_SIZE = int(os.getenv('LOG_MAX_SIZE', '10485760'))  # 10MB
        self.LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))
        
        # Security configuration
        self.ADMIN_USER_IDS = self._parse_admin_ids()
        self.ALLOWED_FILE_TYPES = ['xlsx', 'csv', 'txt', 'pdf']
        self.MAX_FILE_SIZE = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
        
        # Business configuration
        self.CURRENCY_SYMBOL = os.getenv('CURRENCY_SYMBOL', 'ر.ي')
        self.TIMEZONE = os.getenv('TIMEZONE', 'Asia/Aden')
        self.DEFAULT_LANGUAGE = os.getenv('DEFAULT_LANGUAGE', 'ar')
        
        # Feature flags
        self.ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
        self.ENABLE_ANALYTICS = os.getenv('ENABLE_ANALYTICS', 'true').lower() == 'true'
        self.ENABLE_BACKUP = os.getenv('ENABLE_BACKUP', 'true').lower() == 'true'
        
        # Emojis configuration
        self.EMOJIS = {
            'success': '✅',
            'error': '❌',
            'warning': '⚠️',
            'info': 'ℹ️',
            'money': '💰',
            'card': '💳',
            'user': '👤',
            'admin': '👨‍💼',
            'network': '🌐',
            'stats': '📊',
            'history': '📋',
            'settings': '⚙️',
            'help': '❓',
            'back': '🔙',
            'loading': '⏳',
            'done': '✔️'
        }
        
        # User roles and permissions
        self.USER_ROLES = {
            'admin': 'مدير النظام',
            'agent': 'وكيل',
            'supplier': 'مورد',
            'user': 'مستخدم'
        }
        
        self.PERMISSIONS = {
            'admin': ['*'],  # All permissions
            'agent': ['view_reports', 'manage_users', 'process_payments'],
            'supplier': ['upload_cards', 'view_sales', 'manage_networks'],
            'user': ['buy_cards', 'view_balance', 'view_history']
        }
        
        # Quick commands configuration
        self.QUICK_COMMANDS = {
            'wallet': 'المحفظة 💰',
            'buy': 'شراء بطاقة 💳',
            'networks': 'الشبكات 🌐',
            'help': 'المساعدة ❓',
            'profile': 'الملف الشخصي 👤'
        }
        
        self.logger.info("✅ Configuration loaded successfully")
    
    def _get_bot_token_from_file(self) -> Optional[str]:
        """Try to get bot token from configuration files"""
        config_files = [
            'bot_modules/config.py',
            'config.py',
            '.env'
        ]
        
        for config_file in config_files:
            if os.path.exists(config_file):
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Look for BOT_TOKEN in various formats
                        for line in content.split('\n'):
                            if 'BOT_TOKEN' in line and '=' in line:
                                # Extract token from various formats
                                if line.strip().startswith('#'):
                                    continue
                                token = line.split('=')[1].strip().strip('"\'')
                                if token and len(token) > 10:
                                    return token
                except Exception as e:
                    self.logger.warning(f"Error reading config file {config_file}: {e}")
        
        return None
    
    def _parse_admin_ids(self) -> list:
        """Parse admin user IDs from environment"""
        admin_ids_str = os.getenv('ADMIN_USER_IDS', '')
        if admin_ids_str:
            try:
                return [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
            except ValueError as e:
                self.logger.warning(f"Error parsing admin IDs: {e}")
        return []
    
    def get_database_url(self) -> str:
        """Get database URL/path"""
        return f"sqlite:///{self.DATABASE_PATH}"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.ADMIN_USER_IDS
    
    def has_permission(self, user_role: str, permission: str) -> bool:
        """Check if user role has specific permission"""
        if user_role not in self.PERMISSIONS:
            return False
        
        role_permissions = self.PERMISSIONS[user_role]
        return '*' in role_permissions or permission in role_permissions
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary (excluding sensitive data)"""
        return {
            'database_path': self.DATABASE_PATH,
            'rate_limit_enabled': self.RATE_LIMIT_ENABLED,
            'cache_enabled': self.CACHE_ENABLED,
            'log_level': self.LOG_LEVEL,
            'timezone': self.TIMEZONE,
            'currency_symbol': self.CURRENCY_SYMBOL,
            'feature_flags': {
                'notifications': self.ENABLE_NOTIFICATIONS,
                'analytics': self.ENABLE_ANALYTICS,
                'backup': self.ENABLE_BACKUP
            }
        }


# Global configuration instance
config = Config()