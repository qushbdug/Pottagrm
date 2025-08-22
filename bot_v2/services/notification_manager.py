"""
Enhanced notification manager for multi-channel notifications
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from ..core.exceptions import BotException
from ..core.config import config, EMOJIS
from ..services.database_manager import db_manager

logger = logging.getLogger(__name__)

@dataclass
class NotificationTemplate:
    """Notification template"""
    name: str
    subject: str
    body: str
    variables: List[str] = field(default_factory=list)
    channel: str = "telegram"  # telegram, email, sms
    is_active: bool = True

@dataclass
class NotificationRequest:
    """Notification request"""
    user_id: int
    title: str
    message: str
    notification_type: str = "info"
    priority: str = "normal"  # low, normal, high, urgent
    channels: List[str] = field(default_factory=lambda: ["telegram"])
    metadata: Dict[str, Any] = field(default_factory=dict)
    scheduled_for: Optional[datetime] = None
    expires_at: Optional[datetime] = None

class NotificationManager:
    """Advanced notification manager with multiple channels"""
    
    def __init__(self):
        self.templates: Dict[str, NotificationTemplate] = {}
        self.notification_queue: asyncio.Queue = asyncio.Queue()
        self.processing_task = None
        self.is_running = False
        
        # Initialize templates
        self._init_templates()
        
        # Start processing
        self.start()
    
    def _init_templates(self):
        """Initialize notification templates"""
        self.templates = {
            'welcome': NotificationTemplate(
                name='welcome',
                subject='مرحباً بك في بوت يمن نت',
                body='مرحباً {user_name}! 🎉\n\nأهلاً وسهلاً بك في بوت يمن نت.\nنتمنى لك تجربة ممتعة!',
                variables=['user_name'],
                channel='telegram'
            ),
            'balance_update': NotificationTemplate(
                name='balance_update',
                subject='تحديث الرصيد',
                body='مرحباً {user_name}! 💰\n\nتم تحديث رصيدك:\nالرصيد السابق: {old_balance}\nالرصيد الجديد: {new_balance}\nالتغيير: {change_amount}',
                variables=['user_name', 'old_balance', 'new_balance', 'change_amount'],
                channel='telegram'
            ),
            'transfer_success': NotificationTemplate(
                name='transfer_success',
                subject='تم التحويل بنجاح',
                body='تم التحويل بنجاح! ✅\n\nالمبلغ: {amount}\nإلى: {recipient_name}\nالرصيد المتبقي: {remaining_balance}',
                variables=['amount', 'recipient_name', 'remaining_balance'],
                channel='telegram'
            ),
            'transfer_received': NotificationTemplate(
                name='transfer_received',
                subject='تم استلام تحويل',
                body='تم استلام تحويل جديد! 💸\n\nالمبلغ: {amount}\nمن: {sender_name}\nالرصيد الجديد: {new_balance}',
                variables=['amount', 'sender_name', 'new_balance'],
                channel='telegram'
            ),
            'card_purchased': NotificationTemplate(
                name='card_purchased',
                subject='تم شراء البطاقة',
                body='تم شراء البطاقة بنجاح! 💳\n\nنوع البطاقة: {card_type}\nالسعر: {price}\nالرصيد المتبقي: {remaining_balance}',
                variables=['card_type', 'price', 'remaining_balance'],
                channel='telegram'
            ),
            'commission_earned': NotificationTemplate(
                name='commission_earned',
                subject='عمولة جديدة',
                body='مبروك! 🎉\n\nلقد ربحت عمولة جديدة:\nالمبلغ: {amount}\nالنوع: {commission_type}\nالرصيد الجديد: {new_balance}',
                variables=['amount', 'commission_type', 'new_balance'],
                channel='telegram'
            ),
            'system_maintenance': NotificationTemplate(
                name='system_maintenance',
                subject='صيانة النظام',
                body='تنبيه: 🔧\n\nسيتم إجراء صيانة للنظام في {maintenance_time}.\nقد تواجه بعض الانقطاعات.\nشكراً لتفهمكم.',
                variables=['maintenance_time'],
                channel='telegram'
            ),
            'security_alert': NotificationTemplate(
                name='security_alert',
                subject='تنبيه أمني',
                body='تنبيه أمني! 🚨\n\nتم اكتشاف نشاط مشبوه على حسابك.\nيرجى التحقق من إعدادات الأمان.',
                variables=[],
                channel='telegram'
            )
        }
    
    def start(self):
        """Start notification processing"""
        if not self.is_running:
            self.is_running = True
            self.processing_task = asyncio.create_task(self._process_notifications())
            logger.info("Notification manager started")
    
    def stop(self):
        """Stop notification processing"""
        self.is_running = False
        if self.processing_task:
            self.processing_task.cancel()
        logger.info("Notification manager stopped")
    
    async def _process_notifications(self):
        """Process notifications from queue"""
        while self.is_running:
            try:
                # Get notification from queue
                notification = await asyncio.wait_for(
                    self.notification_queue.get(), 
                    timeout=1.0
                )
                
                # Process notification
                await self._send_notification(notification)
                
                # Mark as done
                self.notification_queue.task_done()
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                await asyncio.sleep(1)
    
    async def _send_notification(self, notification: NotificationRequest):
        """Send notification through specified channels"""
        try:
            # Check if notification is expired
            if notification.expires_at and datetime.now() > notification.expires_at:
                logger.info(f"Notification expired for user {notification.user_id}")
                return
            
            # Check if notification is scheduled for future
            if notification.scheduled_for and datetime.now() < notification.scheduled_for:
                # Re-queue for later
                await asyncio.sleep((notification.scheduled_for - datetime.now()).total_seconds())
                await self.notification_queue.put(notification)
                return
            
            # Send through each channel
            for channel in notification.channels:
                try:
                    if channel == "telegram":
                        await self._send_telegram_notification(notification)
                    elif channel == "email":
                        await self._send_email_notification(notification)
                    elif channel == "sms":
                        await self._send_sms_notification(notification)
                    else:
                        logger.warning(f"Unknown notification channel: {channel}")
                
                except Exception as e:
                    logger.error(f"Failed to send {channel} notification: {e}")
            
            # Save to database
            await self._save_notification_to_db(notification)
            
        except Exception as e:
            logger.error(f"Error sending notification: {e}")
    
    async def _send_telegram_notification(self, notification: NotificationRequest):
        """Send Telegram notification"""
        try:
            # Get user's Telegram ID
            user = await self._get_user_by_id(notification.user_id)
            if not user or not user.get('telegram_id'):
                logger.warning(f"No Telegram ID found for user {notification.user_id}")
                return
            
            # Get bot instance (this would need to be passed or accessed differently)
            # For now, we'll just log the notification
            logger.info(f"Telegram notification for user {notification.user_id}: {notification.title}")
            
            # TODO: Implement actual Telegram sending
            # await bot.send_message(
            #     chat_id=user['telegram_id'],
            #     text=f"{notification.title}\n\n{notification.message}"
            # )
            
        except Exception as e:
            logger.error(f"Error sending Telegram notification: {e}")
    
    async def _send_email_notification(self, notification: NotificationRequest):
        """Send email notification"""
        try:
            if not config.notification.enable_email:
                logger.info("Email notifications are disabled")
                return
            
            # Get user's email
            user = await self._get_user_by_id(notification.user_id)
            if not user or not user.get('email'):
                logger.warning(f"No email found for user {notification.user_id}")
                return
            
            # Create email message
            msg = MIMEMultipart()
            msg['From'] = config.notification.smtp_username
            msg['To'] = user['email']
            msg['Subject'] = notification.title
            
            # Add body
            body = f"{notification.message}\n\nتم إرسال هذا الإشعار من بوت يمن نت"
            msg.attach(MIMEText(body, 'plain', 'utf-8'))
            
            # Send email
            with smtplib.SMTP(config.notification.smtp_server, config.notification.smtp_port) as server:
                server.starttls()
                server.login(config.notification.smtp_username, config.notification.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Email notification sent to {user['email']}")
            
        except Exception as e:
            logger.error(f"Error sending email notification: {e}")
    
    async def _send_sms_notification(self, notification: NotificationRequest):
        """Send SMS notification"""
        try:
            if not config.notification.enable_sms:
                logger.info("SMS notifications are disabled")
                return
            
            # Get user's phone number
            user = await self._get_user_by_id(notification.user_id)
            if not user or not user.get('phone'):
                logger.warning(f"No phone number found for user {notification.user_id}")
                return
            
            # TODO: Implement SMS sending service
            logger.info(f"SMS notification for user {notification.user_id}: {notification.title}")
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {e}")
    
    async def _save_notification_to_db(self, notification: NotificationRequest):
        """Save notification to database"""
        try:
            query = '''
                INSERT INTO notifications (user_id, title, message, type, created_at)
                VALUES (?, ?, ?, ?, ?)
            '''
            
            await db_manager.execute_query(query, (
                notification.user_id,
                notification.title,
                notification.message,
                notification.notification_type,
                datetime.now().isoformat()
            ))
            
        except Exception as e:
            logger.error(f"Error saving notification to database: {e}")
    
    async def _get_user_by_id(self, user_id: int) -> Optional[Dict]:
        """Get user by ID from database"""
        try:
            query = 'SELECT * FROM users WHERE id = ?'
            results = await db_manager.execute_query(query, (user_id,))
            return results[0] if results else None
        except Exception as e:
            logger.error(f"Error getting user {user_id}: {e}")
            return None
    
    async def send_notification(self, notification: NotificationRequest):
        """Send notification asynchronously"""
        await self.notification_queue.put(notification)
    
    def send_notification_sync(self, notification: NotificationRequest):
        """Send notification synchronously"""
        asyncio.create_task(self.send_notification(notification))
    
    async def send_template_notification(
        self,
        template_name: str,
        user_id: int,
        variables: Dict[str, Any],
        channels: List[str] = None,
        priority: str = "normal"
    ):
        """Send notification using template"""
        try:
            template = self.templates.get(template_name)
            if not template:
                logger.error(f"Template not found: {template_name}")
                return
            
            # Format message with variables
            try:
                formatted_subject = template.subject.format(**variables)
                formatted_body = template.body.format(**variables)
            except KeyError as e:
                logger.error(f"Missing variable in template {template_name}: {e}")
                return
            
            # Create notification request
            notification = NotificationRequest(
                user_id=user_id,
                title=formatted_subject,
                message=formatted_body,
                notification_type="template",
                priority=priority,
                channels=channels or [template.channel]
            )
            
            # Send notification
            await self.send_notification(notification)
            
        except Exception as e:
            logger.error(f"Error sending template notification: {e}")
    
    async def send_bulk_notification(
        self,
        user_ids: List[int],
        title: str,
        message: str,
        notification_type: str = "bulk",
        channels: List[str] = None
    ):
        """Send notification to multiple users"""
        try:
            for user_id in user_ids:
                notification = NotificationRequest(
                    user_id=user_id,
                    title=title,
                    message=message,
                    notification_type=notification_type,
                    channels=channels or ["telegram"]
                )
                await self.send_notification(notification)
            
            logger.info(f"Bulk notification sent to {len(user_ids)} users")
            
        except Exception as e:
            logger.error(f"Error sending bulk notification: {e}")
    
    async def send_admin_notification(
        self,
        title: str,
        message: str,
        notification_type: str = "admin"
    ):
        """Send notification to all admin users"""
        try:
            # Get admin users
            query = 'SELECT id FROM users WHERE role IN ("admin", "super_admin") AND is_active = 1'
            results = await db_manager.execute_query(query)
            
            admin_ids = [user['id'] for user in results]
            
            if admin_ids:
                await self.send_bulk_notification(
                    admin_ids,
                    title,
                    message,
                    notification_type,
                    ["telegram"]
                )
            
        except Exception as e:
            logger.error(f"Error sending admin notification: {e}")
    
    async def get_user_notifications(
        self,
        user_id: int,
        limit: int = 20,
        unread_only: bool = False
    ) -> List[Dict]:
        """Get user's notifications"""
        try:
            query = '''
                SELECT * FROM notifications 
                WHERE user_id = ?
                {}
                ORDER BY created_at DESC
                LIMIT ?
            '''.format("AND is_read = 0" if unread_only else "")
            
            results = await db_manager.execute_query(query, (user_id, limit))
            return results
            
        except Exception as e:
            logger.error(f"Error getting user notifications: {e}")
            return []
    
    async def mark_notification_read(self, notification_id: int, user_id: int) -> bool:
        """Mark notification as read"""
        try:
            query = '''
                UPDATE notifications 
                SET is_read = 1 
                WHERE id = ? AND user_id = ?
            '''
            
            result = await db_manager.execute_query(query, (notification_id, user_id))
            return True
            
        except Exception as e:
            logger.error(f"Error marking notification as read: {e}")
            return False
    
    async def mark_all_notifications_read(self, user_id: int) -> bool:
        """Mark all user notifications as read"""
        try:
            query = '''
                UPDATE notifications 
                SET is_read = 1 
                WHERE user_id = ?
            '''
            
            await db_manager.execute_query(query, (user_id,))
            return True
            
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {e}")
            return False
    
    async def delete_old_notifications(self, days: int = 30) -> int:
        """Delete old notifications"""
        try:
            query = '''
                DELETE FROM notifications 
                WHERE created_at < datetime('now', '-{} days')
            '''.format(days)
            
            result = await db_manager.execute_query(query)
            deleted_count = result[0]['affected_rows'] if result else 0
            
            logger.info(f"Deleted {deleted_count} old notifications")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error deleting old notifications: {e}")
            return 0
    
    def get_templates(self) -> Dict[str, NotificationTemplate]:
        """Get all notification templates"""
        return self.templates.copy()
    
    def add_template(self, template: NotificationTemplate):
        """Add new notification template"""
        self.templates[template.name] = template
        logger.info(f"Added notification template: {template.name}")
    
    def remove_template(self, template_name: str):
        """Remove notification template"""
        if template_name in self.templates:
            del self.templates[template_name]
            logger.info(f"Removed notification template: {template_name}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get notification manager statistics"""
        return {
            'queue_size': self.notification_queue.qsize(),
            'is_running': self.is_running,
            'templates_count': len(self.templates),
            'active_templates': len([t for t in self.templates.values() if t.is_active])
        }

# Global notification manager instance
notification_manager = NotificationManager()

# Convenience functions
async def send_notification(
    user_id: int,
    title: str,
    message: str,
    notification_type: str = "info",
    channels: List[str] = None
):
    """Send notification to user"""
    notification = NotificationRequest(
        user_id=user_id,
        title=title,
        message=message,
        notification_type=notification_type,
        channels=channels or ["telegram"]
    )
    await notification_manager.send_notification(notification)

async def send_template_notification(
    template_name: str,
    user_id: int,
    variables: Dict[str, Any],
    channels: List[str] = None
):
    """Send template notification to user"""
    await notification_manager.send_template_notification(
        template_name, user_id, variables, channels
    )

async def send_admin_notification(title: str, message: str):
    """Send notification to all admins"""
    await notification_manager.send_admin_notification(title, message)

async def send_bulk_notification(
    user_ids: List[int],
    title: str,
    message: str
):
    """Send notification to multiple users"""
    await notification_manager.send_bulk_notification(user_ids, title, message)