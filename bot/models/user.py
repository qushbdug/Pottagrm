"""
نموذج المستخدم
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

class UserRole(Enum):
    """أدوار المستخدمين"""
    CLIENT = "عميل"
    AGENT = "وكيل"
    SUPPLIER = "مزود"
    ADMIN = "مدير"
    SUPER_ADMIN = "مدير عام"

@dataclass
class User:
    """نموذج المستخدم"""
    id: Optional[int] = None
    telegram_id: int = 0
    full_name: str = ""
    phone: str = ""
    role: UserRole = UserRole.CLIENT
    balance: float = 0.0
    invite_code: Optional[str] = None
    is_active: bool = False
    bank_account: Optional[str] = None
    total_referrals: int = 0
    referral_bonus: float = 0.0
    wallet_number: Optional[str] = None
    created_at: Optional[datetime] = None
    
    @property
    def is_admin(self) -> bool:
        """التحقق من كون المستخدم مدير"""
        return self.role in [UserRole.ADMIN, UserRole.SUPER_ADMIN]
    
    @property
    def is_supplier(self) -> bool:
        """التحقق من كون المستخدم مزود"""
        return self.role == UserRole.SUPPLIER
    
    @property
    def is_agent(self) -> bool:
        """التحقق من كون المستخدم وكيل"""
        return self.role == UserRole.AGENT
    
    @property
    def can_sell_cards(self) -> bool:
        """التحقق من إمكانية بيع الكروت"""
        return self.role in [UserRole.SUPPLIER, UserRole.AGENT]
    
    def to_dict(self) -> dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'telegram_id': self.telegram_id,
            'full_name': self.full_name,
            'phone': self.phone,
            'role': self.role.value,
            'balance': self.balance,
            'invite_code': self.invite_code,
            'is_active': self.is_active,
            'bank_account': self.bank_account,
            'total_referrals': self.total_referrals,
            'referral_bonus': self.referral_bonus,
            'wallet_number': self.wallet_number,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """إنشاء من قاموس"""
        user = cls()
        user.id = data.get('id')
        user.telegram_id = data.get('telegram_id', 0)
        user.full_name = data.get('full_name', '')
        user.phone = data.get('phone', '')
        
        # تحويل الدور من نص إلى enum
        role_str = data.get('role', 'عميل')
        for role in UserRole:
            if role.value == role_str:
                user.role = role
                break
        
        user.balance = data.get('balance', 0.0)
        user.invite_code = data.get('invite_code')
        user.is_active = data.get('is_active', False)
        user.bank_account = data.get('bank_account')
        user.total_referrals = data.get('total_referrals', 0)
        user.referral_bonus = data.get('referral_bonus', 0.0)
        user.wallet_number = data.get('wallet_number')
        
        created_at_str = data.get('created_at')
        if created_at_str:
            user.created_at = datetime.fromisoformat(created_at_str)
        
        return user