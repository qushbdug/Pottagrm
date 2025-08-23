"""
Notification Manager for Yemen Net Bot
Handles user notifications with queuing and delivery tracking
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
import json

from core.exceptions import DatabaseError, ValidationError
from core.logger import get_performance_logger


class NotificationType(Enum):
    """Types of notifications"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    SYSTEM = "system"
    PAYMENT = "payment"
    CARD_PURCHASE = "card_purchase"
    BALANCE_UPDATE = "balance_update"
    PROMOTION = "promotion"


@dataclass
class Notification:
    """Notification data structure"""
    id: Optional[int] = None
    user_id: int = 0
    title: str = ""
    message: str = ""
    type: NotificationType = NotificationType.INFO
    is_read: bool = False
    created_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'type': self.type.value,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'read_at': self.read_at.isoformat() if self.read_at else None,
            'metadata': self.metadata
        }


@dataclass
class NotificationTemplate:
    """Template for notification messages"""
    title_template: str
    message_template: str
    type: NotificationType
    
    def format(self, **kwargs) -> tuple:
        """Format template with variables"""
        title = self.title_template.format(**kwargs)
        message = self.message_template.format(**kwargs)
        return title, message


class NotificationManager:
    """Advanced notification manager with queuing and templates"""
    
    def __init__(self, db_manager):
        self.db_manager = db_manager
        self.logger = logging.getLogger(__name__)
        self.perf_logger = get_performance_logger()
        
        # Notification queue for bulk processing
        self.notification_queue = asyncio.Queue()
        self.delivery_callbacks: Dict[NotificationType, List[Callable]] = {}
        
        # Notification templates
        self.templates = {
            'welcome': NotificationTemplate(
                title_template="مرحباً بك في Yemen Net! 🎉",
                message_template="مرحباً {name}! تم تسجيلك بنجاح في نظام بطاقات Yemen Net. يمكنك الآن شراء البطاقات وإدارة حسابك.",
                type=NotificationType.SUCCESS
            ),
            'balance_credited': NotificationTemplate(
                title_template="تم إيداع رصيد 💰",
                message_template="تم إضافة {amount} ر.ي إلى رصيدك. الرصيد الحالي: {balance} ر.ي",
                type=NotificationType.BALANCE_UPDATE
            ),
            'balance_debited': NotificationTemplate(
                title_template="تم خصم رصيد 💸",
                message_template="تم خصم {amount} ر.ي من رصيدك. الرصيد الحالي: {balance} ر.ي",
                type=NotificationType.BALANCE_UPDATE
            ),
            'card_purchased': NotificationTemplate(
                title_template="تم شراء بطاقة بنجاح 💳",
                message_template="تم شراء بطاقة {card_type} بقيمة {amount} ر.ي. الرقم التسلسلي: {serial}",
                type=NotificationType.CARD_PURCHASE
            ),
            'low_balance': NotificationTemplate(
                title_template="تحذير: رصيد منخفض ⚠️",
                message_template="رصيدك الحالي {balance} ر.ي منخفض. يرجى إعادة الشحن لمتابعة الشراء.",
                type=NotificationType.WARNING
            ),
            'promotion': NotificationTemplate(
                title_template="عرض خاص! 🎁",
                message_template="{message}",
                type=NotificationType.PROMOTION
            ),
            'system_maintenance': NotificationTemplate(
                title_template="صيانة النظام 🔧",
                message_template="سيتم إجراء صيانة على النظام من {start_time} إلى {end_time}. نعتذر عن أي إزعاج.",
                type=NotificationType.SYSTEM
            ),
            'payment_failed': NotificationTemplate(
                title_template="فشل في الدفع ❌",
                message_template="فشل في معالجة دفعة بقيمة {amount} ر.ي. السبب: {reason}",
                type=NotificationType.ERROR
            ),
            'account_suspended': NotificationTemplate(
                title_template="تم تعليق الحساب 🚫",
                message_template="تم تعليق حسابك مؤقتاً. السبب: {reason}. للاستفسار تواصل مع الدعم.",
                type=NotificationType.ERROR
            ),
            'role_changed': NotificationTemplate(
                title_template="تم تغيير صلاحيات الحساب 👤",
                message_template="تم تغيير دورك في النظام إلى: {new_role}",
                type=NotificationType.INFO
            )
        }
        
        # Start background tasks
        asyncio.create_task(self._process_notification_queue())
        asyncio.create_task(self._cleanup_old_notifications())
    
    async def create_notification(self, 
                                user_id: int,
                                title: str,
                                message: str,
                                notification_type: NotificationType = NotificationType.INFO,
                                metadata: Optional[Dict[str, Any]] = None,
                                send_immediately: bool = False) -> Optional[int]:
        """Create a new notification"""
        try:
            notification = Notification(
                user_id=user_id,
                title=title,
                message=message,
                type=notification_type,
                metadata=metadata or {},
                created_at=datetime.now()
            )
            
            if send_immediately:
                return await self._save_notification(notification)
            else:
                await self.notification_queue.put(notification)
                return None
                
        except Exception as e:
            self.logger.error(f"Error creating notification for user {user_id}: {e}")
            raise ValidationError(f"Failed to create notification: {e}")
    
    async def create_from_template(self,
                                 user_id: int,
                                 template_name: str,
                                 template_vars: Dict[str, Any],
                                 send_immediately: bool = False) -> Optional[int]:
        """Create notification from template"""
        if template_name not in self.templates:
            raise ValidationError(f"Template '{template_name}' not found")
        
        template = self.templates[template_name]
        title, message = template.format(**template_vars)
        
        return await self.create_notification(
            user_id=user_id,
            title=title,
            message=message,
            notification_type=template.type,
            metadata={'template': template_name, 'vars': template_vars},
            send_immediately=send_immediately
        )
    
    async def _save_notification(self, notification: Notification) -> int:
        """Save notification to database"""
        try:
            query = """
                INSERT INTO notifications (user_id, title, message, type, is_read, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """
            params = (
                notification.user_id,
                notification.title,
                notification.message,
                notification.type.value,
                notification.is_read,
                notification.created_at.isoformat()
            )
            
            notification_id = await self.db_manager.execute_query(query, params)
            
            # Trigger delivery callbacks
            await self._trigger_delivery_callbacks(notification_id, notification)
            
            return notification_id
            
        except Exception as e:
            self.logger.error(f"Error saving notification: {e}")
            raise DatabaseError(f"Failed to save notification: {e}")
    
    async def get_user_notifications(self,
                                   user_id: int,
                                   limit: int = 50,
                                   offset: int = 0,
                                   unread_only: bool = False) -> List[Dict[str, Any]]:
        """Get notifications for a user"""
        try:
            where_clause = "WHERE user_id = ?"
            params = [user_id]
            
            if unread_only:
                where_clause += " AND is_read = 0"
            
            query = f"""
                SELECT id, user_id, title, message, type, is_read, created_at
                FROM notifications
                {where_clause}
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            notifications = await self.db_manager.execute_query(query, tuple(params), fetch_all=True)
            return notifications or []
            
        except Exception as e:
            self.logger.error(f"Error getting notifications for user {user_id}: {e}")
            raise DatabaseError(f"Failed to get notifications: {e}")
    
    async def mark_as_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        try:
            query = """
                UPDATE notifications
                SET is_read = 1
                WHERE id = ? AND user_id = ?
            """
            await self.db_manager.execute_query(query, (notification_id, user_id))
            
            self.logger.info(f"Marked notification {notification_id} as read for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error marking notification as read: {e}")
            raise DatabaseError(f"Failed to mark notification as read: {e}")
    
    async def mark_all_as_read(self, user_id: int) -> int:
        """Mark all notifications as read for a user"""
        try:
            query = """
                UPDATE notifications
                SET is_read = 1
                WHERE user_id = ? AND is_read = 0
            """
            await self.db_manager.execute_query(query, (user_id,))
            
            # Get count of updated notifications
            count_query = "SELECT changes()"
            result = await self.db_manager.execute_query(count_query, fetch_one=True)
            count = result.get('changes()', 0) if result else 0
            
            self.logger.info(f"Marked {count} notifications as read for user {user_id}")
            return count
            
        except Exception as e:
            self.logger.error(f"Error marking all notifications as read: {e}")
            raise DatabaseError(f"Failed to mark notifications as read: {e}")
    
    async def delete_notification(self, notification_id: int, user_id: int) -> bool:
        """Delete a notification"""
        try:
            query = "DELETE FROM notifications WHERE id = ? AND user_id = ?"
            await self.db_manager.execute_query(query, (notification_id, user_id))
            
            self.logger.info(f"Deleted notification {notification_id} for user {user_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting notification: {e}")
            raise DatabaseError(f"Failed to delete notification: {e}")
    
    async def get_unread_count(self, user_id: int) -> int:
        """Get count of unread notifications for a user"""
        try:
            query = "SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0"
            result = await self.db_manager.execute_query(query, (user_id,), fetch_one=True)
            return result['count'] if result else 0
            
        except Exception as e:
            self.logger.error(f"Error getting unread count for user {user_id}: {e}")
            return 0
    
    async def broadcast_notification(self,
                                   title: str,
                                   message: str,
                                   notification_type: NotificationType = NotificationType.SYSTEM,
                                   user_roles: Optional[List[str]] = None,
                                   exclude_users: Optional[List[int]] = None) -> int:
        """Broadcast notification to multiple users"""
        try:
            # Get target users
            where_conditions = ["is_active = 1"]
            params = []
            
            if user_roles:
                role_placeholders = ','.join('?' * len(user_roles))
                where_conditions.append(f"role IN ({role_placeholders})")
                params.extend(user_roles)
            
            if exclude_users:
                exclude_placeholders = ','.join('?' * len(exclude_users))
                where_conditions.append(f"user_id NOT IN ({exclude_placeholders})")
                params.extend(exclude_users)
            
            query = f"""
                SELECT user_id FROM users
                WHERE {' AND '.join(where_conditions)}
            """
            
            users = await self.db_manager.execute_query(query, tuple(params), fetch_all=True)
            
            # Create notifications for all target users
            created_count = 0
            for user in users:
                await self.create_notification(
                    user_id=user['user_id'],
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    metadata={'broadcast': True},
                    send_immediately=True
                )
                created_count += 1
            
            self.logger.info(f"Broadcast notification sent to {created_count} users")
            return created_count
            
        except Exception as e:
            self.logger.error(f"Error broadcasting notification: {e}")
            raise DatabaseError(f"Failed to broadcast notification: {e}")
    
    async def register_delivery_callback(self, 
                                       notification_type: NotificationType,
                                       callback: Callable):
        """Register a callback for notification delivery"""
        if notification_type not in self.delivery_callbacks:
            self.delivery_callbacks[notification_type] = []
        
        self.delivery_callbacks[notification_type].append(callback)
        self.logger.info(f"Registered delivery callback for {notification_type.value}")
    
    async def _trigger_delivery_callbacks(self, notification_id: int, notification: Notification):
        """Trigger delivery callbacks for a notification"""
        callbacks = self.delivery_callbacks.get(notification.type, [])
        
        for callback in callbacks:
            try:
                await callback(notification_id, notification)
            except Exception as e:
                self.logger.error(f"Error in delivery callback: {e}")
    
    async def _process_notification_queue(self):
        """Process notifications from queue"""
        while True:
            try:
                # Process notifications in batches
                notifications = []
                
                # Collect up to 10 notifications or wait for timeout
                try:
                    for _ in range(10):
                        notification = await asyncio.wait_for(
                            self.notification_queue.get(),
                            timeout=5.0
                        )
                        notifications.append(notification)
                except asyncio.TimeoutError:
                    pass
                
                if notifications:
                    # Save notifications in batch
                    for notification in notifications:
                        await self._save_notification(notification)
                    
                    self.perf_logger.info(
                        f"Processed {len(notifications)} notifications",
                        extra={'batch_size': len(notifications)}
                    )
                
            except Exception as e:
                self.logger.error(f"Error processing notification queue: {e}")
                await asyncio.sleep(1)
    
    async def _cleanup_old_notifications(self):
        """Cleanup old read notifications"""
        while True:
            try:
                await asyncio.sleep(3600)  # Run every hour
                
                # Delete read notifications older than 30 days
                cutoff_date = datetime.now() - timedelta(days=30)
                
                query = """
                    DELETE FROM notifications
                    WHERE is_read = 1 AND created_at < ?
                """
                await self.db_manager.execute_query(query, (cutoff_date.isoformat(),))
                
                self.logger.info("Cleaned up old read notifications")
                
            except Exception as e:
                self.logger.error(f"Error cleaning up old notifications: {e}")
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        try:
            stats_query = """
                SELECT
                    COUNT(*) as total_notifications,
                    COUNT(CASE WHEN is_read = 0 THEN 1 END) as unread_notifications,
                    COUNT(CASE WHEN is_read = 1 THEN 1 END) as read_notifications,
                    COUNT(DISTINCT user_id) as users_with_notifications
                FROM notifications
            """
            
            stats = await self.db_manager.execute_query(stats_query, fetch_one=True)
            
            # Get notifications by type
            type_query = """
                SELECT type, COUNT(*) as count
                FROM notifications
                GROUP BY type
                ORDER BY count DESC
            """
            
            types = await self.db_manager.execute_query(type_query, fetch_all=True)
            
            # Get recent activity (last 24 hours)
            recent_query = """
                SELECT COUNT(*) as count
                FROM notifications
                WHERE created_at > datetime('now', '-24 hours')
            """
            
            recent = await self.db_manager.execute_query(recent_query, fetch_one=True)
            
            return {
                'total': stats['total_notifications'] if stats else 0,
                'unread': stats['unread_notifications'] if stats else 0,
                'read': stats['read_notifications'] if stats else 0,
                'users_with_notifications': stats['users_with_notifications'] if stats else 0,
                'recent_24h': recent['count'] if recent else 0,
                'by_type': {row['type']: row['count'] for row in types} if types else {},
                'queue_size': self.notification_queue.qsize(),
                'templates_available': len(self.templates)
            }
            
        except Exception as e:
            self.logger.error(f"Error getting notification stats: {e}")
            return {}
    
    # Convenience methods for common notification types
    async def notify_welcome(self, user_id: int, name: str):
        """Send welcome notification"""
        return await self.create_from_template(
            user_id=user_id,
            template_name='welcome',
            template_vars={'name': name},
            send_immediately=True
        )
    
    async def notify_balance_change(self, user_id: int, amount: float, new_balance: float, is_credit: bool = True):
        """Send balance change notification"""
        template_name = 'balance_credited' if is_credit else 'balance_debited'
        return await self.create_from_template(
            user_id=user_id,
            template_name=template_name,
            template_vars={'amount': amount, 'balance': new_balance},
            send_immediately=True
        )
    
    async def notify_card_purchase(self, user_id: int, card_type: str, amount: float, serial: str):
        """Send card purchase notification"""
        return await self.create_from_template(
            user_id=user_id,
            template_name='card_purchased',
            template_vars={'card_type': card_type, 'amount': amount, 'serial': serial},
            send_immediately=True
        )
    
    async def notify_low_balance(self, user_id: int, balance: float):
        """Send low balance warning"""
        return await self.create_from_template(
            user_id=user_id,
            template_name='low_balance',
            template_vars={'balance': balance},
            send_immediately=True
        )