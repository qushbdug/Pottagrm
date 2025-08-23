"""
Security and permission system for Yemen Net Bot v2
"""

import hashlib
import secrets
import time
import logging
from typing import Dict, List, Optional, Set, Any, Callable
from functools import wraps
from telegram import Update
from telegram.ext import CallbackContext
from .exceptions import PermissionError, ValidationError
from .cache_manager import cache_manager

logger = logging.getLogger(__name__)

class Permission:
    """Permission definition"""
    
    def __init__(self, name: str, description: str, level: int = 0):
        """
        Initialize permission
        
        Args:
            name: Permission name
            description: Permission description
            level: Permission level (higher = more privileged)
        """
        self.name = name
        self.description = description
        self.level = level
    
    def __str__(self):
        return f"{self.name} (Level {self.level})"
    
    def __repr__(self):
        return f"Permission('{self.name}', '{self.description}', {self.level})"

class Role:
    """User role definition"""
    
    def __init__(self, name: str, description: str, permissions: Set[str] = None):
        """
        Initialize role
        
        Args:
            name: Role name
            description: Role description
            permissions: Set of permission names
        """
        self.name = name
        self.description = description
        self.permissions = permissions or set()
    
    def has_permission(self, permission_name: str) -> bool:
        """Check if role has specific permission"""
        return permission_name in self.permissions
    
    def add_permission(self, permission_name: str):
        """Add permission to role"""
        self.permissions.add(permission_name)
    
    def remove_permission(self, permission_name: str):
        """Remove permission from role"""
        self.permissions.discard(permission_name)
    
    def __str__(self):
        return f"{self.name}: {', '.join(sorted(self.permissions))}"

class SecurityManager:
    """Centralized security and permission management"""
    
    def __init__(self):
        """Initialize security manager"""
        self.permissions: Dict[str, Permission] = {}
        self.roles: Dict[str, Role] = {}
        self.user_roles: Dict[int, str] = {}  # user_id -> role_name
        self.user_permissions: Dict[int, Set[str]] = {}  # user_id -> set of permissions
        
        # Security settings
        self.max_login_attempts = 3
        self.login_lockout_duration = 300  # 5 minutes
        self.failed_login_attempts: Dict[int, Dict[str, Any]] = {}
        
        # Initialize default permissions and roles
        self._initialize_defaults()
    
    def _initialize_defaults(self):
        """Initialize default permissions and roles"""
        # Define permissions
        permissions_data = [
            ("user_basic", "Basic user operations", 1),
            ("user_profile", "View and edit profile", 1),
            ("user_wallet", "Access wallet", 1),
            ("user_transactions", "View transactions", 1),
            ("user_cards", "Purchase cards", 1),
            ("agent_basic", "Agent operations", 2),
            ("agent_sales", "View sales reports", 2),
            ("agent_commissions", "View commissions", 2),
            ("supplier_basic", "Supplier operations", 3),
            ("supplier_cards", "Manage cards", 3),
            ("supplier_reports", "View supplier reports", 3),
            ("admin_basic", "Admin operations", 4),
            ("admin_users", "Manage users", 4),
            ("admin_system", "System administration", 4),
            ("admin_financial", "Financial management", 4),
            ("super_admin", "Super admin operations", 5),
            ("super_activate", "Activate suppliers", 5),
            ("super_override", "Override any restriction", 5)
        ]
        
        for name, description, level in permissions_data:
            self.permissions[name] = Permission(name, description, level)
        
        # Define roles
        roles_data = [
            ("user", "Regular user", {"user_basic", "user_profile", "user_wallet", "user_transactions", "user_cards"}),
            ("agent", "Sales agent", {"user_basic", "user_profile", "user_wallet", "user_transactions", "user_cards", 
                                     "agent_basic", "agent_sales", "agent_commissions"}),
            ("supplier", "Card supplier", {"user_basic", "user_profile", "user_wallet", "user_transactions", "user_cards",
                                         "supplier_basic", "supplier_cards", "supplier_reports"}),
            ("admin", "System administrator", {"user_basic", "user_profile", "user_wallet", "user_transactions", "user_cards",
                                             "agent_basic", "agent_sales", "agent_commissions",
                                             "supplier_basic", "supplier_cards", "supplier_reports",
                                             "admin_basic", "admin_users", "admin_system", "admin_financial"}),
            ("super_admin", "Super administrator", {"user_basic", "user_profile", "user_wallet", "user_transactions", "user_cards",
                                                  "agent_basic", "agent_sales", "agent_commissions",
                                                  "supplier_basic", "supplier_cards", "supplier_reports",
                                                  "admin_basic", "admin_users", "admin_system", "admin_financial",
                                                  "super_admin", "super_activate", "super_override"})
        ]
        
        for name, description, permissions in roles_data:
            self.roles[name] = Role(name, description, permissions)
    
    def add_permission(self, name: str, description: str, level: int = 0) -> Permission:
        """Add new permission"""
        if name in self.permissions:
            raise ValueError(f"Permission '{name}' already exists")
        
        permission = Permission(name, description, level)
        self.permissions[name] = permission
        logger.info(f"Added permission: {permission}")
        return permission
    
    def add_role(self, name: str, description: str, permissions: Set[str] = None) -> Role:
        """Add new role"""
        if name in self.roles:
            raise ValueError(f"Role '{name}' already exists")
        
        # Validate permissions
        if permissions:
            invalid_permissions = permissions - set(self.permissions.keys())
            if invalid_permissions:
                raise ValueError(f"Invalid permissions: {invalid_permissions}")
        
        role = Role(name, description, permissions or set())
        self.roles[name] = role
        logger.info(f"Added role: {role}")
        return role
    
    def assign_role(self, user_id: int, role_name: str):
        """Assign role to user"""
        if role_name not in self.roles:
            raise ValueError(f"Role '{role_name}' does not exist")
        
        self.user_roles[user_id] = role_name
        self.user_permissions[user_id] = self.roles[role_name].permissions.copy()
        
        # Cache user permissions
        cache_key = f"user_permissions_{user_id}"
        cache_manager.set(cache_key, self.user_permissions[user_id], ttl=3600)
        
        logger.info(f"Assigned role '{role_name}' to user {user_id}")
    
    def remove_role(self, user_id: int):
        """Remove role from user"""
        if user_id in self.user_roles:
            role_name = self.user_roles[user_id]
            del self.user_roles[user_id]
            del self.user_permissions[user_id]
            
            # Remove from cache
            cache_key = f"user_permissions_{user_id}"
            cache_manager.delete(cache_key)
            
            logger.info(f"Removed role '{role_name}' from user {user_id}")
    
    def has_permission(self, user_id: int, permission_name: str) -> bool:
        """Check if user has specific permission"""
        # Check cache first
        cache_key = f"user_permissions_{user_id}"
        cached_permissions = cache_manager.get(cache_key)
        
        if cached_permissions is not None:
            return permission_name in cached_permissions
        
        # Check memory
        if user_id in self.user_permissions:
            return permission_name in self.user_permissions[user_id]
        
        return False
    
    def get_user_role(self, user_id: int) -> Optional[str]:
        """Get user's role name"""
        return self.user_roles.get(user_id)
    
    def get_user_permissions(self, user_id: int) -> Set[str]:
        """Get user's permissions"""
        # Check cache first
        cache_key = f"user_permissions_{user_id}"
        cached_permissions = cache_manager.get(cache_key)
        
        if cached_permissions is not None:
            return cached_permissions
        
        # Return from memory
        return self.user_permissions.get(user_id, set()).copy()
    
    def get_role_permissions(self, role_name: str) -> Set[str]:
        """Get permissions for a role"""
        if role_name not in self.roles:
            return set()
        return self.roles[role_name].permissions.copy()
    
    def require_permission(self, permission_name: str):
        """Decorator to require specific permission"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
                user_id = update.effective_user.id if update.effective_user else None
                
                if not user_id:
                    raise PermissionError("User not authenticated")
                
                if not self.has_permission(user_id, permission_name):
                    raise PermissionError(f"Permission '{permission_name}' required")
                
                return await func(update, context, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_role(self, role_name: str):
        """Decorator to require specific role"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(update: Update, context: CallbackContext, *args, **kwargs):
                user_id = update.effective_user.id if update.effective_user else None
                
                if not user_id:
                    raise PermissionError("User not authenticated")
                
                user_role = self.get_user_role(user_id)
                if user_role != role_name:
                    raise PermissionError(f"Role '{role_name}' required, current role: '{user_role}'")
                
                return await func(update, context, *args, **kwargs)
            
            return wrapper
        return decorator
    
    def require_minimum_level(self, min_level: int):
        """Decorator to require minimum permission level"""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(update: Update, context, *args, **kwargs):
                user_id = update.effective_user.id if update.effective_user else None
                
                if not user_id:
                    raise PermissionError("User not authenticated")
                
                user_role = self.get_user_role(user_id)
                if not user_role or user_role not in self.roles:
                    raise PermissionError("Invalid user role")
                
                role_permissions = self.roles[user_role].permissions
                max_level = max(self.permissions[perm].level for perm in role_permissions)
                
                if max_level < min_level:
                    raise PermissionError(f"Minimum permission level {min_level} required")
                
                return await func(update, context, *args, **kwargs)
            
            return wrapper
        return decorator

class InputValidator:
    """Input validation and sanitization"""
    
    @staticmethod
    def validate_phone_number(phone: str) -> bool:
        """Validate phone number format"""
        import re
        # Yemen phone number format: +967XXXXXXXXX or 967XXXXXXXXX
        pattern = r'^(\+?967|0)?[0-9]{9}$'
        return bool(re.match(pattern, phone))
    
    @staticmethod
    def validate_email(email: str) -> bool:
        """Validate email format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(pattern, email))
    
    @staticmethod
    def validate_amount(amount: str) -> bool:
        """Validate monetary amount"""
        try:
            amount_float = float(amount)
            return amount_float > 0 and amount_float <= 999999.99
        except ValueError:
            return False
    
    @staticmethod
    def sanitize_text(text: str, max_length: int = 1000) -> str:
        """Sanitize text input"""
        if not text:
            return ""
        
        # Remove potentially dangerous characters
        sanitized = text.strip()
        sanitized = sanitized.replace('<script>', '').replace('</script>', '')
        sanitized = sanitized.replace('javascript:', '')
        
        # Limit length
        if len(sanitized) > max_length:
            sanitized = sanitized[:max_length]
        
        return sanitized
    
    @staticmethod
    def validate_card_number(card_number: str) -> bool:
        """Validate card number format"""
        import re
        # Basic card number validation (16-19 digits)
        pattern = r'^[0-9]{16,19}$'
        return bool(re.match(pattern, card_number))

class SecurityUtils:
    """Security utility functions"""
    
    @staticmethod
    def generate_token(length: int = 32) -> str:
        """Generate secure random token"""
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple:
        """Hash password with salt"""
        if salt is None:
            salt = secrets.token_hex(16)
        
        # Use PBKDF2 for password hashing
        import hashlib
        hash_obj = hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 100000)
        return salt, hash_obj.hex()
    
    @staticmethod
    def verify_password(password: str, salt: str, hash_value: str) -> bool:
        """Verify password against hash"""
        _, computed_hash = SecurityUtils.hash_password(password, salt)
        return computed_hash == hash_value
    
    @staticmethod
    def generate_otp(length: int = 6) -> str:
        """Generate OTP code"""
        return ''.join(secrets.choice('0123456789') for _ in range(length))
    
    @staticmethod
    def rate_limit_key(user_id: int, action: str) -> str:
        """Generate rate limit key"""
        return f"rate_limit:{user_id}:{action}"

# Global security manager instance
security_manager = SecurityManager()

# Convenience decorators
def require_permission(permission_name: str):
    """Require specific permission decorator"""
    return security_manager.require_permission(permission_name)

def require_role(role_name: str):
    """Require specific role decorator"""
    return security_manager.require_role(role_name)

def require_admin():
    """Require admin role decorator"""
    return security_manager.require_minimum_level(4)

def require_super_admin():
    """Require super admin role decorator"""
    return security_manager.require_minimum_level(5)