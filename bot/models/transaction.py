"""
نماذج المعاملات
"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional
from datetime import datetime

class TransactionType(Enum):
    """أنواع المعاملات"""
    CARD_PURCHASE = "card_purchase"
    BALANCE_RECHARGE = "balance_recharge"
    COMMISSION = "commission"
    REFERRAL_BONUS = "referral_bonus"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    REFUND = "refund"

class TransactionStatus(Enum):
    """حالات المعاملات"""
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

@dataclass
class Transaction:
    """نموذج المعاملة"""
    id: Optional[str] = None
    from_user: Optional[int] = None
    to_user: Optional[int] = None
    amount: float = 0.0
    type: TransactionType = TransactionType.TRANSFER
    status: TransactionStatus = TransactionStatus.PENDING
    reference_id: Optional[str] = None
    is_withdrawable: bool = False
    created_at: Optional[datetime] = None
    
    def to_dict(self) -> dict:
        """تحويل إلى قاموس"""
        return {
            'id': self.id,
            'from_user': self.from_user,
            'to_user': self.to_user,
            'amount': self.amount,
            'type': self.type.value,
            'status': self.status.value,
            'reference_id': self.reference_id,
            'is_withdrawable': self.is_withdrawable,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }