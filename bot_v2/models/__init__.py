"""
Models module for Yemen Net Bot v2
Contains data models and database schemas
"""

# Import data models
from .user import User, UserRole, UserStatus
from .transaction import Transaction, TransactionType, TransactionStatus
from .card import Card, CardType, CardStatus
from .network import Network, NetworkStatus
from .card_category import CardCategory

# Export all models
__all__ = [
    # User models
    'User',
    'UserRole',
    'UserStatus',
    
    # Transaction models
    'Transaction',
    'TransactionType',
    'TransactionStatus',
    
    # Card models
    'Card',
    'CardType',
    'CardStatus',
    
    # Network models
    'Network',
    'NetworkStatus',
    
    # Category models
    'CardCategory'
]

def get_all_models():
    """Get all available models"""
    return {
        'user': User,
        'transaction': Transaction,
        'card': Card,
        'network': Network,
        'card_category': CardCategory
    }

def validate_model_data(model_name: str, data: dict) -> bool:
    """Validate data against a specific model"""
    try:
        models = get_all_models()
        if model_name not in models:
            return False
        
        model = models[model_name]
        # This is a placeholder - actual validation would depend on model implementation
        return True
    except Exception:
        return False

def get_models_info():
    """Get information about available models"""
    return {
        'user': 'User account and profile management',
        'transaction': 'Financial transactions and transfers',
        'card': 'Digital card management',
        'network': 'Network and service providers',
        'card_category': 'Card categories and types',
        'total_models': 5
    }