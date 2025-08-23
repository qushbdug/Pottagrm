"""
Enhanced configuration for Yemen Net Bot v2
Replaces print() statements with proper logging
"""

import os
import logging
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class BotConfig:
    """Enhanced bot configuration with proper logging"""
    
    def __init__(self):
        self._setup_logging()
        self._load_config()
        self._validate_config()
    
    def _setup_logging(self):
        """Setup comprehensive logging configuration"""
        # Create logs directory if it doesn't exist
        os.makedirs('logs', exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/bot.log', encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger('YemenNetBot')
        self.logger.info("Logging system initialized successfully")
    
    def _load_config(self):
        """Load configuration from environment variables"""
        # Bot Configuration
        self.BOT_TOKEN = os.getenv('BOT_TOKEN')
        if not self.BOT_TOKEN:
            self.logger.error("BOT_TOKEN not found in environment variables")
            raise ValueError("BOT_TOKEN is required")
        
        # Database Configuration
        self.DB_PATH = os.getenv('DB_PATH', 'yemen_net.db')
        self.DB_TIMEOUT = int(os.getenv('DB_TIMEOUT', '30'))
        self.DB_MAX_CONNECTIONS = int(os.getenv('DB_MAX_CONNECTIONS', '10'))
        
        # Bot Settings
        self.BOT_NAME = os.getenv('BOT_NAME', 'Yemen Net Bot')
        self.BOT_USERNAME = os.getenv('BOT_USERNAME', 'yemen_net_bot')
        self.ADMIN_USER_ID = int(os.getenv('ADMIN_USER_ID', '0'))
        
        # Rate Limiting
        self.RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', '30'))
        self.RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', '60'))
        
        # Security
        self.SESSION_TIMEOUT = int(os.getenv('SESSION_TIMEOUT', '3600'))
        self.MAX_LOGIN_ATTEMPTS = int(os.getenv('MAX_LOGIN_ATTEMPTS', '5'))
        
        # Performance
        self.CACHE_TTL = int(os.getenv('CACHE_TTL', '300'))
        self.MAX_CONCURRENT_REQUESTS = int(os.getenv('MAX_CONCURRENT_REQUESTS', '100'))
        
        # Notification
        self.ENABLE_NOTIFICATIONS = os.getenv('ENABLE_NOTIFICATIONS', 'true').lower() == 'true'
        self.NOTIFICATION_INTERVAL = int(os.getenv('NOTIFICATION_INTERVAL', '300'))
        
        # Monitoring
        self.ENABLE_MONITORING = os.getenv('ENABLE_MONITORING', 'true').lower() == 'true'
        self.MONITORING_INTERVAL = int(os.getenv('MONITORING_INTERVAL', '60'))
        
        # Backup
        self.ENABLE_AUTO_BACKUP = os.getenv('ENABLE_AUTO_BACKUP', 'true').lower() == 'true'
        self.BACKUP_INTERVAL = int(os.getenv('BACKUP_INTERVAL', '86400'))  # 24 hours
        
        self.logger.info("Configuration loaded successfully")
    
    def _validate_config(self):
        """Validate configuration values"""
        validation_errors = []
        
        if not self.BOT_TOKEN:
            validation_errors.append("BOT_TOKEN is required")
        
        if self.DB_TIMEOUT <= 0:
            validation_errors.append("DB_TIMEOUT must be positive")
        
        if self.RATE_LIMIT_REQUESTS <= 0:
            validation_errors.append("RATE_LIMIT_REQUESTS must be positive")
        
        if self.RATE_LIMIT_WINDOW <= 0:
            validation_errors.append("RATE_LIMIT_WINDOW must be positive")
        
        if validation_errors:
            error_msg = "Configuration validation failed: " + "; ".join(validation_errors)
            self.logger.error(error_msg)
            raise ValueError(error_msg)
        
        self.logger.info("Configuration validation passed")
    
    def get_database_url(self) -> str:
        """Get database connection string"""
        return f"sqlite:///{self.DB_PATH}"
    
    def is_production(self) -> bool:
        """Check if running in production mode"""
        return os.getenv('ENVIRONMENT', 'development').lower() == 'production'
    
    def get_log_level(self) -> str:
        """Get log level based on environment"""
        if self.is_production():
            return 'WARNING'
        return 'INFO'
    
    def update_config(self, key: str, value: Any) -> None:
        """Update configuration value dynamically"""
        if hasattr(self, key):
            old_value = getattr(self, key)
            setattr(self, key, value)
            self.logger.info(f"Configuration updated: {key} = {old_value} -> {value}")
        else:
            self.logger.warning(f"Attempted to update non-existent config key: {key}")
    
    def get_config_summary(self) -> Dict[str, Any]:
        """Get configuration summary for monitoring"""
        return {
            'bot_name': self.BOT_NAME,
            'db_path': self.DB_PATH,
            'rate_limit_requests': self.RATE_LIMIT_REQUESTS,
            'rate_limit_window': self.RATE_LIMIT_WINDOW,
            'cache_ttl': self.CACHE_TTL,
            'enable_notifications': self.ENABLE_NOTIFICATIONS,
            'enable_monitoring': self.ENABLE_MONITORING,
            'enable_auto_backup': self.ENABLE_AUTO_BACKUP
        }

# Global configuration instance
config = BotConfig()