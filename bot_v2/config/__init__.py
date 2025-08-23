"""
Configuration module for Yemen Net Bot v2
Contains configuration management and constants
"""

# Import configuration components
from .bot_config import BotConfig
from .database_config import DatabaseConfig
from .payment_config import PaymentConfig
from .notification_config import NotificationConfig
from .security_config import SecurityConfig
from .monitoring_config import MonitoringConfig

# Export configuration classes
__all__ = [
    'BotConfig',
    'DatabaseConfig',
    'PaymentConfig',
    'NotificationConfig',
    'SecurityConfig',
    'MonitoringConfig'
]

def get_config_summary():
    """Get a summary of all configuration sections"""
    return {
        'bot': 'Bot configuration and settings',
        'database': 'Database connection and settings',
        'payment': 'Payment processing settings',
        'notification': 'Notification system settings',
        'security': 'Security and authentication settings',
        'monitoring': 'Monitoring and logging settings'
    }

def validate_all_configs():
    """Validate all configuration sections"""
    try:
        # This would validate all config sections
        # For now, just return True as a placeholder
        return True
    except Exception as e:
        print(f"Configuration validation failed: {e}")
        return False

def get_config_info():
    """Get information about configuration system"""
    return {
        'sections': 6,
        'status': 'ready',
        'version': '2.0.0',
        'description': 'Comprehensive configuration management system'
    }