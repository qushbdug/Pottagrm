"""
Handlers module for Yemen Net Bot v2
Contains all message and callback handlers organized by functionality
"""

# Import handler setup functions
from .user_handlers import setup_user_handlers
from .admin_handlers import setup_admin_handlers
from .payment_handlers import setup_payment_handlers

# Export handler setup functions
__all__ = [
    'setup_user_handlers',
    'setup_admin_handlers',
    'setup_payment_handlers'
]

def setup_all_handlers():
    """Setup all handlers for the bot"""
    handlers = []
    
    # Add user handlers
    handlers.extend(setup_user_handlers())
    
    # Add admin handlers
    handlers.extend(setup_admin_handlers())
    
    # Add payment handlers
    handlers.extend(setup_payment_handlers())
    
    return handlers

def get_handlers_info():
    """Get information about available handlers"""
    return {
        'user_handlers': 'User interaction handlers',
        'admin_handlers': 'Administrative handlers',
        'payment_handlers': 'Payment processing handlers',
        'total_handlers': 3
    }