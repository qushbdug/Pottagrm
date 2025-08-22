"""
Core module for Yemen Net Bot v2
Contains essential bot functionality and configuration
"""

# Import core components
from .config import config
from .exceptions import (
    BotException,
    DatabaseException,
    ValidationException,
    AuthenticationException,
    PaymentException,
    NetworkException,
    RateLimitException,
    ConfigurationException
)
from .conversation_states import (
    ConversationStates,
    get_state_description,
    is_valid_state,
    get_all_states,
    get_user_states,
    get_admin_states,
    get_payment_states,
    get_transfer_states
)

# Export core components
__all__ = [
    # Configuration
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
    
    # Conversation states
    'ConversationStates',
    'get_state_description',
    'is_valid_state',
    'get_all_states',
    'get_user_states',
    'get_admin_states',
    'get_payment_states',
    'get_transfer_states'
]

def get_core_info():
    """Get information about core components"""
    return {
        'config': 'Configuration management system',
        'exceptions': 'Custom exception classes',
        'conversation_states': 'Conversation state management',
        'version': '2.0.0',
        'status': 'ready'
    }

def get_core_status():
    """Get status of core components"""
    try:
        return {
            'config': 'ready' if config else 'not_ready',
            'exceptions': 'ready',
            'conversation_states': 'ready',
            'overall_status': 'ready'
        }
    except Exception as e:
        return {
            'overall_status': 'error',
            'error': str(e)
        }