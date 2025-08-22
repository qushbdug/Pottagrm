"""
Yemen Net Bot v2 - Enhanced Telegram Bot
A comprehensive financial services bot with advanced architecture

This bot provides:
- User management and authentication
- Wallet and balance management
- Card trading and management
- Money transfers and transactions
- Advanced monitoring and analytics
- Comprehensive error handling
- Performance optimization
- Security features

Author: Yemen Net Team
Version: 2.0.0
License: MIT
"""

__version__ = "2.0.0"
__author__ = "Yemen Net Team"
__license__ = "MIT"
__description__ = "Enhanced Telegram Bot for Financial Services"

# Import core components
from .core.config import config
from .core.exceptions import (
    BotException,
    DatabaseException,
    ValidationException,
    AuthenticationException,
    PaymentException,
    NetworkException,
    RateLimitException,
    ConfigurationException
)

# Import services
from .services import (
    db_manager,
    cache_manager,
    rate_limiter,
    monitoring_service
)

# Import conversation states
from .core.conversation_states import (
    ConversationStates,
    get_state_description,
    is_valid_state,
    get_all_states,
    get_user_states,
    get_admin_states,
    get_payment_states,
    get_transfer_states
)

# Main bot class
from .main import YemenNetBot

# Utility functions
def get_bot_info():
    """Get comprehensive bot information"""
    return {
        'name': 'Yemen Net Bot v2',
        'version': __version__,
        'author': __author__,
        'license': __license__,
        'description': __description__,
        'features': [
            'Advanced Architecture',
            'Comprehensive Error Handling',
            'Performance Optimization',
            'Security Features',
            'Monitoring & Analytics',
            'Rate Limiting',
            'Caching System',
            'Database Management'
        ]
    }

def get_system_status():
    """Get current system status"""
    try:
        return {
            'bot_status': 'initialized',
            'database_status': 'ready' if db_manager else 'not_ready',
            'cache_status': 'ready' if cache_manager else 'not_ready',
            'rate_limiter_status': 'ready' if rate_limiter else 'not_ready',
            'monitoring_status': 'ready' if monitoring_service else 'not_ready',
            'config_status': 'ready' if config else 'not_ready'
        }
    except Exception as e:
        return {
            'bot_status': 'error',
            'error': str(e)
        }

def validate_installation():
    """Validate that all components are properly installed"""
    errors = []
    
    # Check required modules
    required_modules = [
        'telegram',
        'sqlite3',
        'asyncio',
        'logging',
        'threading',
        'time',
        'json',
        'hashlib',
        'uuid',
        'datetime',
        'collections',
        'dataclasses',
        'functools',
        'pathlib',
        'queue',
        'contextlib'
    ]
    
    for module in required_modules:
        try:
            __import__(module)
        except ImportError:
            errors.append(f"Missing required module: {module}")
    
    # Check optional modules
    optional_modules = [
        'psutil',
        'cryptography',
        'aiofiles',
        'pandas',
        'matplotlib',
        'seaborn',
        'Pillow',
        'qrcode'
    ]
    
    missing_optional = []
    for module in optional_modules:
        try:
            __import__(module)
        except ImportError:
            missing_optional.append(module)
    
    if missing_optional:
        print(f"Warning: Missing optional modules: {', '.join(missing_optional)}")
        print("These modules provide additional functionality but are not required for basic operation.")
    
    # Check configuration
    try:
        if not config.BOT_TOKEN:
            errors.append("BOT_TOKEN not configured")
    except Exception as e:
        errors.append(f"Configuration error: {e}")
    
    # Check database
    try:
        if not db_manager:
            errors.append("Database manager not initialized")
    except Exception as e:
        errors.append(f"Database error: {e}")
    
    if errors:
        print("Installation validation failed:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    print("Installation validation passed successfully!")
    return True

# Export main components
__all__ = [
    # Core
    'YemenNetBot',
    'config',
    
    # Exceptions
    'BotException',
    'DatabaseException', 
    'ValidationException',
    'AuthenticationException',
    'PaymentException',
    'NetworkException',
    'RateLimitException',
    'ConfigurationException',
    
    # Services
    'db_manager',
    'cache_manager',
    'rate_limiter',
    'monitoring_service',
    
    # Conversation states
    'ConversationStates',
    'get_state_description',
    'is_valid_state',
    'get_all_states',
    'get_user_states',
    'get_admin_states',
    'get_payment_states',
    'get_transfer_states',
    
    # Utility functions
    'get_bot_info',
    'get_system_status',
    'validate_installation',
    
    # Version info
    '__version__',
    '__author__',
    '__license__',
    '__description__'
]

# Print welcome message on import
if __name__ != "__main__":
    print(f"🚀 Yemen Net Bot v{__version__} loaded successfully!")
    print(f"📚 For documentation, visit: https://github.com/yemen-net/bot-v2")
    print(f"🆘 For support, contact: @yemen_net_support")