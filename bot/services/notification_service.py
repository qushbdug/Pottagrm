"""
خدمة الإشعارات المتقدمة
"""

import logging
import asyncio
from typing import Optional, List, Dict
from telegram import Bot
from bot.database.connection import db_manager
from bot.config import BOT_TOKEN, NOTIFICATION_CHANNELS, ENABLE_PUSH_NOTIFICATIONS

logger = logging.getLogger(__name__)

class NotificationService:
    """خدمة إدارة الإشعارات"""
    
    def __init__(self):
        self.bot = Bot(token=BOT_TOKEN)
    
    async def send_push_notification(self, user_id: int, title: str, message: str, 
                                   notification_type: str = "info") -> bool:
        """إرسال إشعار push للمستخدم"""
        
        if not ENABLE_PUSH_NOTIFICATIONS:
            return False
        
        try:
            # حفظ الإشعار في قاعدة البيانات
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    INSERT INTO notifications (user_id, title, message, type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, title, message, notification_type))
                
                # الحصول على telegram_id للمستخدم
                cursor.execute('SELECT telegram_id FROM users WHERE id = ?', (user_id,))
                user_row = cursor.fetchone()
                
                if not user_row:
                    return False
                
                telegram_id = user_row[0]
            
            # إرسال الإشعار عبر تليجرام
            notification_text = f"🔔 {title}\n\n{message}"
            await self.bot.send_message(chat_id=telegram_id, text=notification_text)
            
            logger.info(f"تم إرسال إشعار push للمستخدم {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إرسال الإشعار: {e}")
            return False
    
    async def send_bulk_notification(self, user_ids: List[int], title: str, 
                                   message: str, notification_type: str = "info") -> Dict:
        """إرسال إشعار جماعي"""
        
        successful = 0
        failed = 0
        
        for user_id in user_ids:
            success = await self.send_push_notification(user_id, title, message, notification_type)
            if success:
                successful += 1
            else:
                failed += 1
            
            # توقف قصير لتجنب الـ rate limiting
            await asyncio.sleep(0.1)
        
        return {
            'total': len(user_ids),
            'successful': successful,
            'failed': failed
        }
    
    async def send_admin_notification(self, title: str, message: str, 
                                    notification_type: str = "admin") -> bool:
        """إرسال إشعار للمديرين"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # جلب جميع المديرين
                cursor.execute('''
                    SELECT id FROM users 
                    WHERE role IN ('مدير', 'مدير عام') AND is_active = 1
                ''')
                
                admin_ids = [row[0] for row in cursor.fetchall()]
            
            if not admin_ids:
                return False
            
            # إرسال للمديرين
            result = await self.send_bulk_notification(admin_ids, title, message, notification_type)
            
            # إرسال لقناة المديرين إذا كانت متوفرة
            if NOTIFICATION_CHANNELS.get('admin'):
                try:
                    notification_text = f"🚨 إشعار إداري\n\n📋 {title}\n\n{message}"
                    await self.bot.send_message(
                        chat_id=NOTIFICATION_CHANNELS['admin'],
                        text=notification_text
                    )
                except Exception as e:
                    logger.warning(f"فشل إرسال الإشعار لقناة المديرين: {e}")
            
            return result['successful'] > 0
            
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار المديرين: {e}")
            return False
    
    async def send_channel_notification(self, title: str, message: str, 
                                      channel_type: str = "general") -> bool:
        """إرسال إشعار للقناة العامة"""
        
        channel = NOTIFICATION_CHANNELS.get(channel_type)
        if not channel:
            return False
        
        try:
            notification_text = f"📢 {title}\n\n{message}"
            await self.bot.send_message(chat_id=channel, text=notification_text)
            return True
            
        except Exception as e:
            logger.error(f"خطأ في إرسال إشعار القناة: {e}")
            return False
    
    def get_user_notifications(self, user_id: int, limit: int = 20, 
                             unread_only: bool = False) -> List[Dict]:
        """جلب إشعارات المستخدم"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                query = '''
                    SELECT id, title, message, type, is_read, created_at
                    FROM notifications
                    WHERE user_id = ?
                '''
                params = [user_id]
                
                if unread_only:
                    query += ' AND is_read = 0'
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                
                notifications = []
                for row in cursor.fetchall():
                    notifications.append({
                        'id': row[0],
                        'title': row[1],
                        'message': row[2],
                        'type': row[3],
                        'is_read': bool(row[4]),
                        'created_at': row[5]
                    })
                
                return notifications
                
        except Exception as e:
            logger.error(f"خطأ في جلب الإشعارات: {e}")
            return []
    
    def mark_notification_as_read(self, notification_id: int, user_id: int) -> bool:
        """تحديد الإشعار كمقروء"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    UPDATE notifications 
                    SET is_read = 1 
                    WHERE id = ? AND user_id = ?
                ''', (notification_id, user_id))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الإشعار: {e}")
            return False
    
    def mark_all_notifications_as_read(self, user_id: int) -> bool:
        """تحديد جميع الإشعارات كمقروءة"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    UPDATE notifications 
                    SET is_read = 1 
                    WHERE user_id = ? AND is_read = 0
                ''', (user_id,))
                
                return cursor.rowcount > 0
                
        except Exception as e:
            logger.error(f"خطأ في تحديث الإشعارات: {e}")
            return False
    
    def get_unread_count(self, user_id: int) -> int:
        """عدد الإشعارات غير المقروءة"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    SELECT COUNT(*) FROM notifications 
                    WHERE user_id = ? AND is_read = 0
                ''', (user_id,))
                
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"خطأ في حساب الإشعارات غير المقروءة: {e}")
            return 0

# إنشاء مثيل عام لخدمة الإشعارات
notification_service = NotificationService()