"""
Services module for Yemen Net Bot v2
Contains database, cache, rate limiting, and monitoring services
"""

# Import service instances
from .database_manager import db_manager, DatabaseManager
from .cache_manager import cache_manager, CacheManager, cached
from .rate_limiter import rate_limiter, RateLimiter, rate_limit
from .monitoring import monitoring_service, MonitoringService

# Export service instances and classes
__all__ = [
    # Database
    'db_manager',
    'DatabaseManager',
    
    # Cache
    'cache_manager',
    'CacheManager',
    'cached',
    
    # Rate Limiting
    'rate_limiter',
    'RateLimiter',
    'rate_limit',
    
    # Monitoring
    'monitoring_service',
    'MonitoringService'
]

def get_services_status():
    """Get status of all services"""
    try:
        return {
            'database': {
                'status': 'ready' if db_manager else 'not_ready',
                'type': 'DatabaseManager'
            },
            'cache': {
                'status': 'ready' if cache_manager else 'not_ready',
                'type': 'CacheManager'
            },
            'rate_limiter': {
                'status': 'ready' if rate_limiter else 'not_ready',
                'type': 'RateLimiter'
            },
            'monitoring': {
                'status': 'ready' if monitoring_service else 'not_ready',
                'type': 'MonitoringService'
            }
        }
    except Exception as e:
        return {
            'error': str(e),
            'status': 'error'
        }

def initialize_all_services():
    """Initialize all services"""
    try:
        # This would initialize all services
        # For now, just return True as a placeholder
        return True
    except Exception as e:
        print(f"Service initialization failed: {e}")
        return False

def shutdown_all_services():
    """Shutdown all services gracefully"""
    try:
        # This would shutdown all services
        # For now, just return True as a placeholder
        return True
    except Exception as e:
        print(f"Service shutdown failed: {e}")
        return False