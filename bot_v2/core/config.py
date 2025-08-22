"""
Enhanced configuration management for Yemen Net Bot
"""

import os
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pathlib import Path

@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "yemen_net.db"
    timeout: float = 30.0
    check_same_thread: bool = False
    max_connections: int = 10
    connection_timeout: float = 5.0

@dataclass
class BotConfig:
    """Bot configuration"""
    token: str = ""
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    webhook_cert: Optional[str] = None
    webhook_key: Optional[str] = None
    
    # Rate limiting
    rate_limit_per_user: int = 10
    rate_limit_per_minute: int = 60
    rate_limit_burst: int = 20
    
    # Logging
    log_level: str = "INFO"
    log_file: str = "bot.log"
    log_max_size: int = 10 * 1024 * 1024  # 10MB
    log_backup_count: int = 5
    
    # Security
    admin_user_ids: List[int] = field(default_factory=list)
    allowed_users: List[int] = field(default_factory=list)
    maintenance_mode: bool = False
    
    # Features
    enable_notifications: bool = True
    enable_analytics: bool = True
    enable_backup: bool = True
    backup_interval_hours: int = 24

@dataclass
class PaymentConfig:
    """Payment configuration"""
    min_transfer_amount: float = 1.0
    max_transfer_amount: float = 10000.0
    transfer_fee_percent: float = 0.5
    min_balance_for_transfer: float = 10.0
    
    # Payment providers
    enable_bank_transfer: bool = True
    enable_crypto: bool = False
    enable_cash: bool = True

@dataclass
class NotificationConfig:
    """Notification configuration"""
    enable_telegram: bool = True
    enable_email: bool = False
    enable_sms: bool = False
    
    # Telegram notifications
    admin_chat_id: Optional[int] = None
    support_chat_id: Optional[int] = None
    
    # Email settings
    smtp_server: str = ""
    smtp_port: int = 587
    smtp_username: str = ""
    smtp_password: str = ""

class ConfigManager:
    """Configuration manager with environment variable support"""
    
    def __init__(self):
        self.bot = BotConfig()
        self.database = DatabaseConfig()
        self.payment = PaymentConfig()
        self.notification = NotificationConfig()
        self._load_from_env()
        self._load_from_file()
    
    def _load_from_env(self):
        """Load configuration from environment variables"""
        # Bot settings
        if os.getenv('BOT_TOKEN'):
            self.bot.token = os.getenv('BOT_TOKEN')
        
        if os.getenv('BOT_WEBHOOK_URL'):
            self.bot.webhook_url = os.getenv('BOT_WEBHOOK_URL')
        
        if os.getenv('BOT_LOG_LEVEL'):
            self.bot.log_level = os.getenv('BOT_LOG_LEVEL')
        
        # Database settings
        if os.getenv('DB_PATH'):
            self.database.path = os.getenv('DB_PATH')
        
        # Admin users
        admin_ids = os.getenv('ADMIN_USER_IDS')
        if admin_ids:
            try:
                self.bot.admin_user_ids = [int(x.strip()) for x in admin_ids.split(',')]
            except ValueError:
                pass
    
    def _load_from_file(self):
        """Load configuration from config file if exists"""
        config_file = Path("config.yaml")
        if config_file.exists():
            try:
                import yaml
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = yaml.safe_load(f)
                    self._apply_config_data(config_data)
            except Exception as e:
                logging.warning(f"Failed to load config file: {e}")
    
    def _apply_config_data(self, config_data: Dict[str, Any]):
        """Apply configuration data from file"""
        if 'bot' in config_data:
            for key, value in config_data['bot'].items():
                if hasattr(self.bot, key):
                    setattr(self.bot, key, value)
        
        if 'database' in config_data:
            for key, value in config_data['database'].items():
                if hasattr(self.database, key):
                    setattr(self.database, key, value)
        
        if 'payment' in config_data:
            for key, value in config_data['payment'].items():
                if hasattr(self.payment, key):
                    setattr(self.payment, key, value)
        
        if 'notification' in config_data:
            for key, value in config_data['notification'].items():
                if hasattr(self.notification, key):
                    setattr(self.notification, key, value)
    
    def validate(self) -> List[str]:
        """Validate configuration and return list of errors"""
        errors = []
        
        if not self.bot.token:
            errors.append("BOT_TOKEN is required")
        
        if self.bot.webhook_url and not self.bot.webhook_cert:
            errors.append("Webhook certificate is required when using webhook")
        
        if self.database.path and not Path(self.database.path).parent.exists():
            errors.append(f"Database directory does not exist: {Path(self.database.path).parent}")
        
        return errors
    
    def get_database_url(self) -> str:
        """Get database connection string"""
        return f"sqlite:///{self.database.path}"
    
    def is_admin(self, user_id: int) -> bool:
        """Check if user is admin"""
        return user_id in self.bot.admin_user_ids
    
    def is_allowed_user(self, user_id: int) -> bool:
        """Check if user is allowed to use bot"""
        if not self.bot.allowed_users:
            return True
        return user_id in self.bot.allowed_users

# Global configuration instance
config = ConfigManager()

# Emojis and constants
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'money': '💰',
    'card': '💳',
    'user': '👤',
    'admin': '👑',
    'settings': '⚙️',
    'stats': '📊',
    'transfer': '💸',
    'wallet': '👛',
    'notification': '🔔',
    'lock': '🔒',
    'unlock': '🔓',
    'refresh': '🔄',
    'download': '⬇️',
    'upload': '⬆️',
    'search': '🔍',
    'filter': '🔧',
    'calendar': '📅',
    'clock': '⏰',
    'check': '☑️',
    'cross': '❌',
    'star': '⭐',
    'fire': '🔥',
    'rocket': '🚀',
    'trophy': '🏆',
    'medal': '🥇',
    'gift': '🎁',
    'party': '🎉'
}

QUICK_COMMANDS = {
    'start': 'بدء استخدام البوت',
    'help': 'عرض المساعدة',
    'wallet': 'عرض المحفظة',
    'profile': 'الملف الشخصي',
    'settings': 'الإعدادات',
    'support': 'الدعم الفني'
}

USER_ROLES = {
    'user': 'مستخدم عادي',
    'agent': 'وكيل',
    'supplier': 'مورد',
    'admin': 'مدير',
    'super_admin': 'مدير عام'
}

PERMISSIONS = {
    'user': ['view_profile', 'view_wallet', 'make_transfer', 'view_transactions'],
    'agent': ['user_permissions', 'view_commissions', 'view_sales', 'upload_cards'],
    'supplier': ['agent_permissions', 'manage_networks', 'view_supplier_stats'],
    'admin': ['supplier_permissions', 'manage_users', 'view_admin_panel', 'system_settings'],
    'super_admin': ['admin_permissions', 'manage_admins', 'system_maintenance', 'full_access']
}