"""
Comprehensive Configuration System for Yemen Net Bot
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum

from ..core.exceptions import ConfigurationException, MissingConfiguration, InvalidConfiguration


class LogLevel(Enum):
    """Log level enumeration"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Environment(Enum):
    """Environment enumeration"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


@dataclass
class DatabaseConfig:
    """Database configuration"""
    path: str = "yemen_net.db"
    max_connections: int = 20
    timeout: float = 30.0
    backup_interval_hours: int = 24
    optimize_interval_hours: int = 168  # 1 week
    
    def __post_init__(self):
        if self.max_connections < 1:
            raise InvalidConfiguration("max_connections must be at least 1")
        if self.timeout <= 0:
            raise InvalidConfiguration("timeout must be positive")


@dataclass
class TelegramConfig:
    """Telegram bot configuration"""
    token: str
    webhook_url: Optional[str] = None
    webhook_port: int = 8443
    webhook_path: str = "/webhook"
    max_connections: int = 40
    
    def __post_init__(self):
        if not self.token:
            raise MissingConfiguration("Telegram bot token is required")
        if self.max_connections < 1 or self.max_connections > 100:
            raise InvalidConfiguration("max_connections must be between 1 and 100")


@dataclass
class SecurityConfig:
    """Security configuration"""
    enable_rate_limiting: bool = True
    max_login_attempts: int = 3
    login_cooldown_minutes: int = 15
    session_timeout_hours: int = 24
    require_phone_verification: bool = True
    enable_2fa: bool = False
    password_min_length: int = 8
    jwt_secret_key: Optional[str] = None
    jwt_expiry_hours: int = 24
    
    def __post_init__(self):
        if self.max_login_attempts < 1:
            raise InvalidConfiguration("max_login_attempts must be at least 1")
        if self.password_min_length < 4:
            raise InvalidConfiguration("password_min_length must be at least 4")


@dataclass
class PaymentConfig:
    """Payment system configuration"""
    enable_payments: bool = True
    min_transfer_amount: float = 10.0
    max_transfer_amount: float = 100000.0
    commission_rate: float = 0.02
    auto_withdrawal_enabled: bool = False
    withdrawal_min_amount: float = 100.0
    withdrawal_fee: float = 5.0
    supported_currencies: List[str] = field(default_factory=lambda: ["YER", "USD"])
    
    def __post_init__(self):
        if self.min_transfer_amount < 0:
            raise InvalidConfiguration("min_transfer_amount cannot be negative")
        if self.max_transfer_amount <= self.min_transfer_amount:
            raise InvalidConfiguration("max_transfer_amount must be greater than min_transfer_amount")
        if self.commission_rate < 0 or self.commission_rate > 1:
            raise InvalidConfiguration("commission_rate must be between 0 and 1")


@dataclass
class LoggingConfig:
    """Logging configuration"""
    level: LogLevel = LogLevel.INFO
    log_to_file: bool = True
    log_to_console: bool = True
    log_directory: str = "logs"
    max_file_size_mb: int = 10
    backup_count: int = 5
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
    
    def __post_init__(self):
        if self.max_file_size_mb < 1:
            raise InvalidConfiguration("max_file_size_mb must be at least 1")
        if self.backup_count < 0:
            raise InvalidConfiguration("backup_count cannot be negative")


@dataclass
class CacheConfig:
    """Cache configuration"""
    enable_caching: bool = True
    default_ttl_seconds: int = 300
    max_entries: int = 10000
    cleanup_interval_minutes: int = 10
    
    def __post_init__(self):
        if self.default_ttl_seconds < 1:
            raise InvalidConfiguration("default_ttl_seconds must be at least 1")
        if self.max_entries < 100:
            raise InvalidConfiguration("max_entries must be at least 100")


@dataclass
class MonitoringConfig:
    """Monitoring and metrics configuration"""
    enable_monitoring: bool = True
    metrics_collection_interval: int = 60
    health_check_interval: int = 30
    alert_thresholds: Dict[str, float] = field(default_factory=lambda: {
        "cpu_usage": 80.0,
        "memory_usage": 80.0,
        "disk_usage": 85.0,
        "error_rate": 5.0,
        "response_time": 2.0
    })
    
    def __post_init__(self):
        for key, value in self.alert_thresholds.items():
            if value < 0 or value > 100:
                raise InvalidConfiguration(f"alert_thresholds.{key} must be between 0 and 100")


@dataclass
class BotConfig:
    """Main bot configuration"""
    environment: Environment = Environment.DEVELOPMENT
    debug: bool = False
    admin_user_ids: List[int] = field(default_factory=list)
    maintenance_mode: bool = False
    registration_enabled: bool = True
    max_users: int = 10000
    features_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "referral_system": True,
        "commission_system": True,
        "file_uploads": True,
        "notifications": True,
        "analytics": True,
        "backup": True
    })


class Settings:
    """Main settings class with validation and environment variable support"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or "config.json"
        self._config_data = {}
        
        # Load configuration
        self._load_config()
        self._load_environment_variables()
        self._validate_config()
        
        # Initialize configuration objects
        self.database = DatabaseConfig(**self._get_section("database", {}))
        self.telegram = TelegramConfig(**self._get_section("telegram", {}))
        self.security = SecurityConfig(**self._get_section("security", {}))
        self.payment = PaymentConfig(**self._get_section("payment", {}))
        self.logging = LoggingConfig(**self._get_section("logging", {}))
        self.cache = CacheConfig(**self._get_section("cache", {}))
        self.monitoring = MonitoringConfig(**self._get_section("monitoring", {}))
        self.bot = BotConfig(**self._get_section("bot", {}))
        
    def _load_config(self):
        """Load configuration from file"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    self._config_data = json.load(f)
            except json.JSONDecodeError as e:
                raise InvalidConfiguration(f"Invalid JSON in config file: {e}")
            except Exception as e:
                raise ConfigurationException(f"Failed to load config file: {e}")
        else:
            # Create default config file
            self._create_default_config()
            
    def _create_default_config(self):
        """Create default configuration file"""
        default_config = {
            "telegram": {
                "token": "YOUR_BOT_TOKEN_HERE"
            },
            "database": {
                "path": "yemen_net.db",
                "max_connections": 20
            },
            "security": {
                "enable_rate_limiting": True,
                "max_login_attempts": 3
            },
            "payment": {
                "enable_payments": True,
                "min_transfer_amount": 10.0
            },
            "logging": {
                "level": "INFO",
                "log_to_file": True
            },
            "bot": {
                "environment": "development",
                "debug": True
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            self._config_data = default_config
        except Exception as e:
            raise ConfigurationException(f"Failed to create default config: {e}")
            
    def _load_environment_variables(self):
        """Load configuration from environment variables"""
        env_mappings = {
            # Telegram
            "TELEGRAM_BOT_TOKEN": ("telegram", "token"),
            "TELEGRAM_WEBHOOK_URL": ("telegram", "webhook_url"),
            "TELEGRAM_WEBHOOK_PORT": ("telegram", "webhook_port"),
            
            # Database
            "DATABASE_PATH": ("database", "path"),
            "DATABASE_MAX_CONNECTIONS": ("database", "max_connections"),
            "DATABASE_TIMEOUT": ("database", "timeout"),
            
            # Security
            "SECURITY_ENABLE_RATE_LIMITING": ("security", "enable_rate_limiting"),
            "SECURITY_MAX_LOGIN_ATTEMPTS": ("security", "max_login_attempts"),
            "SECURITY_JWT_SECRET": ("security", "jwt_secret_key"),
            
            # Payment
            "PAYMENT_ENABLE": ("payment", "enable_payments"),
            "PAYMENT_MIN_AMOUNT": ("payment", "min_transfer_amount"),
            "PAYMENT_MAX_AMOUNT": ("payment", "max_transfer_amount"),
            "PAYMENT_COMMISSION_RATE": ("payment", "commission_rate"),
            
            # Logging
            "LOG_LEVEL": ("logging", "level"),
            "LOG_DIRECTORY": ("logging", "log_directory"),
            
            # Bot
            "BOT_ENVIRONMENT": ("bot", "environment"),
            "BOT_DEBUG": ("bot", "debug"),
            "BOT_MAINTENANCE_MODE": ("bot", "maintenance_mode"),
            "BOT_ADMIN_IDS": ("bot", "admin_user_ids")
        }
        
        for env_var, (section, key) in env_mappings.items():
            value = os.getenv(env_var)
            if value is not None:
                # Ensure section exists
                if section not in self._config_data:
                    self._config_data[section] = {}
                    
                # Type conversion
                if key in ["max_connections", "webhook_port", "max_login_attempts"]:
                    value = int(value)
                elif key in ["timeout", "min_transfer_amount", "max_transfer_amount", "commission_rate"]:
                    value = float(value)
                elif key in ["enable_rate_limiting", "enable_payments", "debug", "maintenance_mode"]:
                    value = value.lower() in ("true", "1", "yes", "on")
                elif key == "admin_user_ids":
                    value = [int(x.strip()) for x in value.split(",") if x.strip()]
                    
                self._config_data[section][key] = value
                
    def _validate_config(self):
        """Validate configuration"""
        required_settings = [
            ("telegram", "token")
        ]
        
        for section, key in required_settings:
            if not self._get_nested_value(section, key):
                raise MissingConfiguration(f"Required setting missing: {section}.{key}")
                
    def _get_section(self, section_name: str, default: Dict[str, Any]) -> Dict[str, Any]:
        """Get configuration section with defaults"""
        return self._config_data.get(section_name, default)
        
    def _get_nested_value(self, section: str, key: str, default: Any = None) -> Any:
        """Get nested configuration value"""
        return self._config_data.get(section, {}).get(key, default)
        
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot notation"""
        keys = key.split(".")
        value = self._config_data
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
                
        return value
        
    def set(self, key: str, value: Any):
        """Set configuration value by dot notation"""
        keys = key.split(".")
        config = self._config_data
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
            
        config[keys[-1]] = value
        
    def save(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self._config_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigurationException(f"Failed to save config: {e}")
            
    def reload(self):
        """Reload configuration from file and environment"""
        self.__init__(self.config_file)
        
    def get_summary(self) -> Dict[str, Any]:
        """Get configuration summary for debugging"""
        return {
            "environment": self.bot.environment.value,
            "debug": self.bot.debug,
            "database_path": self.database.path,
            "telegram_configured": bool(self.telegram.token and self.telegram.token != "YOUR_BOT_TOKEN_HERE"),
            "features_enabled": self.bot.features_enabled,
            "security_enabled": self.security.enable_rate_limiting,
            "payment_enabled": self.payment.enable_payments,
            "logging_level": self.logging.level.value,
            "cache_enabled": self.cache.enable_caching,
            "monitoring_enabled": self.monitoring.enable_monitoring
        }


# Global settings instance
settings = Settings()

# Convenience exports
DATABASE_CONFIG = settings.database
TELEGRAM_CONFIG = settings.telegram
SECURITY_CONFIG = settings.security
PAYMENT_CONFIG = settings.payment
LOGGING_CONFIG = settings.logging
CACHE_CONFIG = settings.cache
MONITORING_CONFIG = settings.monitoring
BOT_CONFIG = settings.bot