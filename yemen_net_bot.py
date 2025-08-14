import logging
import sqlite3
import uuid
import csv
import io
import re
import os
import random
import json
import base64
import asyncio
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timedelta, date

# Cryptography import (optional for enhanced security)
try:
    from cryptography.fernet import Fernet
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    Fernet = None

# Optional imports for enhanced features
try:
    import aiofiles
    AIOFILES_AVAILABLE = True
except ImportError:
    AIOFILES_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False

try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False

try:
    from PIL import Image
    import qrcode
    IMAGE_AVAILABLE = True
except ImportError:
    IMAGE_AVAILABLE = False
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    BotCommand,
    MenuButtonCommands,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    ConversationHandler,
    PicklePersistence,
    filters,
)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Bot configuration
BOT_TOKEN = '7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0'
DB_PATH = os.getenv('DB_PATH', os.path.abspath('yemen_net.db'))

# Accounting constants
ACCOUNT_TYPE_ASSET = 'asset'
ACCOUNT_TYPE_LIABILITY = 'liability'
ACCOUNT_TYPE_EQUITY = 'equity'
ACCOUNT_TYPE_REVENUE = 'revenue'
ACCOUNT_TYPE_EXPENSE = 'expense'
ACCOUNT_CODE_ISSUANCE_EXPENSE = '5000'
ACCOUNT_CODE_BOT_COMMISSION_REVENUE = '4100'

# Business configuration
CARD_COMMISSION_RATE = float(os.getenv('CARD_COMMISSION_RATE', '0.10'))
AGENT_COMMISSION_RATE = float(os.getenv('AGENT_COMMISSION_RATE', '0.05'))

# Bot command menu
QUICK_COMMANDS = [
    BotCommand('start', '🏠 القائمة الرئيسية'),
    BotCommand('menu', '📋 القائمة السريعة'),
    BotCommand('balance', '💳 عرض الرصيد'),
    BotCommand('buy', '🛒 شراء كرت'),
    BotCommand('transfer', '💸 تحويل رصيد'),
    BotCommand('stats', '📊 الإحصائيات'),
    BotCommand('help', '❓ المساعدة'),
]

# Emojis for better UI
EMOJIS = {
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'loading': '⏳',
    'money': '💰',
    'card': '🎫',
    'network': '📶',
    'user': '👤',
    'admin': '👑',
    'stats': '📊',
    'home': '🏠',
    'back': '↩️',
    'cancel': '❌',
    'confirm': '✅',
    'search': '🔍',
    'settings': '⚙️',
    'wallet': '💳',
    'transfer': '💸',
    'purchase': '🛒',
    'upload': '📤',
    'download': '📥',
    'phone': '📱',
    'email': '📧',
    'id': '🆔',
    'time': '⏰',
    'date': '📅',
    'star': '⭐',
    'fire': '🔥',
    'new': '🆕',
    'hot': '🔥',
    'cool': '😎'
}

# Enhanced utility functions for new features
def log_activity(user_id: int, activity_type: str, description: str, metadata: dict = None):
    """Log user activity for enhanced tracking"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        activity_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO activity_logs (id, user_id, activity_type, description, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (activity_id, user_id, activity_type, description, metadata_json))
        
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging activity: {e}")

def create_wallet_transaction(user_id: int, transaction_type: str, amount: float, 
                            balance_before: float, balance_after: float, 
                            description: str = None, reference_id: str = None,
                            metadata: dict = None) -> str:
    """Create a wallet transaction record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        transaction_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO wallet_transactions 
            (id, user_id, transaction_type, amount, balance_before, balance_after, 
             reference_id, description, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, user_id, transaction_type, amount, balance_before, 
              balance_after, reference_id, description, metadata_json))
        
        conn.commit()
        conn.close()
        return transaction_id
    except Exception as e:
        logger.error(f"Error creating wallet transaction: {e}")
        return None

def send_smart_notification(user_id: int, notification_type: str, title: str, 
                          message: str, priority: str = 'normal', 
                          metadata: dict = None) -> str:
    """Send a smart notification to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check user notification preferences
        cursor.execute('''
            SELECT * FROM notification_preferences WHERE user_id = ?
        ''', (user_id,))
        prefs = cursor.fetchone()
        
        # Default preferences if not set
        if not prefs:
            cursor.execute('''
                INSERT INTO notification_preferences (user_id) VALUES (?)
            ''', (user_id,))
            conn.commit()
        
        notification_id = str(uuid.uuid4())
        metadata_json = json.dumps(metadata) if metadata else None
        
        cursor.execute('''
            INSERT INTO smart_notifications 
            (id, user_id, notification_type, title, message, priority, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (notification_id, user_id, notification_type, title, message, 
              priority, metadata_json))
        
        conn.commit()
        conn.close()
        return notification_id
    except Exception as e:
        logger.error(f"Error sending smart notification: {e}")
        return None

def calculate_user_rating(user_id: int) -> Dict:
    """Calculate and update user rating summary"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT rating, COUNT(*) as count FROM ratings 
            WHERE rated_user_id = ? AND is_visible = 1
            GROUP BY rating
        ''', (user_id,))
        
        rating_counts = {i: 0 for i in range(1, 6)}
        total_ratings = 0
        total_score = 0
        
        for rating, count in cursor.fetchall():
            rating_counts[rating] = count
            total_ratings += count
            total_score += rating * count
        
        average_rating = total_score / total_ratings if total_ratings > 0 else 0.0
        
        # Update or insert rating summary
        cursor.execute('''
            INSERT OR REPLACE INTO user_ratings_summary 
            (user_id, total_ratings, average_rating, rating_1_count, rating_2_count,
             rating_3_count, rating_4_count, rating_5_count, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (user_id, total_ratings, average_rating, rating_counts[1], 
              rating_counts[2], rating_counts[3], rating_counts[4], 
              rating_counts[5], datetime.now()))
        
        conn.commit()
        conn.close()
        
        return {
            'total_ratings': total_ratings,
            'average_rating': round(average_rating, 2),
            'rating_distribution': rating_counts
        }
    except Exception as e:
        logger.error(f"Error calculating user rating: {e}")
        return {'total_ratings': 0, 'average_rating': 0.0, 'rating_distribution': {}}

def update_inventory_stock(network_id: str, category_id: int, change: int) -> bool:
    """Update inventory stock count"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        inventory_id = f"{network_id}_{category_id}"
        
        cursor.execute('''
            INSERT OR IGNORE INTO product_inventory 
            (id, network_id, category_id, stock_count)
            VALUES (?, ?, ?, 0)
        ''', (inventory_id, network_id, category_id))
        
        cursor.execute('''
            UPDATE product_inventory 
            SET stock_count = stock_count + ?, last_updated = ?
            WHERE id = ?
        ''', (change, datetime.now(), inventory_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error updating inventory: {e}")
        return False

def check_low_stock_alerts():
    """Check for low stock items and send alerts"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT pi.*, n.name as network_name, cc.category_name, cc.value
            FROM product_inventory pi
            JOIN networks n ON pi.network_id = n.id
            JOIN card_categories cc ON pi.category_id = cc.id
            WHERE pi.stock_count <= pi.low_stock_threshold
        ''')
        
        low_stock_items = cursor.fetchall()
        
        for item in low_stock_items:
            # Send alert to suppliers and admins
            cursor.execute('''
                SELECT id FROM users WHERE role IN ('supplier', 'admin', 'superadmin')
            ''')
            
            for user in cursor.fetchall():
                send_smart_notification(
                    user[0], 
                    'low_stock_alert',
                    f'⚠️ تنبيه نقص مخزون',
                    f'المخزون منخفض لـ {item["network_name"]} - {item["category_name"]} ({item["value"]} ريال)\n'
                    f'الكمية المتبقية: {item["stock_count"]}',
                    'high'
                )
        
        conn.close()
        return len(low_stock_items)
    except Exception as e:
        logger.error(f"Error checking low stock: {e}")
        return 0

async def generate_sales_report(report_type: str, start_date: date, end_date: date, 
                              user_id: int) -> Dict:
    """Generate comprehensive sales report"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get sales data
        cursor.execute('''
            SELECT t.*, u.full_name, n.name as network_name
            FROM transactions t
            JOIN users u ON t.from_user = u.id
            LEFT JOIN cards c ON t.reference_id = c.id
            LEFT JOIN card_categories cc ON c.category_id = cc.id
            LEFT JOIN networks n ON cc.network_id = n.id
            WHERE DATE(t.created_at) BETWEEN ? AND ?
            AND t.type = 'purchase'
        ''', (start_date, end_date))
        
        transactions = cursor.fetchall()
        
        # Calculate metrics
        total_sales = sum(t['amount'] for t in transactions)
        total_transactions = len(transactions)
        
        # Calculate commissions
        cursor.execute('''
            SELECT SUM(amount) as total_commission
            FROM transactions
            WHERE DATE(created_at) BETWEEN ? AND ?
            AND type = 'commission'
        ''', (start_date, end_date))
        
        commission_result = cursor.fetchone()
        total_commission = commission_result['total_commission'] if commission_result['total_commission'] else 0
        
        # Network breakdown
        network_sales = {}
        for t in transactions:
            network = t['network_name'] or 'غير محدد'
            if network not in network_sales:
                network_sales[network] = {'count': 0, 'amount': 0}
            network_sales[network]['count'] += 1
            network_sales[network]['amount'] += t['amount']
        
        report_data = {
            'total_sales': total_sales,
            'total_commission': total_commission,
            'total_transactions': total_transactions,
            'network_breakdown': network_sales,
            'period': f"{start_date} - {end_date}",
            'generated_at': datetime.now().isoformat()
        }
        
        # Save report
        report_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO sales_reports 
            (id, report_type, start_date, end_date, total_sales, total_commission,
             total_transactions, generated_by, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (report_id, report_type, start_date, end_date, total_sales,
              total_commission, total_transactions, user_id, json.dumps(report_data)))
        
        conn.commit()
        conn.close()
        
        return report_data
    except Exception as e:
        logger.error(f"Error generating sales report: {e}")
        return {}

def get_user_permissions(user_id: int) -> List[str]:
    """Get user permissions list"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT permission_name FROM user_permissions
            WHERE user_id = ? AND is_active = 1
            AND (expires_at IS NULL OR expires_at > ?)
        ''', (user_id, datetime.now()))
        
        permissions = [row[0] for row in cursor.fetchall()]
        conn.close()
        return permissions
    except Exception as e:
        logger.error(f"Error getting user permissions: {e}")
        return []

def has_permission(user_id: int, permission: str) -> bool:
    """Check if user has specific permission"""
    permissions = get_user_permissions(user_id)
    return permission in permissions

def grant_user_permission(user_id: int, permission: str, granted_by: int, expires_at: datetime = None) -> bool:
    """Grant a permission to a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if permission already exists
        cursor.execute('''
            SELECT id FROM user_permissions
            WHERE user_id = ? AND permission_name = ? AND is_active = 1
        ''', (user_id, permission))
        
        if cursor.fetchone():
            conn.close()
            return False  # Permission already exists
        
        cursor.execute('''
            INSERT INTO user_permissions (user_id, permission_name, granted_by, expires_at)
            VALUES (?, ?, ?, ?)
        ''', (user_id, permission, granted_by, expires_at))
        
        conn.commit()
        conn.close()
        
        # Log the permission grant
        log_activity(granted_by, 'permission_grant', f'Granted permission {permission} to user {user_id}')
        
        return True
    except Exception as e:
        logger.error(f"Error granting permission: {e}")
        return False

def revoke_user_permission(user_id: int, permission: str, revoked_by: int) -> bool:
    """Revoke a permission from a user"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE user_permissions 
            SET is_active = 0
            WHERE user_id = ? AND permission_name = ? AND is_active = 1
        ''', (user_id, permission))
        
        if cursor.rowcount > 0:
            conn.commit()
            log_activity(revoked_by, 'permission_revoke', f'Revoked permission {permission} from user {user_id}')
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Error revoking permission: {e}")
        return False

def get_user_activity_summary(user_id: int, days: int = 30) -> Dict:
    """Get user activity summary for the last N days"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        since_date = datetime.now() - timedelta(days=days)
        
        # Get activity counts by type
        cursor.execute('''
            SELECT activity_type, COUNT(*) as count
            FROM activity_logs
            WHERE user_id = ? AND created_at >= ?
            GROUP BY activity_type
        ''', (user_id, since_date))
        
        activity_counts = {row['activity_type']: row['count'] for row in cursor.fetchall()}
        
        # Get recent activities
        cursor.execute('''
            SELECT * FROM activity_logs
            WHERE user_id = ? AND created_at >= ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user_id, since_date))
        
        recent_activities = cursor.fetchall()
        
        # Get login statistics
        cursor.execute('''
            SELECT COUNT(DISTINCT DATE(created_at)) as active_days
            FROM activity_logs
            WHERE user_id = ? AND created_at >= ?
        ''', (user_id, since_date))
        
        active_days = cursor.fetchone()['active_days']
        
        conn.close()
        
        return {
            'activity_counts': activity_counts,
            'recent_activities': recent_activities,
            'active_days': active_days,
            'period_days': days
        }
    except Exception as e:
        logger.error(f"Error getting user activity summary: {e}")
        return {}

def update_user_role(user_id: int, new_role: str, updated_by: int) -> bool:
    """Update user role with proper validation"""
    try:
        valid_roles = ['customer', 'agent', 'supplier', 'admin', 'super_admin']
        if new_role not in valid_roles:
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get current role
        cursor.execute('SELECT role FROM users WHERE id = ?', (user_id,))
        current_role = cursor.fetchone()
        
        if not current_role:
            conn.close()
            return False
        
        old_role = current_role['role']
        
        # Update role
        cursor.execute('''
            UPDATE users SET role = ? WHERE id = ?
        ''', (new_role, user_id))
        
        conn.commit()
        conn.close()
        
        # Log role change
        log_activity(updated_by, 'role_change', f'Changed user {user_id} role from {old_role} to {new_role}')
        
        # Send notification to user
        send_smart_notification(
            user_id,
            'role_change',
            '🔄 تغيير الدور',
            f'تم تغيير دورك من {old_role} إلى {new_role}',
            'high'
        )
        
        return True
    except Exception as e:
        logger.error(f"Error updating user role: {e}")
        return False

def get_users_by_role(role: str, active_only: bool = True) -> List[Dict]:
    """Get all users with a specific role"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        query = 'SELECT * FROM users WHERE role = ?'
        params = [role]
        
        if active_only:
            query += ' AND is_active = 1'
        
        cursor.execute(query, params)
        users = cursor.fetchall()
        
        conn.close()
        return users
    except Exception as e:
        logger.error(f"Error getting users by role: {e}")
        return []

def suspend_user(user_id: int, suspended_by: int, reason: str = None) -> bool:
    """Suspend a user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET is_active = 0 WHERE id = ?
        ''', (user_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            
            # Log suspension
            log_activity(suspended_by, 'user_suspension', f'Suspended user {user_id}. Reason: {reason or "Not specified"}')
            
            # Send notification
            send_smart_notification(
                user_id,
                'account_suspended',
                '🚫 تم تعليق الحساب',
                f'تم تعليق حسابك. السبب: {reason or "غير محدد"}',
                'high'
            )
            
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Error suspending user: {e}")
        return False

def activate_user(user_id: int, activated_by: int) -> bool:
    """Activate a user account"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET is_active = 1 WHERE id = ?
        ''', (user_id,))
        
        if cursor.rowcount > 0:
            conn.commit()
            
            # Log activation
            log_activity(activated_by, 'user_activation', f'Activated user {user_id}')
            
            # Send notification
            send_smart_notification(
                user_id,
                'account_activated',
                '✅ تم تفعيل الحساب',
                'تم تفعيل حسابك بنجاح. يمكنك الآن استخدام جميع الخدمات.',
                'normal'
            )
            
            conn.close()
            return True
        
        conn.close()
        return False
    except Exception as e:
        logger.error(f"Error activating user: {e}")
        return False

# Advanced Reporting and Analytics Functions

async def generate_comprehensive_report(report_type: str, start_date: date, end_date: date, 
                                      user_id: int, filters: dict = None) -> Dict:
    """Generate comprehensive business reports"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        report_data = {
            'report_type': report_type,
            'period': f"{start_date} to {end_date}",
            'generated_by': user_id,
            'generated_at': datetime.now().isoformat(),
            'filters_applied': filters or {}
        }
        
        if report_type == 'sales_overview':
            # Sales Overview Report
            cursor.execute('''
                SELECT 
                    COUNT(*) as total_transactions,
                    SUM(amount) as total_revenue,
                    AVG(amount) as avg_transaction,
                    COUNT(DISTINCT from_user) as unique_customers
                FROM transactions 
                WHERE type = 'purchase' 
                AND DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date))
            
            overview = cursor.fetchone()
            
            # Revenue by network
            cursor.execute('''
                SELECT n.name, COUNT(*) as sales_count, SUM(t.amount) as revenue
                FROM transactions t
                JOIN cards c ON t.reference_id = c.id
                JOIN card_categories cc ON c.category_id = cc.id
                JOIN networks n ON cc.network_id = n.id
                WHERE t.type = 'purchase' AND DATE(t.created_at) BETWEEN ? AND ?
                GROUP BY n.name
                ORDER BY revenue DESC
            ''', (start_date, end_date))
            
            network_sales = cursor.fetchall()
            
            # Daily sales trend
            cursor.execute('''
                SELECT DATE(created_at) as sale_date, 
                       COUNT(*) as daily_sales,
                       SUM(amount) as daily_revenue
                FROM transactions 
                WHERE type = 'purchase' AND DATE(created_at) BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                ORDER BY sale_date
            ''', (start_date, end_date))
            
            daily_trends = cursor.fetchall()
            
            report_data.update({
                'overview': overview,
                'network_sales': network_sales,
                'daily_trends': daily_trends
            })
            
        elif report_type == 'user_analytics':
            # User Analytics Report
            cursor.execute('''
                SELECT role, COUNT(*) as user_count, 
                       COUNT(CASE WHEN is_active = 1 THEN 1 END) as active_count
                FROM users 
                GROUP BY role
            ''')
            user_distribution = cursor.fetchall()
            
            # User registration trends
            cursor.execute('''
                SELECT DATE(created_at) as reg_date, COUNT(*) as new_users
                FROM users 
                WHERE DATE(created_at) BETWEEN ? AND ?
                GROUP BY DATE(created_at)
                ORDER BY reg_date
            ''', (start_date, end_date))
            registration_trends = cursor.fetchall()
            
            # Most active users
            cursor.execute('''
                SELECT u.full_name, u.role, 
                       COUNT(t.id) as transaction_count,
                       SUM(t.amount) as total_spent
                FROM users u
                LEFT JOIN transactions t ON u.id = t.from_user AND t.type = 'purchase'
                WHERE DATE(t.created_at) BETWEEN ? AND ?
                GROUP BY u.id
                ORDER BY transaction_count DESC
                LIMIT 10
            ''', (start_date, end_date))
            active_users = cursor.fetchall()
            
            report_data.update({
                'user_distribution': user_distribution,
                'registration_trends': registration_trends,
                'most_active_users': active_users
            })
            
        elif report_type == 'financial_summary':
            # Financial Summary Report
            cursor.execute('''
                SELECT 
                    SUM(CASE WHEN type = 'purchase' THEN amount ELSE 0 END) as total_sales,
                    SUM(CASE WHEN type = 'commission' THEN amount ELSE 0 END) as total_commissions,
                    SUM(CASE WHEN type = 'transfer' THEN amount ELSE 0 END) as total_transfers,
                    SUM(CASE WHEN type = 'recharge' THEN amount ELSE 0 END) as total_recharges
                FROM transactions 
                WHERE DATE(created_at) BETWEEN ? AND ?
            ''', (start_date, end_date))
            financial_overview = cursor.fetchone()
            
            # Revenue breakdown by role
            cursor.execute('''
                SELECT u.role, SUM(t.amount) as revenue
                FROM transactions t
                JOIN users u ON t.from_user = u.id
                WHERE t.type = 'purchase' AND DATE(t.created_at) BETWEEN ? AND ?
                GROUP BY u.role
            ''', (start_date, end_date))
            revenue_by_role = cursor.fetchall()
            
            report_data.update({
                'financial_overview': financial_overview,
                'revenue_by_role': revenue_by_role
            })
            
        elif report_type == 'inventory_status':
            # Inventory Status Report
            cursor.execute('''
                SELECT n.name as network_name, cc.value, cc.category_name,
                       COUNT(c.id) as total_cards,
                       COUNT(CASE WHEN c.is_used = 0 THEN 1 END) as available_cards,
                       COUNT(CASE WHEN c.is_used = 1 THEN 1 END) as sold_cards
                FROM networks n
                JOIN card_categories cc ON n.id = cc.network_id
                LEFT JOIN cards c ON cc.id = c.category_id
                GROUP BY n.id, cc.id
                ORDER BY n.name, cc.value
            ''')
            inventory_status = cursor.fetchall()
            
            # Low stock alerts
            cursor.execute('''
                SELECT n.name, cc.value, COUNT(c.id) as remaining_stock
                FROM networks n
                JOIN card_categories cc ON n.id = cc.network_id
                LEFT JOIN cards c ON cc.id = c.category_id AND c.is_used = 0
                GROUP BY n.id, cc.id
                HAVING remaining_stock < 10
                ORDER BY remaining_stock ASC
            ''')
            low_stock_items = cursor.fetchall()
            
            report_data.update({
                'inventory_status': inventory_status,
                'low_stock_alerts': low_stock_items
            })
        
        # Save report to database
        report_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO sales_reports 
            (id, report_type, start_date, end_date, total_sales, total_commission,
             total_transactions, generated_by, data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            report_id, 
            report_type, 
            start_date, 
            end_date,
            report_data.get('financial_overview', {}).get('total_sales', 0),
            report_data.get('financial_overview', {}).get('total_commissions', 0),
            report_data.get('overview', {}).get('total_transactions', 0),
            user_id,
            json.dumps(report_data)
        ))
        
        conn.commit()
        conn.close()
        
        report_data['report_id'] = report_id
        return report_data
        
    except Exception as e:
        logger.error(f"Error generating comprehensive report: {e}")
        return {}

async def export_data_to_csv(data: List[Dict], filename: str) -> str:
    """Export data to CSV format"""
    try:
        if not data:
            return None
        
        if not PANDAS_AVAILABLE:
            # Fallback to basic CSV writing
            import csv
            os.makedirs('exports', exist_ok=True)
            filepath = f'exports/{filename}'
            
            with open(filepath, 'w', newline='', encoding='utf-8-sig') as csvfile:
                if data:
                    fieldnames = data[0].keys()
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(data)
            return filepath
        
        # Use pandas if available
        import pandas as pd
        df = pd.DataFrame(data)
        
        os.makedirs('exports', exist_ok=True)
        filepath = f'exports/{filename}'
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        
        return filepath
    except Exception as e:
        logger.error(f"Error exporting to CSV: {e}")
        return None

async def generate_visual_chart(data: List[Dict], chart_type: str, title: str) -> str:
    """Generate visual charts from data"""
    try:
        if not PLOTTING_AVAILABLE:
            logger.warning("Plotting libraries not available - chart generation skipped")
            return None
            
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        try:
            plt.style.use('seaborn-v0_8')
        except:
            plt.style.use('default')
        
        plt.rcParams['font.family'] = ['Arial Unicode MS', 'Tahoma', 'DejaVu Sans']
        
        fig, ax = plt.subplots(figsize=(12, 8))
        
        if chart_type == 'bar':
            if data and len(data) > 0:
                x_values = [item.get('name', str(i)) for i, item in enumerate(data)]
                y_values = [float(item.get('value', 0)) for item in data]
                
                bars = ax.bar(x_values, y_values, color='skyblue', alpha=0.8)
                ax.set_title(title, fontsize=16, fontweight='bold')
                ax.set_xlabel('Categories', fontsize=12)
                ax.set_ylabel('Values', fontsize=12)
                
                # Add value labels on bars
                for bar in bars:
                    height = bar.get_height()
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.1f}', ha='center', va='bottom')
                
                plt.xticks(rotation=45, ha='right')
        
        elif chart_type == 'line':
            if data and len(data) > 0:
                x_values = [item.get('date', str(i)) for i, item in enumerate(data)]
                y_values = [float(item.get('value', 0)) for item in data]
                
                ax.plot(x_values, y_values, marker='o', linewidth=2, markersize=6)
                ax.set_title(title, fontsize=16, fontweight='bold')
                ax.set_xlabel('Date', fontsize=12)
                ax.set_ylabel('Values', fontsize=12)
                plt.xticks(rotation=45, ha='right')
        
        elif chart_type == 'pie':
            if data and len(data) > 0:
                labels = [item.get('name', str(i)) for i, item in enumerate(data)]
                sizes = [float(item.get('value', 0)) for item in data]
                
                wedges, texts, autotexts = ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
                ax.set_title(title, fontsize=16, fontweight='bold')
        
        plt.tight_layout()
        
        # Save chart
        import os
        os.makedirs('charts', exist_ok=True)
        
        chart_filename = f'charts/{title.replace(" ", "_")}_chart.png'
        plt.savefig(chart_filename, dpi=300, bbox_inches='tight')
        plt.close()
        
        return chart_filename
        
    except Exception as e:
        logger.error(f"Error generating chart: {e}")
        return None

def get_platform_statistics() -> Dict:
    """Get comprehensive platform statistics"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Basic statistics
        cursor.execute('SELECT COUNT(*) as total_users FROM users')
        total_users = cursor.fetchone()['total_users']
        
        cursor.execute('SELECT COUNT(*) as active_users FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()['active_users']
        
        cursor.execute('SELECT COUNT(*) as total_transactions FROM transactions')
        total_transactions = cursor.fetchone()['total_transactions']
        
        cursor.execute('SELECT SUM(amount) as total_revenue FROM transactions WHERE type = "purchase"')
        total_revenue = cursor.fetchone()['total_revenue'] or 0
        
        cursor.execute('SELECT COUNT(*) as total_networks FROM networks WHERE is_active = 1')
        total_networks = cursor.fetchone()['total_networks']
        
        cursor.execute('SELECT COUNT(*) as total_cards FROM cards')
        total_cards = cursor.fetchone()['total_cards']
        
        cursor.execute('SELECT COUNT(*) as available_cards FROM cards WHERE is_used = 0')
        available_cards = cursor.fetchone()['available_cards']
        
        # Recent activity (last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        cursor.execute('SELECT COUNT(*) as weekly_sales FROM transactions WHERE type = "purchase" AND created_at >= ?', (week_ago,))
        weekly_sales = cursor.fetchone()['weekly_sales']
        
        cursor.execute('SELECT COUNT(*) as weekly_registrations FROM users WHERE created_at >= ?', (week_ago,))
        weekly_registrations = cursor.fetchone()['weekly_registrations']
        
        # Average statistics
        cursor.execute('SELECT AVG(amount) as avg_transaction FROM transactions WHERE type = "purchase"')
        avg_transaction = cursor.fetchone()['avg_transaction'] or 0
        
        conn.close()
        
        return {
            'total_users': total_users,
            'active_users': active_users,
            'total_transactions': total_transactions,
            'total_revenue': round(total_revenue, 2),
            'total_networks': total_networks,
            'total_cards': total_cards,
            'available_cards': available_cards,
            'weekly_sales': weekly_sales,
            'weekly_registrations': weekly_registrations,
            'avg_transaction': round(avg_transaction, 2),
            'card_utilization': round((total_cards - available_cards) / max(total_cards, 1) * 100, 1),
            'user_activity_rate': round(active_users / max(total_users, 1) * 100, 1)
        }
        
    except Exception as e:
        logger.error(f"Error getting platform statistics: {e}")
        return {}

# Encryption functions
def _load_cipher_suite():
    """Load or generate encryption key for secure data storage"""
    if not CRYPTO_AVAILABLE:
        logger.warning("Cryptography library not available - using basic encoding")
        return None
        
    key_b64: Optional[str] = os.getenv('ENCRYPTION_KEY_B64')
    if key_b64 and key_b64.strip():
        key_bytes = key_b64.strip().encode()
    else:
        key_file = os.path.abspath('encryption.key')
        if os.path.exists(key_file):
            with open(key_file, 'rb') as f:
                key_bytes = f.read().strip()
        else:
            key_bytes = Fernet.generate_key()
            with open(key_file, 'wb') as f:
                f.write(key_bytes)
            logger.warning('Generated new encryption.key (development only). Set ENCRYPTION_KEY_B64 in production.')
    return Fernet(key_bytes)

cipher_suite = _load_cipher_suite()

def encrypt_data(data: str) -> str:
    """Encrypt sensitive data"""
    try:
        if cipher_suite:
            return cipher_suite.encrypt(data.encode()).decode()
        else:
            # Fallback to base64 encoding if crypto not available
            return base64.b64encode(data.encode()).decode()
    except Exception as e:
        logger.error(f"Encryption error: {e}")
        return data

def decrypt_data(encrypted_data: str) -> str:
    """Decrypt sensitive data"""
    try:
        if cipher_suite:
            return cipher_suite.decrypt(encrypted_data.encode()).decode()
        else:
            # Fallback to base64 decoding if crypto not available
            return base64.b64decode(encrypted_data.encode()).decode()
    except Exception as e:
        logger.error(f"Decryption error: {e}")
        return encrypted_data

# Database connection with error handling
def get_db_connection():
    """Get database connection with error handling"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=30.0)
        conn.execute('PRAGMA foreign_keys = ON')
        return conn
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise

def execute_db_query(query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
    """Execute database query with proper error handling"""
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, params)
        
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        else:
            result = cursor.lastrowid
            
        conn.commit()
        return result
    except sqlite3.Error as e:
        logger.error(f"Database query error: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn:
            conn.close()

def init_db():
    """Initialize database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Users table with enhanced fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER UNIQUE NOT NULL,
                full_name TEXT NOT NULL,
                phone TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL DEFAULT 'customer',
                balance REAL DEFAULT 0.0,
                invite_code TEXT UNIQUE,
                is_active BOOLEAN DEFAULT 0,
                bank_account TEXT,
                total_referrals INTEGER DEFAULT 0,
                referral_bonus REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                wallet_number TEXT UNIQUE,
                last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0,
                verification_code TEXT,
                total_purchases INTEGER DEFAULT 0,
                total_spent REAL DEFAULT 0.0
            )
        ''')

        # Networks table with enhanced fields including unique ID system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS networks (
                id TEXT PRIMARY KEY,
                supplier_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                city TEXT NOT NULL,
                network_code TEXT UNIQUE NOT NULL,
                is_active BOOLEAN DEFAULT 0,
                is_approved BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approved_at TIMESTAMP,
                approved_by INTEGER,
                description TEXT,
                contact_info TEXT,
                FOREIGN KEY(supplier_id) REFERENCES users(id),
                FOREIGN KEY(approved_by) REFERENCES users(id)
            )
        ''')

        # Card categories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS card_categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                network_id TEXT NOT NULL,
                value REAL NOT NULL,
                price REAL NOT NULL,
                is_available BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                category_name TEXT,
                description TEXT,
                FOREIGN KEY(network_id) REFERENCES networks(id)
            )
        ''')

        # Cards table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cards (
                id TEXT PRIMARY KEY,
                category_id INTEGER NOT NULL,
                code TEXT NOT NULL,
                is_used BOOLEAN DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                used_at TIMESTAMP,
                used_by INTEGER,
                expiry_date TEXT,
                FOREIGN KEY(category_id) REFERENCES card_categories(id),
                FOREIGN KEY(used_by) REFERENCES users(id)
            )
        ''')

        # Enhanced transactions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS transactions (
                id TEXT PRIMARY KEY,
                from_user INTEGER,
                to_user INTEGER,
                amount REAL NOT NULL,
                type TEXT NOT NULL,
                status TEXT DEFAULT 'completed',
                reference_id TEXT,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_withdrawable BOOLEAN DEFAULT 0,
                commission_amount REAL DEFAULT 0.0,
                FOREIGN KEY(from_user) REFERENCES users(id),
                FOREIGN KEY(to_user) REFERENCES users(id)
            )
        ''')

        # Withdrawal requests table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS withdrawal_requests (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                request_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                approval_time TIMESTAMP,
                admin_id INTEGER,
                admin_notes TEXT,
                bank_details TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(admin_id) REFERENCES users(id)
            )
        ''')

        # Referrals table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_id INTEGER NOT NULL,
                referred_id INTEGER NOT NULL,
                bonus_amount REAL DEFAULT 0.0,
                awarded BOOLEAN DEFAULT 0,
                awarded_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(referrer_id) REFERENCES users(id),
                FOREIGN KEY(referred_id) REFERENCES users(id)
            )
        ''')

        # System logs table for admin monitoring
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS system_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                action TEXT NOT NULL,
                details TEXT,
                ip_address TEXT,
                user_agent TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Admin notifications table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS admin_notifications (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                type TEXT DEFAULT 'info',
                is_read BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER,
                target_admin INTEGER,
                FOREIGN KEY(created_by) REFERENCES users(id),
                FOREIGN KEY(target_admin) REFERENCES users(id)
            )
        ''')

        # Accounting tables (keeping existing structure)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                parent_id INTEGER,
                is_active BOOLEAN DEFAULT 1
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_accounts (
                user_id INTEGER UNIQUE NOT NULL,
                account_id INTEGER NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_entries (
                id TEXT PRIMARY KEY,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS journal_lines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entry_id TEXT NOT NULL,
                account_id INTEGER NOT NULL,
                debit REAL DEFAULT 0.0,
                credit REAL DEFAULT 0.0,
                user_id INTEGER,
                ref_type TEXT,
                ref_id TEXT,
                FOREIGN KEY(entry_id) REFERENCES journal_entries(id),
                FOREIGN KEY(account_id) REFERENCES accounts(id)
            )
        ''')

        # Enhanced sales system tables
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS sales_reports (
                id TEXT PRIMARY KEY,
                report_type TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE NOT NULL,
                total_sales REAL DEFAULT 0.0,
                total_commission REAL DEFAULT 0.0,
                total_transactions INTEGER DEFAULT 0,
                generated_by INTEGER NOT NULL,
                generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data TEXT,
                FOREIGN KEY(generated_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS product_inventory (
                id TEXT PRIMARY KEY,
                network_id TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                stock_count INTEGER DEFAULT 0,
                reserved_count INTEGER DEFAULT 0,
                low_stock_threshold INTEGER DEFAULT 10,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_by INTEGER,
                FOREIGN KEY(network_id) REFERENCES networks(id),
                FOREIGN KEY(category_id) REFERENCES card_categories(id),
                FOREIGN KEY(updated_by) REFERENCES users(id)
            )
        ''')

        # E-wallet enhanced features
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet_transactions (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL,
                amount REAL NOT NULL,
                balance_before REAL NOT NULL,
                balance_after REAL NOT NULL,
                reference_id TEXT,
                description TEXT,
                status TEXT DEFAULT 'completed',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS payment_methods (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                method_type TEXT NOT NULL,
                method_name TEXT NOT NULL,
                account_details TEXT NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                is_verified BOOLEAN DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                verified_at TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Rating and review system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS ratings (
                id TEXT PRIMARY KEY,
                rater_id INTEGER NOT NULL,
                rated_user_id INTEGER NOT NULL,
                transaction_id TEXT,
                rating INTEGER NOT NULL CHECK(rating >= 1 AND rating <= 5),
                review_text TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_visible BOOLEAN DEFAULT 1,
                FOREIGN KEY(rater_id) REFERENCES users(id),
                FOREIGN KEY(rated_user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_ratings_summary (
                user_id INTEGER PRIMARY KEY,
                total_ratings INTEGER DEFAULT 0,
                average_rating REAL DEFAULT 0.0,
                rating_1_count INTEGER DEFAULT 0,
                rating_2_count INTEGER DEFAULT 0,
                rating_3_count INTEGER DEFAULT 0,
                rating_4_count INTEGER DEFAULT 0,
                rating_5_count INTEGER DEFAULT 0,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Smart notifications system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notification_preferences (
                user_id INTEGER PRIMARY KEY,
                balance_alerts BOOLEAN DEFAULT 1,
                transaction_alerts BOOLEAN DEFAULT 1,
                promotion_alerts BOOLEAN DEFAULT 1,
                system_alerts BOOLEAN DEFAULT 1,
                low_stock_alerts BOOLEAN DEFAULT 0,
                rating_requests BOOLEAN DEFAULT 1,
                email_notifications BOOLEAN DEFAULT 0,
                sms_notifications BOOLEAN DEFAULT 0,
                quiet_hours_start TIME,
                quiet_hours_end TIME,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS smart_notifications (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                notification_type TEXT NOT NULL,
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                priority TEXT DEFAULT 'normal',
                is_read BOOLEAN DEFAULT 0,
                is_sent BOOLEAN DEFAULT 0,
                scheduled_for TIMESTAMP,
                sent_at TIMESTAMP,
                read_at TIMESTAMP,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Enhanced user management
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_permissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                permission_name TEXT NOT NULL,
                granted_by INTEGER NOT NULL,
                granted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(granted_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                activity_type TEXT NOT NULL,
                description TEXT NOT NULL,
                ip_address TEXT,
                user_agent TEXT,
                session_id TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
        ''')

        # Promotions and offers system
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotions (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                promotion_type TEXT NOT NULL,
                discount_percentage REAL DEFAULT 0.0,
                discount_amount REAL DEFAULT 0.0,
                min_purchase_amount REAL DEFAULT 0.0,
                max_usage_per_user INTEGER DEFAULT 1,
                start_date TIMESTAMP NOT NULL,
                end_date TIMESTAMP NOT NULL,
                is_active BOOLEAN DEFAULT 1,
                created_by INTEGER NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                target_user_role TEXT,
                applicable_networks TEXT,
                FOREIGN KEY(created_by) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS promotion_usage (
                id TEXT PRIMARY KEY,
                promotion_id TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                transaction_id TEXT NOT NULL,
                discount_applied REAL NOT NULL,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(promotion_id) REFERENCES promotions(id),
                FOREIGN KEY(user_id) REFERENCES users(id),
                FOREIGN KEY(transaction_id) REFERENCES transactions(id)
            )
        ''')

        # Migration: Add missing columns
        try:
            cursor.execute('ALTER TABLE users ADD COLUMN wallet_number TEXT UNIQUE')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN is_verified BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN total_purchases INTEGER DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE users ADD COLUMN total_spent REAL DEFAULT 0.0')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE networks ADD COLUMN network_code TEXT UNIQUE')
        except sqlite3.OperationalError:
            pass

        try:
            cursor.execute('ALTER TABLE networks ADD COLUMN is_approved BOOLEAN DEFAULT 0')
        except sqlite3.OperationalError:
            pass

        # Backfill missing wallet numbers
        cursor.execute("SELECT id FROM users WHERE wallet_number IS NULL OR wallet_number = ''")
        missing = [row[0] for row in cursor.fetchall()]
        for user_id in missing:
            for _ in range(20):
                trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
                cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
                if not cursor.fetchone():
                    cursor.execute('UPDATE users SET wallet_number = ? WHERE id = ?', (trial, user_id))
                    break

        # Backfill missing network codes (only if column exists)
        try:
            cursor.execute("SELECT id, supplier_id FROM networks WHERE network_code IS NULL OR network_code = ''")
            missing_codes = cursor.fetchall()
            for network_id, supplier_id in missing_codes:
                for _ in range(20):
                    code = ''.join(str(random.randint(0, 9)) for _ in range(5))
                    cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (code,))
                    if not cursor.fetchone():
                        cursor.execute('UPDATE networks SET network_code = ? WHERE id = ?', (code, network_id))
                        break
        except sqlite3.OperationalError:
            # Column doesn't exist yet, will be handled by migration
            pass

        ensure_base_accounts(cursor)
        conn.commit()
        logger.info("Database initialized successfully")

    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def ensure_base_accounts(cursor: sqlite3.Cursor) -> None:
    """Ensure base accounting accounts exist"""
    cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
            (ACCOUNT_CODE_ISSUANCE_EXPENSE, 'Issuance Expense', ACCOUNT_TYPE_EXPENSE),
        )
    cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
    if not cursor.fetchone():
        cursor.execute(
            'INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)',
            (ACCOUNT_CODE_BOT_COMMISSION_REVENUE, 'Bot Commission Revenue', ACCOUNT_TYPE_REVENUE),
        )

def get_or_create_user_wallet_account(cursor: sqlite3.Cursor, user_id: int) -> int:
    """Get or create user wallet account for accounting"""
    cursor.execute('SELECT account_id FROM user_accounts WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    code = f'2{user_id:06d}'
    name = f'User Wallet #{user_id}'
    cursor.execute('INSERT INTO accounts (code, name, type) VALUES (?, ?, ?)', 
                  (code, name, ACCOUNT_TYPE_LIABILITY))
    account_id = cursor.lastrowid
    cursor.execute('INSERT INTO user_accounts (user_id, account_id) VALUES (?, ?)', 
                  (user_id, account_id))
    return account_id

def post_journal(description: str, created_by: Optional[int], lines: list[dict]) -> str:
    """Post accounting journal entry"""
    total_debit = round(sum(l.get('debit', 0.0) for l in lines), 2)
    total_credit = round(sum(l.get('credit', 0.0) for l in lines), 2)
    if abs(total_debit - total_credit) > 0.0001:
        raise ValueError('Unbalanced journal entry')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        entry_id = str(uuid.uuid4())
        cursor.execute('INSERT INTO journal_entries (id, description, created_by) VALUES (?, ?, ?)', 
                      (entry_id, description, created_by))
        
        for l in lines:
            cursor.execute(
                'INSERT INTO journal_lines (entry_id, account_id, debit, credit, user_id, ref_type, ref_id) VALUES (?, ?, ?, ?, ?, ?, ?)',
                (
                    entry_id,
                    l['account_id'],
                    float(l.get('debit', 0.0) or 0.0),
                    float(l.get('credit', 0.0) or 0.0),
                    l.get('user_id'),
                    l.get('ref_type'),
                    l.get('ref_id'),
                ),
            )
        conn.commit()
        return entry_id
    except Exception as e:
        conn.rollback()
        logger.error(f"Journal posting error: {e}")
        raise
    finally:
        conn.close()

def get_user_ledger_balance(user_id: int) -> float:
    """Get user's balance from ledger"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        account_id = get_or_create_user_wallet_account(cursor, user_id)
        cursor.execute('SELECT COALESCE(SUM(credit - debit), 0) FROM journal_lines WHERE account_id = ?', 
                      (account_id,))
        bal = cursor.fetchone()[0] or 0.0
        return round(bal, 2)
    finally:
        conn.close()

def recalc_and_set_user_balance(user_id: int) -> float:
    """Recalculate and update user balance"""
    bal = get_user_ledger_balance(user_id)
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('UPDATE users SET balance = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?', 
                      (bal, user_id))
        conn.commit()
        return bal
    finally:
        conn.close()

def issue_balance_to_user(super_admin_id: int, target_user_id: int, amount: float, note: str = '') -> str:
    """Issue balance to user by super admin"""
    if amount <= 0:
        raise ValueError('Amount must be positive')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
        row = cursor.fetchone()
        if not row:
            ensure_base_accounts(cursor)
            cursor.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_ISSUANCE_EXPENSE,))
            row = cursor.fetchone()
        issuance_acc_id = row[0]
        
        wallet_acc_id = get_or_create_user_wallet_account(cursor, target_user_id)
        conn.commit()
    finally:
        conn.close()
    
    entry_id = post_journal(
        description=f'Balance issuance to user {target_user_id}. {note}',
        created_by=super_admin_id,
        lines=[
            {'account_id': issuance_acc_id, 'debit': amount, 'credit': 0.0, 
             'user_id': None, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
            {'account_id': wallet_acc_id, 'debit': 0.0, 'credit': amount, 
             'user_id': target_user_id, 'ref_type': 'issuance', 'ref_id': str(target_user_id)},
        ],
    )
    recalc_and_set_user_balance(target_user_id)
    
    # Log the action
    log_system_action(super_admin_id, 'balance_issuance', 
                     f'Issued {amount} to user {target_user_id}. {note}')
    
    return entry_id

# User management functions
def create_user(telegram_id, full_name, phone, role='customer', is_active=False):
    """Create new user with enhanced validation"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        invite_code = str(uuid.uuid4())[:8].upper()
        
        # Generate unique wallet number
        wallet_number = None
        for _ in range(10):
            trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
            cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
            if not cursor.fetchone():
                wallet_number = trial
                break
        
        if not wallet_number:
            raise RuntimeError('Failed to generate unique wallet number')
        
        # Auto-activate customers, require admin approval for agents/suppliers
        is_active_val = 1 if role == 'customer' else (1 if is_active else 0)
        
        cursor.execute('''
            INSERT INTO users (telegram_id, full_name, phone, role, invite_code, 
                             is_active, wallet_number, is_verified, created_at, last_activity) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ''', (telegram_id, full_name, phone, role, invite_code, is_active_val, wallet_number, 1))
        
        user_id = cursor.lastrowid
        conn.commit()
        
        # Log user creation
        log_system_action(user_id, 'user_registration', f'New {role} registered: {full_name}')
        
        return user_id
    except sqlite3.IntegrityError as e:
        logger.error(f'Error creating user: {e}')
        return None
    finally:
        conn.close()

def _row_to_dict(cursor, row):
    """Convert database row to dictionary"""
    if row is None:
        return None
    columns = [col[0] for col in cursor.description]
    return dict(zip(columns, row))

def get_user(telegram_id):
    """Get user by Telegram ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_phone(phone):
    """Get user by phone number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE phone = ?', (phone,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_wallet(wallet_number: str):
    """Get user by wallet number"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE wallet_number = ?', (wallet_number,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def get_user_by_id(user_id):
    """Get user by ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = cursor.fetchone()
        return _row_to_dict(cursor, row)
    finally:
        conn.close()

def update_user_activity(user_id):
    """Update user's last activity timestamp"""
    try:
        execute_db_query(
            'UPDATE users SET last_activity = CURRENT_TIMESTAMP WHERE id = ?',
            (user_id,)
        )
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

def create_transaction(from_user_id, to_user_id, amount, txn_type, reference_id=None, 
                     is_withdrawable=False, description='', commission_amount=0.0):
    """Create transaction record"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        txn_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions (id, from_user, to_user, amount, type, reference_id, 
                                    is_withdrawable, description, commission_amount) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (txn_id, from_user_id, to_user_id, amount, txn_type, reference_id, 
              1 if is_withdrawable else 0, description, commission_amount))
        conn.commit()
        return txn_id
    finally:
        conn.close()

def log_system_action(user_id, action, details='', ip_address='', user_agent=''):
    """Log system actions for monitoring"""
    try:
        execute_db_query('''
            INSERT INTO system_logs (user_id, action, details, ip_address, user_agent) 
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, action, details, ip_address, user_agent))
    except Exception as e:
        logger.error(f"Error logging system action: {e}")

def create_admin_notification(title, message, notification_type='info', created_by=None, target_admin=None):
    """Create admin notification"""
    try:
        notification_id = str(uuid.uuid4())
        execute_db_query('''
            INSERT INTO admin_notifications (id, title, message, type, created_by, target_admin) 
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (notification_id, title, message, notification_type, created_by, target_admin))
        return notification_id
    except Exception as e:
        logger.error(f"Error creating admin notification: {e}")
        return None

def setup_super_admin():
    """Setup super admin account"""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (7684780523,))
        admin = cursor.fetchone()
        if not admin:
            # Generate unique wallet for super admin
            wallet_number = None
            for _ in range(10):
                trial = '79' + ''.join(str(random.randint(0, 9)) for _ in range(7))
                cursor.execute('SELECT 1 FROM users WHERE wallet_number = ?', (trial,))
                if not cursor.fetchone():
                    wallet_number = trial
                    break
            
            cursor.execute('''
                INSERT INTO users (telegram_id, full_name, phone, role, is_active, 
                                 invite_code, wallet_number, is_verified) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (7684780523, 'المشرف الأعلى 👑', '000000000', 'super_admin', 1, 'ADMIN123', wallet_number, 1))
            conn.commit()
            logger.info('Super admin created successfully')
    finally:
        conn.close()

# Conversation states
(
    GET_FULL_NAME, GET_PHONE, CHOOSE_ROLE,
    SUPPLIER_MENU, AGENT_MENU, ADMIN_MENU, SUPER_ADMIN_MENU,
    UPLOAD_CARDS, CONFIRM_UPLOAD, SELECT_NETWORK, SELECT_CATEGORY, CONFIRM_PURCHASE,
    SELECT_CUSTOMER, GET_RECHARGE_AMOUNT, CONFIRM_RECHARGE,
    GET_WITHDRAW_AMOUNT, CONFIRM_WITHDRAWAL,
    ADMIN_ACTIVATE_ACCOUNTS, ADMIN_APPROVE_NETWORKS,
    ISSUE_TARGET, ISSUE_AMOUNT, ISSUE_CONFIRM,
    PASTE_CARDS, ADD_NETWORK_NAME, ADD_NETWORK_CITY, ADD_NETWORK_DESCRIPTION,
    TRANSFER_TARGET, TRANSFER_AMOUNT, TRANSFER_CONFIRM,
    SEARCH_NETWORK_INPUT, MANAGE_INVENTORY_MENU,
    VIEW_STATS_MENU, ADMIN_REPORTS_MENU,
) = range(33)

# Enhanced message templates
def format_user_info(user):
    """Format user information display"""
    role_emoji = {
        'customer': '👤',
        'agent': '🔷',
        'supplier': '🏪',
        'admin': '👨‍💼',
        'super_admin': '👑'
    }
    
    status = f"{EMOJIS['success']} مفعل" if user['is_active'] else f"{EMOJIS['warning']} غير مفعل"
    
    return f"""
{role_emoji.get(user['role'], '👤')} **{user['full_name']}**
{EMOJIS['phone']} الهاتف: {user['phone']}
{EMOJIS['wallet']} المحفظة: {user.get('wallet_number', 'غير محدد')}
{EMOJIS['money']} الرصيد: {user['balance']:.2f} ريال
{EMOJIS['stats']} المشتريات: {user.get('total_purchases', 0)}
📊 الحالة: {status}
{EMOJIS['date']} التسجيل: {user.get('created_at', 'غير محدد')[:10]}
"""

def format_network_info(network, supplier_name=''):
    """Format network information display"""
    status = f"{EMOJIS['success']} مفعلة" if network[5] else f"{EMOJIS['warning']} غير مفعلة"
    approval = f"{EMOJIS['success']} معتمدة" if network[6] else f"{EMOJIS['warning']} في انتظار الموافقة"
    
    return f"""
{EMOJIS['network']} **{network[2]}**
{EMOJIS['id']} الرمز: {network[7] if len(network) > 7 else 'غير محدد'}
{EMOJIS['user']} المزود: {supplier_name}
🏙️ المدينة: {network[3]}
📊 الحالة: {status}
✅ الاعتماد: {approval}
{EMOJIS['date']} الإنشاء: {network[8][:10] if len(network) > 8 else 'غير محدد'}
"""

# Enhanced UI functions
def create_main_keyboard(role):
    """Create main menu keyboard based on user role"""
    if role == 'customer':
        return [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كروت إنترنت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["wallet"]} محفظتي المطورة', callback_data='enhanced_wallet'),
             InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton(f'{EMOJIS["star"]} تقييماتي', callback_data='my_ratings')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends'),
             InlineKeyboardButton(f'🔔 إشعاراتي', callback_data='my_notifications')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} شحن رصيد', callback_data='recharge_balance'),
             InlineKeyboardButton(f'🎁 العروض والخصومات', callback_data='promotions')],
            [InlineKeyboardButton(f'⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton(f'❓ المساعدة', callback_data='customer_help')],
        ]
    elif role == 'supplier':
        return [
            [InlineKeyboardButton(f'{EMOJIS["upload"]} رفع كروت جديدة', callback_data='upload_cards'),
             InlineKeyboardButton(f'📝 لصق أكواد يدوياً', callback_data='paste_cards')],
            [InlineKeyboardButton(f'{EMOJIS["network"]} إدارة الشبكات', callback_data='manage_networks'),
             InlineKeyboardButton(f'{EMOJIS["settings"]} إدارة المخزون', callback_data='manage_inventory')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} تقارير المبيعات المتقدمة', callback_data='advanced_sales_reports'),
             InlineKeyboardButton(f'{EMOJIS["star"]} تقييمات المنتجات', callback_data='product_ratings')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} سحب الأرباح', callback_data='withdraw_earnings'),
             InlineKeyboardButton(f'🎁 إنشاء عروض', callback_data='create_promotions')],
            [InlineKeyboardButton(f'🔔 تنبيهات المخزون', callback_data='inventory_alerts'),
             InlineKeyboardButton(f'📊 تحليلات الأداء', callback_data='performance_analytics')],
        ]
    elif role == 'agent':
        return [
            [InlineKeyboardButton(f'🔋 شحن عملاء', callback_data='recharge_customers')],
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء للعملاء', callback_data='buy_for_customers')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} سحب الأرباح', callback_data='agent_withdraw')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} سجل العمولات', callback_data='commission_history')],
            [InlineKeyboardButton(f'👥 إدارة العملاء', callback_data='manage_customers')],
        ]
    elif role == 'admin':
        return [
            [InlineKeyboardButton(f'{EMOJIS["user"]} تفعيل حسابات', callback_data='activate_accounts'),
             InlineKeyboardButton(f'{EMOJIS["network"]} موافقة شبكات', callback_data='approve_networks')],
            [InlineKeyboardButton(f'🔍 مراقبة التحويلات', callback_data='monitor_transactions'),
             InlineKeyboardButton(f'💼 طلبات السحب', callback_data='withdrawal_requests')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} التقارير الشاملة', callback_data='comprehensive_reports'),
             InlineKeyboardButton(f'{EMOJIS["star"]} إدارة التقييمات', callback_data='manage_ratings')],
            [InlineKeyboardButton(f'🔔 إدارة الإشعارات', callback_data='manage_notifications'),
             InlineKeyboardButton(f'🎁 إدارة العروض', callback_data='manage_promotions')],
            [InlineKeyboardButton(f'👥 إدارة الصلاحيات', callback_data='manage_permissions'),
             InlineKeyboardButton(f'📊 إحصائيات متقدمة', callback_data='advanced_analytics')],
        ]
    elif role == 'super_admin':
        return [
            [InlineKeyboardButton(f'{EMOJIS["admin"]} إدارة المشرفين', callback_data='manage_admins'),
             InlineKeyboardButton(f'{EMOJIS["settings"]} إعدادات النظام', callback_data='system_settings')],
            [InlineKeyboardButton(f'{EMOJIS["money"]} إصدار رصيد', callback_data='issue_balance'),
             InlineKeyboardButton(f'💾 النسخ الاحتياطي', callback_data='backup_database')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} التقارير التنفيذية', callback_data='executive_reports'),
             InlineKeyboardButton(f'📊 تحليلات الأعمال', callback_data='business_analytics')],
            [InlineKeyboardButton(f'🏛️ إدارة المنصة', callback_data='platform_management'),
             InlineKeyboardButton(f'🔧 إعدادات متقدمة', callback_data='advanced_settings')],
            [InlineKeyboardButton(f'🚨 مراقبة الأمان', callback_data='security_monitoring'),
             InlineKeyboardButton(f'📈 لوحة المعلومات', callback_data='dashboard_analytics')],
        ]
    
    return [[InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]]

# Handler functions start here

async def start(update: Update, context: CallbackContext) -> int:
    """Start command handler with enhanced welcome message"""
    try:
        user = get_user(update.effective_user.id)
        
        if user:
            update_user_activity(user['id'])
            role = user['role']
            
            welcome_message = f"""
{EMOJIS['star']} **مرحباً بك {user['full_name']}!** {EMOJIS['star']}

{format_user_info(user)}

{EMOJIS['fire']} اختر من القائمة أدناه:
"""
            
            keyboard = create_main_keyboard(role)
            keyboard.append([InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')])
            
            if update.message:
                await update.message.reply_text(welcome_message, 
                                              reply_markup=InlineKeyboardMarkup(keyboard),
                                              parse_mode='Markdown')
            else:
                await update.callback_query.edit_message_text(welcome_message,
                                                            reply_markup=InlineKeyboardMarkup(keyboard),
                                                            parse_mode='Markdown')
            return ConversationHandler.END
        
        # Handle referral codes
        if context.args and context.args[0].startswith('ref_'):
            context.user_data['referral_code'] = context.args[0][4:]
        
        welcome_text = f"""
{EMOJIS['star']} **مرحباً بك في بوت كروت الإنترنت اليمني!** {EMOJIS['network']}

{EMOJIS['new']} للبدء، يرجى إدخال اسمك الرباعي الكامل:
{EMOJIS['warning']} مثال: أحمد محمد علي سالم
"""
        
        await update.message.reply_text(welcome_text, 
                                      reply_markup=ReplyKeyboardRemove(),
                                      parse_mode='Markdown')
        return GET_FULL_NAME
        
    except Exception as e:
        logger.error(f"Error in start handler: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def get_full_name(update: Update, context: CallbackContext) -> int:
    """Get user's full name with validation"""
    try:
        full_name = update.message.text.strip()
        
        # Validate Arabic name with at least 4 parts
        if len(full_name.split()) < 4:
            await update.message.reply_text(
                f"{EMOJIS['warning']} يرجى إدخال الاسم الرباعي كاملاً (أربعة أجزاء على الأقل)\n"
                f"مثال: أحمد محمد علي سالم"
            )
            return GET_FULL_NAME
        
        # Basic Arabic name validation
        if not re.match(r'^[\u0600-\u06FF\s]+$', full_name):
            await update.message.reply_text(
                f"{EMOJIS['warning']} يرجى إدخال الاسم باللغة العربية فقط"
            )
            return GET_FULL_NAME
        
        context.user_data['full_name'] = full_name
        
        phone_text = f"""
{EMOJIS['phone']} **الآن أدخل رقم هاتفك:**

{EMOJIS['warning']} **مهم:** أدخل 9 أرقام فقط (بدون الصفر الأول)
{EMOJIS['star']} مثال: 733456789

أو اختر من الأمثلة أدناه:
"""
        
        await update.message.reply_text(
            phone_text,
            reply_markup=ReplyKeyboardMarkup([
                ['711234567', '733456789', '755678901'],
                ['777890123', '799012345', '70123456'],
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return GET_PHONE
        
    except Exception as e:
        logger.error(f"Error in get_full_name: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def get_phone(update: Update, context: CallbackContext) -> int:
    """Get and validate phone number"""
    try:
        phone = update.message.text.strip()
        
        # Validate Yemen phone number format
        if not re.fullmatch(r'[7][0-9]{8}', phone):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رقم الهاتف غير صحيح!**\n\n"
                f"يرجى إدخال رقم يمني صحيح:\n"
                f"• 9 أرقام تبدأ بالرقم 7\n"
                f"• بدون الصفر الأول\n"
                f"• مثال: 733456789",
                parse_mode='Markdown'
            )
            return GET_PHONE
        
        # Check if phone already exists
        if get_user_by_phone(phone):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **هذا الرقم مسجل مسبقاً!**\n"
                f"يرجى استخدام رقم آخر أو التواصل مع الدعم إذا كان هذا رقمك."
            )
            return GET_PHONE
        
        context.user_data['phone'] = phone
        
        role_text = f"""
{EMOJIS['user']} **اختر دورك في المنصة:**

{EMOJIS['star']} **العميل:** شراء كروت الإنترنت
{EMOJIS['cool']} **الوكيل:** بيع الكروت والحصول على عمولة  
{EMOJIS['fire']} **المزود:** توفير كروت الإنترنت
"""
        
        await update.message.reply_text(
            role_text,
            reply_markup=ReplyKeyboardMarkup([
                [f"{EMOJIS['user']} عميل", f"{EMOJIS['cool']} وكيل", f"{EMOJIS['fire']} مزود"]
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return CHOOSE_ROLE
        
    except Exception as e:
        logger.error(f"Error in get_phone: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def choose_role(update: Update, context: CallbackContext) -> int:
    """Handle role selection with enhanced validation"""
    try:
        role_choice = update.message.text.strip()
        role_map = {
            f"{EMOJIS['user']} عميل": 'customer',
            f"{EMOJIS['cool']} وكيل": 'agent', 
            f"{EMOJIS['fire']} مزود": 'supplier',
            'عميل': 'customer',
            'وكيل': 'agent',
            'مزود': 'supplier'
        }
        
        if role_choice not in role_map:
            await update.message.reply_text(
                f"{EMOJIS['warning']} اختيار غير صحيح! يرجى الاختيار من القائمة.",
                reply_markup=ReplyKeyboardMarkup([
                    [f"{EMOJIS['user']} عميل", f"{EMOJIS['cool']} وكيل", f"{EMOJIS['fire']} مزود"]
                ], one_time_keyboard=True, resize_keyboard=True)
            )
            return CHOOSE_ROLE
        
        role = role_map[role_choice]
        full_name = context.user_data['full_name']
        phone = context.user_data['phone']
        telegram_id = update.effective_user.id
        
        # Auto-activate customers, require approval for agents/suppliers
        is_active = True if role == 'customer' else False
        
        user_id = create_user(telegram_id, full_name, phone, role, is_active)
        
        if not user_id:
            await update.message.reply_text(
                f"{EMOJIS['error']} **حدث خطأ أثناء التسجيل!**\n"
                f"يرجى المحاولة لاحقاً أو التواصل مع الدعم.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        # Handle referral
        referral_code = context.user_data.get('referral_code')
        if referral_code:
            conn = get_db_connection()
            cursor = conn.cursor()
            try:
                cursor.execute('SELECT id, full_name FROM users WHERE invite_code = ?', (referral_code,))
                referrer = cursor.fetchone()
                if referrer:
                    referrer_id = referrer[0]
                    referral_id = str(uuid.uuid4())
                    cursor.execute('''
                        INSERT INTO referrals (id, referrer_id, referred_id, bonus_amount) 
                        VALUES (?, ?, ?, ?)
                    ''', (referral_id, referrer_id, user_id, 100.0))  # 100 riyal bonus
                    conn.commit()
                    
                    await update.message.reply_text(
                        f"{EMOJIS['success']} تم تسجيلك بدعوة من **{referrer[1]}**!\n"
                        f"{EMOJIS['money']} ستحصل على مكافأة عند أول شحن!",
                        parse_mode='Markdown'
                    )
            finally:
                conn.close()
        
        # Success message
        role_names = {'customer': 'عميل', 'agent': 'وكيل', 'supplier': 'مزود'}
        success_message = f"""
{EMOJIS['success']} **تم تسجيلك بنجاح كـ {role_names[role]}!**

{EMOJIS['user']} الاسم: {full_name}
{EMOJIS['phone']} الهاتف: {phone}
{EMOJIS['wallet']} رقم المحفظة: {get_user(telegram_id)['wallet_number']}
"""
        
        if role in ['agent', 'supplier']:
            success_message += f"""
{EMOJIS['warning']} **انتظار التفعيل:**
سيتم مراجعة طلبك من قبل الإدارة خلال 24 ساعة.
سيتم إشعارك فور الموافقة على حسابك.
"""
            # Notify admins
            await notify_admins(context, f"""
{EMOJIS['new']} **طلب تفعيل حساب جديد**

{EMOJIS['user']} الاسم: {full_name}
{EMOJIS['phone']} الهاتف: {phone}
{EMOJIS['star']} الدور: {role_names[role]}
{EMOJIS['id']} معرف التلغرام: {telegram_id}
{EMOJIS['date']} وقت التسجيل: {datetime.now().strftime('%Y-%m-%d %H:%M')}

للموافقة: /approve_user_{user_id}
""")
        
        # Get updated user data and show invite link
        user = get_user(telegram_id)
        invite_link = f"https://t.me/Vsjsgshh_bot?start=ref_{user['invite_code']}"
        
        success_message += f"""
{EMOJIS['user']} **رابط دعوتك:**
{invite_link}

{EMOJIS['money']} احصل على مكافآت من دعوة الأصدقاء!
"""
        
        await update.message.reply_text(
            success_message,
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='Markdown'
        )
        
        # Show appropriate menu
        return await show_main_menu(update, context, role)
        
    except Exception as e:
        logger.error(f"Error in choose_role: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def show_main_menu(update: Update, context: CallbackContext, role: str):
    """Show main menu based on user role"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        # Recalculate balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(update.effective_user.id)  # Refresh user data
        
        role_emojis = {
            'customer': '👤',
            'agent': '🔷', 
            'supplier': '🏪',
            'admin': '👨‍💼',
            'super_admin': '👑'
        }
        
        role_names = {
            'customer': 'العميل',
            'agent': 'الوكيل',
            'supplier': 'المزود',
            'admin': 'المشرف',
            'super_admin': 'المشرف الأعلى'
        }
        
        menu_text = f"""
{role_emojis.get(role, '👤')} **لوحة تحكم {role_names.get(role, 'المستخدم')}**

{EMOJIS['user']} مرحباً **{user['full_name']}**
{EMOJIS['wallet']} رصيدك: **{user['balance']:.2f}** ريال
{EMOJIS['id']} محفظتك: `{user['wallet_number']}`

{EMOJIS['fire']} اختر الإجراء المطلوب:
"""
        
        keyboard = create_main_keyboard(role)
        
        if update.message:
            await update.message.reply_text(
                menu_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await update.callback_query.edit_message_text(
                menu_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in show_main_menu: {e}")
        error_text = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة. يرجى المحاولة مرة أخرى."
        
        if update.message:
            await update.message.reply_text(error_text)
        else:
            await update.callback_query.edit_message_text(error_text)
        
        return ConversationHandler.END

# ... continuing with rest of the handlers ...

# Utility functions for admin notifications
async def notify_admins(context: CallbackContext, message: str):
    """Send notification to super admin"""
    try:
        logger.info(f'Admin Notification: {message}')
        await context.bot.send_message(chat_id=7684780523, text=message, parse_mode='Markdown')
        
        # Also create admin notification in database
        create_admin_notification(
            title="إشعار إداري جديد", 
            message=message, 
            notification_type='info'
        )
    except Exception as e:
        logger.error(f"Error sending admin notification: {e}")

# Enhanced handler functions

async def cancel(update: Update, context: CallbackContext) -> int:
    """Cancel current operation"""
    try:
        message = f"{EMOJIS['cancel']} تم إلغاء العملية."
        
        if update.message:
            await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())
        else:
            await update.callback_query.edit_message_text(message)
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in cancel handler: {e}")
        return ConversationHandler.END

async def main_menu_handler(update: Update, context: CallbackContext) -> int:
    """Handle main menu button press"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if user:
            return await show_main_menu(update, context, user['role'])
        
        return await start(update, context)
    except Exception as e:
        logger.error(f"Error in main menu handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

# Quick menu and balance display
async def quick_menu(update: Update, context: CallbackContext) -> int:
    """Show quick menu for fast access"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        buttons = [
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')],
            [InlineKeyboardButton(f'{EMOJIS["wallet"]} رصيدي', callback_data='show_balance')],
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["stats"]} إحصائياتي', callback_data='my_stats')],
        ]
        
        text = f"""
{EMOJIS['fire']} **القائمة السريعة**

{EMOJIS['user']} مرحباً **{user['full_name']}**
{EMOJIS['wallet']} رصيدك: **{user['balance']:.2f}** ريال

اختر الإجراء المطلوب:
"""
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(buttons), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in quick menu: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في تحميل القائمة السريعة."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

async def show_balance(update: Update, context: CallbackContext) -> int:
    """Show user balance and wallet info"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        # Recalculate and update balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(update.effective_user.id)  # Refresh data
        
        update_user_activity(user['id'])
        
        # Get additional stats
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
            purchases_count, purchases_total = cursor.fetchone()
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ? AND type != 'card_purchase'", (user['id'],))
            incoming_total = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'p2p_transfer'", (user['id'],))
            outgoing_transfers = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user['id'],))
            referrals_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(bonus_amount),0) FROM referrals WHERE referrer_id = ? AND awarded = 1", (user['id'],))
            referral_earnings = cursor.fetchone()[0] or 0
            
            # Get last transaction
            cursor.execute("SELECT type, amount, created_at FROM transactions WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC LIMIT 1", (user['id'], user['id']))
            last_transaction = cursor.fetchone()
        finally:
            conn.close()
        
        last_tx_text = "لا توجد معاملات"
        if last_transaction:
            tx_type_map = {
                'card_purchase': 'شراء كرت',
                'p2p_transfer': 'تحويل رصيد',
                'wallet_recharge': 'شحن رصيد',
                'agent_commission': 'عمولة وكيل'
            }
            tx_type = tx_type_map.get(last_transaction[0], last_transaction[0])
            last_tx_text = f"{tx_type} - {last_transaction[1]} ريال ({last_transaction[2][:10]})"
        
        role_names = {
            'customer': 'عميل',
            'agent': 'وكيل',
            'supplier': 'مزود',
            'admin': 'مشرف',
            'super_admin': 'مشرف أعلى'
        }
        
        text = f"""
{EMOJIS['wallet']} **معلومات المحفظة**

{EMOJIS['user']} الاسم: **{user['full_name']}**
{EMOJIS['wallet']} رقم المحفظة: `{user['wallet_number']}`
{EMOJIS['money']} الرصيد الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['stats']} **الإحصائيات:**
{EMOJIS['purchase']} عدد المشتريات: **{purchases_count}**
{EMOJIS['money']} إجمالي الإنفاق: **{purchases_total:.2f}** ريال

{EMOJIS['transfer']} **التحويلات:**
التحويلات الصادرة: **{outgoing_transfers:.2f}** ريال
التحويلات الواردة: **{incoming_total:.2f}** ريال

{EMOJIS['user']} **الإحالات:**
عدد الدعوات: **{referrals_count}**
أرباح الإحالة: **{referral_earnings:.2f}** ريال

{EMOJIS['time']} **آخر معاملة:**
{last_tx_text}

{EMOJIS['date']} **تاريخ التسجيل:**
{user.get('created_at', 'غير محدد')[:10]}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in show_balance: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الرصيد."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

# Network and supplier functions
async def _ensure_supplier_network(cursor: sqlite3.Cursor, supplier_user_id: int) -> str:
    """Ensure supplier has a default network"""
    cursor.execute('SELECT id FROM networks WHERE supplier_id = ?', (supplier_user_id,))
    row = cursor.fetchone()
    if row:
        return row[0]
    
    # Generate unique network code
    network_code = None
    for _ in range(20):
        code = ''.join(str(random.randint(0, 9)) for _ in range(5))
        cursor.execute('SELECT 1 FROM networks WHERE network_code = ?', (code,))
        if not cursor.fetchone():
            network_code = code
            break
    
    if not network_code:
        raise RuntimeError('Failed to generate unique network code')
    
    network_id = str(uuid.uuid4())
    cursor.execute('''
        INSERT INTO networks (id, supplier_id, name, city, network_code, is_active, is_approved) 
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (network_id, supplier_user_id, 'شبكة المزود الافتراضية', 'غير محدد', network_code, 0, 0))
    
    return network_id

# Card management functions
async def buy_cards(update: Update, context: CallbackContext) -> int:
    """Handle card purchase flow"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return ConversationHandler.END
        
        update_user_activity(user['id'])
        
        loading_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري تحميل الشبكات المتاحة...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT n.id, n.name, n.network_code, u.full_name 
                FROM networks n 
                JOIN users u ON n.supplier_id = u.id 
                WHERE n.is_active = 1 AND n.is_approved = 1
            ''')
            networks = cursor.fetchall()
        finally:
            conn.close()
        
        if not networks:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id, 
                message_id=loading_msg.message_id, 
                text=f"{EMOJIS['warning']} لا تتوفر شبكات مفعلة حالياً. يرجى المحاولة لاحقاً."
            )
            return ConversationHandler.END
        
        keyboard = []
        for network in networks:
            network_text = f"{EMOJIS['network']} {network[1]} ({network[2]})"
            keyboard.append([InlineKeyboardButton(network_text, callback_data=f'network_{network[0]}')])
        
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["search"]} بحث بالرمز', callback_data='search_networks')])
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')])
        
        text = f"""
{EMOJIS['purchase']} **شراء كروت الإنترنت**

{EMOJIS['network']} اختر الشبكة المطلوبة:
{EMOJIS['star']} يمكنك البحث بالرمز المكون من 5 أرقام
"""
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id, 
            message_id=loading_msg.message_id, 
            text=text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECT_NETWORK
    except Exception as e:
        logger.error(f"Error in buy_cards: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل الشبكات.")
        return ConversationHandler.END

async def select_category(update: Update, context: CallbackContext) -> int:
    """Handle network selection and show categories"""
    try:
        query = update.callback_query
        await query.answer()
        
        network_id = query.data.split('_')[1]
        context.user_data['selected_network'] = network_id
        
        loading_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري تحميل الفئات المتاحة...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get network info
            cursor.execute('SELECT name, network_code FROM networks WHERE id = ?', (network_id,))
            network_info = cursor.fetchone()
            
            # Get available categories
            cursor.execute('''
                SELECT id, value, price, category_name 
                FROM card_categories 
                WHERE network_id = ? AND is_available = 1
            ''', (network_id,))
            categories = cursor.fetchall()
        finally:
            conn.close()
        
        if not categories:
            await context.bot.edit_message_text(
                chat_id=query.message.chat_id, 
                message_id=loading_msg.message_id, 
                text=f"{EMOJIS['warning']} لا تتوفر فئات كروت لهذه الشبكة حالياً.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data='buy_cards')]])
            )
            return ConversationHandler.END
        
        keyboard = []
        for category in categories:
            category_name = category[3] if category[3] else f"فئة {category[1]} ريال"
            category_text = f"{EMOJIS['card']} {category_name} - {category[2]} ريال"
            keyboard.append([InlineKeyboardButton(category_text, callback_data=f'category_{category[0]}')])
        
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data='buy_cards')])
        keyboard.append([InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')])
        
        text = f"""
{EMOJIS['purchase']} **اختيار فئة الكرت**

{EMOJIS['network']} الشبكة: **{network_info[0]}** ({network_info[1]})

{EMOJIS['money']} اختر الفئة السعرية:
"""
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id, 
            message_id=loading_msg.message_id, 
            text=text, 
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        return SELECT_CATEGORY
    except Exception as e:
        logger.error(f"Error in select_category: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحميل الفئات.")
        return ConversationHandler.END

async def confirm_purchase(update: Update, context: CallbackContext) -> int:
    """Show purchase confirmation"""
    try:
        query = update.callback_query
        await query.answer()
        
        category_id = query.data.split('_')[1]
        context.user_data['selected_category'] = category_id
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute('''
                SELECT cc.value, cc.price, cc.category_name, n.name, n.network_code 
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ?
            ''', (category_id,))
            row = cursor.fetchone()
            
            if not row:
                await query.edit_message_text(f"{EMOJIS['error']} الفئة المحددة غير متوفرة!")
                return ConversationHandler.END
            
            value, price, category_name, network_name, network_code = row
            
            # Check card availability
            cursor.execute('SELECT COUNT(*) FROM cards WHERE category_id = ? AND is_used = 0', (category_id,))
            available_cards = cursor.fetchone()[0] or 0
        finally:
            conn.close()
        
        user = get_user(query.from_user.id)
        balance = user['balance']
        
        if available_cards == 0:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **عذراً، الكروت نفذت لهذه الفئة!**\n\n"
                f"يرجى اختيار فئة أخرى أو المحاولة لاحقاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["back"]} اختيار فئة أخرى', callback_data=f'network_{context.user_data.get("selected_network")}')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        if balance < price:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي!**\n\n"
                f"{EMOJIS['card']} سعر الكرت: **{price}** ريال\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{balance}** ريال\n\n"
                f"يرجى شحن رصيدك أولاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["money"]} شحن الرصيد', callback_data='recharge_balance')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        category_display = category_name if category_name else f"فئة {value} ريال"
        
        text = f"""
{EMOJIS['purchase']} **تأكيد الشراء**

{EMOJIS['network']} الشبكة: **{network_name}** ({network_code})
{EMOJIS['card']} الفئة: **{category_display}**
{EMOJIS['money']} القيمة: **{value}** ريال
{EMOJIS['wallet']} السعر: **{price}** ريال

{EMOJIS['user']} رصيدك الحالي: **{balance}** ريال
{EMOJIS['stats']} الرصيد بعد الشراء: **{balance - price}** ريال
{EMOJIS['card']} الكروت المتاحة: **{available_cards}**

هل تريد تأكيد الشراء؟
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["confirm"]} تأكيد الشراء', callback_data='complete_purchase')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} رجوع', callback_data=f'network_{context.user_data.get("selected_network")}')],
            [InlineKeyboardButton(f'{EMOJIS["cancel"]} إلغاء', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return CONFIRM_PURCHASE
    except Exception as e:
        logger.error(f"Error in confirm_purchase: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد الشراء.")
        return ConversationHandler.END

async def complete_purchase(update: Update, context: CallbackContext) -> int:
    """Complete the card purchase"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        category_id = context.user_data.get('selected_category')
        
        if not category_id:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عملية الشراء.")
            return ConversationHandler.END
        
        processing_msg = await query.edit_message_text(f"{EMOJIS['loading']} جاري معالجة عملية الشراء...")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get category and network info
            cursor.execute('''
                SELECT cc.price, cc.value, n.supplier_id, n.name 
                FROM card_categories cc 
                JOIN networks n ON cc.network_id = n.id 
                WHERE cc.id = ?
            ''', (category_id,))
            row = cursor.fetchone()
            
            if not row:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=processing_msg.message_id,
                    text=f"{EMOJIS['error']} الفئة المحددة غير متوفرة!"
                )
                return ConversationHandler.END
            
            price, value, supplier_id, network_name = row
            
            # Check and apply promotions
            applied_promotion = None
            discount_amount = 0.0
            final_price = price
            
            cursor.execute('''
                SELECT * FROM promotions 
                WHERE is_active = 1 
                AND start_date <= ? 
                AND end_date >= ?
                AND (target_user_role IS NULL OR target_user_role = ?)
                AND min_purchase_amount <= ?
                ORDER BY discount_percentage DESC, discount_amount DESC
                LIMIT 1
            ''', (datetime.now(), datetime.now(), user['role'], price))
            
            promotion = cursor.fetchone()
            
            if promotion:
                # Check if user hasn't exceeded usage limit
                cursor.execute('''
                    SELECT COUNT(*) as usage_count
                    FROM promotion_usage 
                    WHERE user_id = ? AND promotion_id = ?
                ''', (user['id'], promotion['id']))
                
                usage_count = cursor.fetchone()['usage_count']
                
                if usage_count < promotion['max_usage_per_user']:
                    if promotion['discount_percentage'] > 0:
                        discount_amount = round(price * promotion['discount_percentage'] / 100, 2)
                    else:
                        discount_amount = promotion['discount_amount']
                    
                    final_price = max(0, price - discount_amount)
                    applied_promotion = promotion
            
            # Check user balance
            if user['balance'] < final_price:
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=processing_msg.message_id,
                    text=f"{EMOJIS['error']} رصيدك غير كافي!\n\n"
                         f"💰 المطلوب: {final_price:.2f} ريال\n"
                         f"💳 رصيدك: {user['balance']:.2f} ريال\n"
                         f"💸 النقص: {final_price - user['balance']:.2f} ريال"
                )
                return ConversationHandler.END
            
            # Get available card
            cursor.execute('SELECT id, code FROM cards WHERE category_id = ? AND is_used = 0 LIMIT 1', (category_id,))
            card = cursor.fetchone()
            
            if not card:
                # Update inventory to reflect shortage
                update_inventory_stock(row['network_id'] if 'network_id' in row else None, category_id, -1)
                
                await context.bot.edit_message_text(
                    chat_id=query.message.chat_id,
                    message_id=processing_msg.message_id,
                    text=f"{EMOJIS['warning']} عذراً، الكروت نفذت لهذه الفئة!\n\n"
                         f"🔔 سيتم إشعارك عند توفر كروت جديدة."
                )
                
                # Send low stock notification
                send_smart_notification(
                    user['id'],
                    'out_of_stock',
                    '⚠️ نفاد المخزون',
                    f'الكروت نفذت لفئة {value} ريال من شبكة {network_name}',
                    'high'
                )
                
                return ConversationHandler.END
            
            card_id, encrypted_code = card
            decrypted_code = decrypt_data(encrypted_code)
            
            # Perform accounting transactions
            cur2 = conn.cursor()
            buyer_acc = get_or_create_user_wallet_account(cur2, user['id'])
            supplier_acc = get_or_create_user_wallet_account(cur2, supplier_id)
            
            cur2.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
            row_acc = cur2.fetchone()
            if not row_acc:
                ensure_base_accounts(cur2)
                cur2.execute('SELECT id FROM accounts WHERE code = ?', (ACCOUNT_CODE_BOT_COMMISSION_REVENUE,))
                row_acc = cur2.fetchone()
            commission_acc = row_acc[0]
            
            supplier_share = round(final_price * (1.0 - CARD_COMMISSION_RATE), 2)
            bot_commission = round(final_price * CARD_COMMISSION_RATE, 2)
            
            # Mark card as used and update user stats
            cursor.execute('UPDATE cards SET is_used = 1, used_at = CURRENT_TIMESTAMP, used_by = ? WHERE id = ?', (user['id'], card_id))
            cursor.execute('UPDATE users SET total_purchases = total_purchases + 1, total_spent = total_spent + ? WHERE id = ?', (final_price, user['id']))
            
            # Record promotion usage if applicable
            transaction_id = str(uuid.uuid4())
            if applied_promotion:
                cursor.execute('''
                    INSERT INTO promotion_usage (id, promotion_id, user_id, transaction_id, discount_applied)
                    VALUES (?, ?, ?, ?, ?)
                ''', (str(uuid.uuid4()), applied_promotion['id'], user['id'], transaction_id, discount_amount))
            
            # Update inventory
            network_id = row.get('network_id', f"net_{supplier_id}")
            update_inventory_stock(network_id, category_id, -1)
            
            # Create enhanced wallet transaction
            create_wallet_transaction(
                user['id'], 
                'debit', 
                final_price, 
                user['balance'], 
                user['balance'] - final_price,
                f'شراء كرت {value} ريال من {network_name}',
                card_id,
                {
                    'original_price': price,
                    'discount_applied': discount_amount,
                    'promotion_id': applied_promotion['id'] if applied_promotion else None,
                    'network_name': network_name,
                    'card_value': value
                }
            )
            
            conn.commit()
        finally:
            conn.close()
        
        # Post journal entries
        post_journal(
            description=f'Card purchase {card_id} by user {user["id"]}',
            created_by=user['id'],
            lines=[
                {'account_id': buyer_acc, 'debit': price, 'credit': 0.0, 'user_id': user['id'], 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': supplier_acc, 'debit': 0.0, 'credit': supplier_share, 'user_id': supplier_id, 'ref_type': 'card_purchase', 'ref_id': card_id},
                {'account_id': commission_acc, 'debit': 0.0, 'credit': bot_commission, 'user_id': None, 'ref_type': 'card_purchase', 'ref_id': card_id},
            ],
        )
        
        # Create transaction record
        create_transaction(
            user['id'], supplier_id, price, 'card_purchase', card_id,
            description=f'Purchase of {value} riyal card from {network_name}',
            commission_amount=bot_commission
        )
        
        # Update balances
        recalc_and_set_user_balance(user['id'])
        recalc_and_set_user_balance(supplier_id)
        
        # Log the purchase with enhanced details
        log_system_action(user['id'], 'card_purchase', f'Purchased card {card_id} for {final_price} riyal')
        log_activity(user['id'], 'purchase', f'Purchased {value} riyal card from {network_name}', {
            'card_id': card_id,
            'network_name': network_name,
            'original_price': price,
            'final_price': final_price,
            'discount_amount': discount_amount,
            'promotion_used': applied_promotion['title'] if applied_promotion else None
        })
        
        # Send purchase notification
        notification_msg = f'تم شراء كرت {value} ريال من {network_name}'
        if applied_promotion:
            notification_msg += f' مع خصم {discount_amount:.2f} ريال'
        
        send_smart_notification(
            user['id'],
            'purchase_success',
            '✅ تم الشراء بنجاح',
            notification_msg,
            'normal'
        )
        
        # Send success message with promotion details
        success_text = f"{EMOJIS['success']} **تم الشراء بنجاح!**\n\n"
        
        if applied_promotion:
            success_text += f"🎁 **تم تطبيق عرض:** {applied_promotion['title']}\n"
            success_text += f"💰 السعر الأصلي: {price:.2f} ريال\n"
            success_text += f"🎊 الخصم: {discount_amount:.2f} ريال\n"
            success_text += f"💳 المبلغ المدفوع: {final_price:.2f} ريال\n\n"
        
        success_text += "كود الكرت سيرسل لك في الرسالة التالية..."
        
        await context.bot.edit_message_text(
            chat_id=query.message.chat_id,
            message_id=processing_msg.message_id,
            text=success_text,
            parse_mode='Markdown'
        )
        
        # Send card code in separate message for security
        card_message = f"""
{EMOJIS['card']} **كود الكرت الخاص بك:**

`{decrypted_code}`

{EMOJIS['network']} الشبكة: **{network_name}**
{EMOJIS['money']} القيمة: **{value}** ريال
"""

        if applied_promotion:
            card_message += f"\n🎁 العرض المطبق: **{applied_promotion['title']}**"
            card_message += f"\n💰 وفرت: **{discount_amount:.2f}** ريال"

        card_message += f"""

{EMOJIS['warning']} **تنبيه مهم:**
• احفظ الكود في مكان آمن
• لا تشارك الكود مع أحد
• استخدم الكود قبل انتهاء صلاحيته

💳 رصيدك الحالي: **{user['balance'] - final_price:.2f}** ريال
"""
        
        await context.bot.send_message(
            chat_id=query.message.chat_id, 
            text=card_message,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت آخر', callback_data='buy_cards')],
                [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
            ]),
            parse_mode='Markdown'
        )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error completing purchase: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ أثناء عملية الشراء. يرجى المحاولة لاحقاً.")
        return ConversationHandler.END

# Transfer functionality
async def transfer_to_friend_handler(update: Update, context: CallbackContext) -> int:
    """Start transfer process"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return ConversationHandler.END
        
        update_user_activity(user['id'])
        
        # Recalculate balance
        recalc_and_set_user_balance(user['id'])
        user = get_user(query.from_user.id)  # Refresh data
        
        if user['balance'] <= 0:
            await query.edit_message_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي للتحويل!**\n\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{user['balance']:.2f}** ريال\n\n"
                f"يرجى شحن رصيدك أولاً.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["money"]} شحن الرصيد', callback_data='recharge_balance')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        text = f"""
{EMOJIS['transfer']} **تحويل رصيد لصديق**

{EMOJIS['wallet']} رصيدك الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['id']} أدخل رقم محفظة المستلم:
{EMOJIS['star']} يجب أن يكون 9 أرقام ويبدأ بـ 79
{EMOJIS['warning']} مثال: 791234567

أو اكتب /cancel للإلغاء
"""
        
        await query.edit_message_text(text, parse_mode='Markdown')
        return TRANSFER_TARGET
    except Exception as e:
        logger.error(f"Error in transfer_to_friend_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء التحويل.")
        return ConversationHandler.END

async def transfer_target(update: Update, context: CallbackContext) -> int:
    """Get transfer target wallet"""
    try:
        wallet = update.message.text.strip()
        
        if wallet.lower() == '/cancel':
            return await cancel(update, context)
        
        if not re.fullmatch(r'79\d{7}', wallet):
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رقم المحفظة غير صحيح!**\n\n"
                f"يرجى إدخال رقم محفظة صحيح:\n"
                f"• 9 أرقام تبدأ بـ 79\n"
                f"• مثال: 791234567\n\n"
                f"أعد المحاولة أو اكتب /cancel للإلغاء",
                parse_mode='Markdown'
            )
            return TRANSFER_TARGET
        
        sender = get_user(update.message.from_user.id)
        if wallet == sender['wallet_number']:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **لا يمكنك التحويل لنفسك!**\n\n"
                f"يرجى إدخال رقم محفظة مختلف."
            )
            return TRANSFER_TARGET
        
        target_user = get_user_by_wallet(wallet)
        if not target_user:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **لم يتم العثور على محفظة بهذا الرقم!**\n\n"
                f"تأكد من صحة الرقم وأعد المحاولة:\n"
                f"أو اكتب /cancel للإلغاء"
            )
            return TRANSFER_TARGET
        
        context.user_data['transfer_target_id'] = target_user['id']
        context.user_data['transfer_target_name'] = target_user['full_name']
        context.user_data['transfer_target_wallet'] = target_user['wallet_number']
        
        await update.message.reply_text(
            f"{EMOJIS['confirm']} **تم العثور على المستلم:**\n\n"
            f"{EMOJIS['user']} الاسم: **{target_user['full_name']}**\n"
            f"{EMOJIS['wallet']} المحفظة: `{target_user['wallet_number']}`\n\n"
            f"{EMOJIS['money']} الآن أدخل مبلغ التحويل (بالريال):\n"
            f"{EMOJIS['warning']} الحد الأدنى: 10 ريال\n\n"
            f"أو اكتب /cancel للإلغاء",
            parse_mode='Markdown'
        )
        return TRANSFER_AMOUNT
    except Exception as e:
        logger.error(f"Error in transfer_target: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def transfer_amount(update: Update, context: CallbackContext) -> int:
    """Get transfer amount"""
    try:
        amount_text = update.message.text.strip()
        
        if amount_text.lower() == '/cancel':
            return await cancel(update, context)
        
        try:
            amount = float(amount_text)
            if amount <= 0:
                raise ValueError()
            if amount < 10:
                await update.message.reply_text(
                    f"{EMOJIS['warning']} **المبلغ أقل من الحد الأدنى!**\n\n"
                    f"الحد الأدنى للتحويل: **10** ريال\n"
                    f"أدخل مبلغاً أكبر من أو يساوي 10 ريال."
                )
                return TRANSFER_AMOUNT
        except ValueError:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **مبلغ غير صحيح!**\n\n"
                f"يرجى إدخال مبلغ صحيح بالأرقام فقط\n"
                f"مثال: 100 أو 50.5\n\n"
                f"أو اكتب /cancel للإلغاء"
            )
            return TRANSFER_AMOUNT
        
        sender = get_user(update.message.from_user.id)
        # Recalculate balance
        recalc_and_set_user_balance(sender['id'])
        sender = get_user(update.message.from_user.id)  # Refresh data
        
        if amount > sender['balance']:
            await update.message.reply_text(
                f"{EMOJIS['warning']} **رصيدك غير كافي!**\n\n"
                f"{EMOJIS['money']} المبلغ المطلوب: **{amount}** ريال\n"
                f"{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال\n\n"
                f"أدخل مبلغاً أقل أو اشحن رصيدك.",
                parse_mode='Markdown'
            )
            return TRANSFER_AMOUNT
        
        context.user_data['transfer_amount'] = round(amount, 2)
        
        target_name = context.user_data['transfer_target_name']
        target_wallet = context.user_data['transfer_target_wallet']
        
        confirmation_text = f"""
{EMOJIS['transfer']} **تأكيد التحويل**

{EMOJIS['user']} المرسل: **{sender['full_name']}**
{EMOJIS['wallet']} محفظتك: `{sender['wallet_number']}`

{EMOJIS['user']} المستلم: **{target_name}**
{EMOJIS['wallet']} محفظة المستلم: `{target_wallet}`

{EMOJIS['money']} المبلغ: **{amount}** ريال
{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال
{EMOJIS['stats']} رصيدك بعد التحويل: **{sender['balance'] - amount:.2f}** ريال

هل تريد تأكيد التحويل؟
"""
        
        await update.message.reply_text(
            confirmation_text,
            reply_markup=ReplyKeyboardMarkup([
                [f'{EMOJIS["confirm"]} نعم، أكد التحويل'],
                [f'{EMOJIS["cancel"]} إلغاء العملية']
            ], one_time_keyboard=True, resize_keyboard=True),
            parse_mode='Markdown'
        )
        return TRANSFER_CONFIRM
    except Exception as e:
        logger.error(f"Error in transfer_amount: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

async def transfer_confirm(update: Update, context: CallbackContext) -> int:
    """Confirm and execute transfer"""
    try:
        choice = update.message.text.strip()
        
        if choice != f'{EMOJIS["confirm"]} نعم، أكد التحويل':
            await update.message.reply_text(
                f"{EMOJIS['cancel']} تم إلغاء عملية التحويل.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        sender = get_user(update.message.from_user.id)
        target_id = context.user_data.get('transfer_target_id')
        amount = float(context.user_data.get('transfer_amount', 0))
        
        if not target_id or amount <= 0:
            await update.message.reply_text(
                f"{EMOJIS['error']} حدث خطأ في البيانات. يرجى المحاولة مرة أخرى.",
                reply_markup=ReplyKeyboardRemove()
            )
            return ConversationHandler.END
        
        processing_msg = await update.message.reply_text(
            f"{EMOJIS['loading']} جاري معالجة التحويل...",
            reply_markup=ReplyKeyboardRemove()
        )
        
        try:
            conn = get_db_connection()
            cur = conn.cursor()
            sender_acc = get_or_create_user_wallet_account(cur, sender['id'])
            recv_acc = get_or_create_user_wallet_account(cur, target_id)
            conn.commit()
            conn.close()
            
            # Post journal entry
            post_journal(
                description=f'P2P transfer from {sender["id"]} to {target_id}',
                created_by=sender['id'],
                lines=[
                    {'account_id': sender_acc, 'debit': amount, 'credit': 0.0, 'user_id': sender['id'], 'ref_type': 'p2p_transfer', 'ref_id': str(target_id)},
                    {'account_id': recv_acc, 'debit': 0.0, 'credit': amount, 'user_id': target_id, 'ref_type': 'p2p_transfer', 'ref_id': str(sender['id'])},
                ],
            )
            
            # Create transaction record
            create_transaction(
                sender['id'], target_id, amount, 'p2p_transfer',
                description=f'Transfer from {sender["full_name"]} to {context.user_data["transfer_target_name"]}'
            )
            
            # Update balances
            recalc_and_set_user_balance(sender['id'])
            recalc_and_set_user_balance(target_id)
            
            # Log the transfer
            log_system_action(sender['id'], 'p2p_transfer', f'Transferred {amount} riyal to user {target_id}')
            
            # Get updated sender data
            sender = get_user(update.message.from_user.id)
            
            success_message = f"""
{EMOJIS['success']} **تم التحويل بنجاح!**

{EMOJIS['money']} تم تحويل **{amount}** ريال
{EMOJIS['user']} إلى: **{context.user_data['transfer_target_name']}**
{EMOJIS['wallet']} رصيدك الحالي: **{sender['balance']:.2f}** ريال

{EMOJIS['time']} وقت التحويل: {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
            
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=processing_msg.message_id,
                text=success_message,
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل آخر', callback_data='transfer_to_friend')],
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            
            # Notify receiver
            try:
                target_user = get_user_by_id(target_id)
                await context.bot.send_message(
                    target_user['telegram_id'],
                    f"{EMOJIS['money']} **تم استلام تحويل جديد!**\n\n"
                    f"{EMOJIS['user']} من: **{sender['full_name']}**\n"
                    f"{EMOJIS['money']} المبلغ: **{amount}** ريال\n"
                    f"{EMOJIS['time']} الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                    parse_mode='Markdown'
                )
            except Exception:
                pass  # If we can't notify receiver, that's okay
            
            return ConversationHandler.END
        except Exception as e:
            logger.error(f"Error processing transfer: {e}")
            await context.bot.edit_message_text(
                chat_id=update.message.chat_id,
                message_id=processing_msg.message_id,
                text=f"{EMOJIS['error']} حدث خطأ أثناء التحويل. يرجى المحاولة لاحقاً."
            )
            return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in transfer_confirm: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.")
        return ConversationHandler.END

# Statistics and user info
async def my_stats(update: Update, context: CallbackContext) -> int:
    """Show user statistics"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            return await start(update, context)
        
        update_user_activity(user['id'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            # Get comprehensive statistics
            cursor.execute("SELECT COUNT(*), COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'card_purchase'", (user['id'],))
            purchases_count, purchases_total = cursor.fetchone()
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE to_user = ? AND type != 'card_purchase'", (user['id'],))
            incoming_total = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(amount),0) FROM transactions WHERE from_user = ? AND type = 'p2p_transfer'", (user['id'],))
            outgoing_transfers = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id = ?", (user['id'],))
            referrals_count = cursor.fetchone()[0] or 0
            
            cursor.execute("SELECT COALESCE(SUM(bonus_amount),0) FROM referrals WHERE referrer_id = ? AND awarded = 1", (user['id'],))
            referral_earnings = cursor.fetchone()[0] or 0
            
            # Get last transaction
            cursor.execute("SELECT type, amount, created_at FROM transactions WHERE from_user = ? OR to_user = ? ORDER BY created_at DESC LIMIT 1", (user['id'], user['id']))
            last_transaction = cursor.fetchone()
        finally:
            conn.close()
        
        last_tx_text = "لا توجد معاملات"
        if last_transaction:
            tx_type_map = {
                'card_purchase': 'شراء كرت',
                'p2p_transfer': 'تحويل رصيد',
                'wallet_recharge': 'شحن رصيد',
                'agent_commission': 'عمولة وكيل'
            }
            tx_type = tx_type_map.get(last_transaction[0], last_transaction[0])
            last_tx_text = f"{tx_type} - {last_transaction[1]} ريال ({last_transaction[2][:10]})"
        
        role_names = {
            'customer': 'عميل',
            'agent': 'وكيل',
            'supplier': 'مزود',
            'admin': 'مشرف',
            'super_admin': 'مشرف أعلى'
        }
        
        text = f"""
{EMOJIS['stats']} **إحصائياتك الشاملة**

{EMOJIS['user']} **المعلومات الأساسية:**
الاسم: **{user['full_name']}**
الدور: **{role_names.get(user['role'], user['role'])}**
{EMOJIS['wallet']} المحفظة: `{user['wallet_number']}`
{EMOJIS['money']} الرصيد: **{user['balance']:.2f}** ريال

{EMOJIS['purchase']} **عمليات الشراء:**
عدد المشتريات: **{purchases_count}**
إجمالي الإنفاق: **{purchases_total:.2f}** ريال

{EMOJIS['transfer']} **التحويلات:**
التحويلات الصادرة: **{outgoing_transfers:.2f}** ريال
التحويلات الواردة: **{incoming_total:.2f}** ريال

{EMOJIS['user']} **الإحالات:**
عدد الدعوات: **{referrals_count}**
أرباح الإحالة: **{referral_earnings:.2f}** ريال

{EMOJIS['time']} **آخر معاملة:**
{last_tx_text}

{EMOJIS['date']} **تاريخ التسجيل:**
{user.get('created_at', 'غير محدد')[:10]}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["purchase"]} شراء كرت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["user"]} دعوة أصدقاء', callback_data='invite_friends')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if update.message:
            await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.callback_query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الإحصائيات."
        
        if update.message:
            await update.message.reply_text(error_msg)
        else:
            await update.callback_query.edit_message_text(error_msg)
        
        return ConversationHandler.END

# Placeholder handlers for missing features
async def invite_friends_handler(update: Update, context: CallbackContext):
    """Handle invite friends"""
    try:
        user = get_user(update.callback_query.from_user.id)
        invite_link = f"https://t.me/Vsjsgshh_bot?start=ref_{user['invite_code']}"
        
        text = f"""
{EMOJIS['user']} **دعوة الأصدقاء**

{EMOJIS['star']} رابط دعوتك الخاص:
{invite_link}

{EMOJIS['money']} **المكافآت:**
• احصل على مكافأة عند تسجيل كل صديق
• 10% من أول شحن لكل صديق يدعوه
• مكافآت إضافية للمستخدمين النشطين

{EMOJIS['fire']} **كيفية الاستخدام:**
1. انسخ الرابط أعلاه
2. شاركه مع أصدقائك
3. عندما يسجلون سيتم احتساب المكافأة لك تلقائياً

{EMOJIS['stats']} دعواتك المقبولة: {user.get('total_referrals', 0)}
"""
        
        await update.callback_query.edit_message_text(
            text, 
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in invite_friends_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

async def recharge_balance_handler(update: Update, context: CallbackContext):
    """Handle balance recharge"""
    try:
        user = get_user(update.callback_query.from_user.id)
        text = f"""
{EMOJIS['money']} **شحن الرصيد**

{EMOJIS['wallet']} رقم محفظتك: `{user['wallet_number']}`
{EMOJIS['money']} رصيدك الحالي: **{user['balance']:.2f}** ريال

{EMOJIS['warning']} **طرق الشحن:**
• تحويل من صديق
• شحن من وكيل معتمد
• الحصول على مكافآت الإحالة

{EMOJIS['phone']} **للشحن الفوري:**
تواصل مع الدعم عبر الرقم المرفق في المساعدة

{EMOJIS['star']} **نصائح:**
• تأكد من رقم المحفظة قبل إعطائه للوكيل
• احتفظ بإيصال التحويل للمراجعة
"""
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton(f'{EMOJIS["transfer"]} تحويل من صديق', callback_data='transfer_to_friend')],
                [InlineKeyboardButton(f'❓ المساعدة', callback_data='customer_help')],
                [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
            ]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in recharge_balance_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

async def customer_help_handler(update: Update, context: CallbackContext):
    """Handle customer help"""
    try:
        text = f"""
{EMOJIS['star']} **مركز المساعدة**

{EMOJIS['fire']} **الأسئلة الشائعة:**

❓ **كيف أشتري كرت؟**
• اختر "شراء كروت" من القائمة
• اختر الشبكة والفئة المطلوبة
• تأكد من وجود رصيد كافي

❓ **كيف أشحن رصيدي؟**
• من خلال تحويل من صديق
• من خلال وكيل معتمد
• مكافآت الإحالة

❓ **كيف أدعو أصدقاء؟**
• اختر "دعوة أصدقاء" من القائمة
• انسخ رابط الدعوة وشاركه
• احصل على مكافآت عند تسجيلهم

{EMOJIS['phone']} **التواصل:**
• للاستفسارات: @YemenNetSupport
• للشكاوى: @YemenNetAdmin
• الطوارئ: 967712345678

{EMOJIS['time']} **ساعات العمل:**
السبت - الخميس: 8 صباحاً - 10 مساءً
الجمعة: 2 ظهراً - 10 مساءً
"""
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
            ]]),
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in customer_help_handler: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ.")

# Enhanced feature handlers

async def enhanced_wallet_handler(update: Update, context: CallbackContext):
    """Enhanced wallet with transaction history and analytics"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Get wallet transactions
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM wallet_transactions 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user['id'],))
        transactions = cursor.fetchall()
        
        # Calculate statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                SUM(CASE WHEN transaction_type = 'credit' THEN amount ELSE 0 END) as total_credits,
                SUM(CASE WHEN transaction_type = 'debit' THEN amount ELSE 0 END) as total_debits
            FROM wallet_transactions 
            WHERE user_id = ?
        ''', (user['id'],))
        stats = cursor.fetchone()
        
        conn.close()
        
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

{EMOJIS['money']} الرصيد الحالي: `{user['balance']:.2f}` ريال
{EMOJIS['id']} رقم المحفظة: `{user['wallet_number']}`

📊 **إحصائيات المحفظة:**
🔢 إجمالي المعاملات: {stats['total_transactions'] or 0}
💚 إجمالي الإيداعات: {stats['total_credits'] or 0:.2f} ريال
💸 إجمالي المصروفات: {stats['total_debits'] or 0:.2f} ريال

📋 **آخر المعاملات:**
"""
        
        if transactions:
            for i, trans in enumerate(transactions[:5], 1):
                trans_type = "➕ إيداع" if trans['transaction_type'] == 'credit' else "➖ سحب"
                wallet_text += f"\n{i}. {trans_type}: {trans['amount']:.2f} ريال"
                wallet_text += f"\n   📅 {trans['created_at'][:16]}"
                if trans['description']:
                    wallet_text += f"\n   📝 {trans['description']}"
                wallet_text += "\n"
        else:
            wallet_text += "\nلا توجد معاملات حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'💸 تحويل رصيد', callback_data='transfer_to_friend'),
             InlineKeyboardButton(f'💰 شحن رصيد', callback_data='recharge_balance')],
            [InlineKeyboardButton(f'📋 تاريخ المعاملات الكامل', callback_data='full_transaction_history'),
             InlineKeyboardButton(f'📊 تقرير الإنفاق', callback_data='spending_report')],
            [InlineKeyboardButton(f'⚙️ إعدادات المحفظة', callback_data='wallet_settings'),
             InlineKeyboardButton(f'🔔 تنبيهات الرصيد', callback_data='balance_alerts')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            wallet_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Log activity
        log_activity(user['id'], 'wallet_access', 'Accessed enhanced wallet')
        
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض المحفظة.")

async def personal_reports_handler(update: Update, context: CallbackContext):
    """Personal reports and analytics for customers"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Generate personal analytics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get purchase statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as total_purchases,
                SUM(amount) as total_spent,
                AVG(amount) as avg_purchase
            FROM transactions 
            WHERE from_user = ? AND type = 'purchase'
        ''', (user['id'],))
        purchase_stats = cursor.fetchone()
        
        # Get this month's statistics
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_purchases,
                SUM(amount) as monthly_spent
            FROM transactions 
            WHERE from_user = ? AND type = 'purchase'
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user['id'],))
        monthly_stats = cursor.fetchone()
        
        # Get network preferences
        cursor.execute('''
            SELECT n.name, COUNT(*) as count
            FROM transactions t
            JOIN cards c ON t.reference_id = c.id
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE t.from_user = ? AND t.type = 'purchase'
            GROUP BY n.name
            ORDER BY count DESC
            LIMIT 3
        ''', (user['id'],))
        network_prefs = cursor.fetchall()
        
        conn.close()
        
        report_text = f"""
📊 **تقاريري الشخصية** 📊

👤 **المستخدم:** {user['full_name']}

📈 **إحصائيات الشراء:**
🛒 إجمالي المشتريات: {purchase_stats['total_purchases'] or 0}
💰 إجمالي المبلغ: {purchase_stats['total_spent'] or 0:.2f} ريال
📊 متوسط الشراء: {purchase_stats['avg_purchase'] or 0:.2f} ريال

📅 **إحصائيات هذا الشهر:**
🛒 مشتريات الشهر: {monthly_stats['monthly_purchases'] or 0}
💰 إنفاق الشهر: {monthly_stats['monthly_spent'] or 0:.2f} ريال

🌐 **الشبكات المفضلة:**
"""
        
        if network_prefs:
            for i, (network, count) in enumerate(network_prefs, 1):
                report_text += f"\n{i}. {network}: {count} مرة"
        else:
            report_text += "\nلا توجد مشتريات حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'📊 تقرير مفصل', callback_data='detailed_personal_report'),
             InlineKeyboardButton(f'📈 رسم بياني', callback_data='spending_chart')],
            [InlineKeyboardButton(f'📅 تقرير شهري', callback_data='monthly_report'),
             InlineKeyboardButton(f'📄 تصدير التقرير', callback_data='export_personal_report')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            report_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Log activity
        log_activity(user['id'], 'report_access', 'Accessed personal reports')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقارير.")

async def my_ratings_handler(update: Update, context: CallbackContext):
    """Show user ratings and reviews"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Get user rating summary
        rating_summary = calculate_user_rating(user['id'])
        
        # Get recent ratings received
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT r.*, u.full_name
            FROM ratings r
            JOIN users u ON r.rater_id = u.id
            WHERE r.rated_user_id = ? AND r.is_visible = 1
            ORDER BY r.created_at DESC
            LIMIT 5
        ''', (user['id'],))
        recent_ratings = cursor.fetchall()
        
        # Get ratings given by user
        cursor.execute('''
            SELECT r.*, u.full_name
            FROM ratings r
            JOIN users u ON r.rated_user_id = u.id
            WHERE r.rater_id = ?
            ORDER BY r.created_at DESC
            LIMIT 3
        ''', (user['id'],))
        given_ratings = cursor.fetchall()
        
        conn.close()
        
        stars = "⭐" * int(rating_summary['average_rating'])
        
        ratings_text = f"""
⭐ **تقييماتي** ⭐

📊 **ملخص التقييمات:**
{stars} متوسط التقييم: {rating_summary['average_rating']}/5
🔢 إجمالي التقييمات: {rating_summary['total_ratings']}

📈 **توزيع التقييمات:**
⭐⭐⭐⭐⭐ {rating_summary['rating_distribution'][5]} تقييم
⭐⭐⭐⭐ {rating_summary['rating_distribution'][4]} تقييم
⭐⭐⭐ {rating_summary['rating_distribution'][3]} تقييم
⭐⭐ {rating_summary['rating_distribution'][2]} تقييم
⭐ {rating_summary['rating_distribution'][1]} تقييم

📝 **آخر التقييمات المستلمة:**
"""
        
        if recent_ratings:
            for rating in recent_ratings:
                stars = "⭐" * rating['rating']
                ratings_text += f"\n{stars} من {rating['full_name']}"
                if rating['review_text']:
                    ratings_text += f"\n💬 {rating['review_text'][:50]}..."
                ratings_text += f"\n📅 {rating['created_at'][:10]}\n"
        else:
            ratings_text += "\nلا توجد تقييمات حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'📝 تقييماتي للآخرين', callback_data='my_given_ratings'),
             InlineKeyboardButton(f'⭐ إضافة تقييم', callback_data='add_rating')],
            [InlineKeyboardButton(f'📊 تفاصيل التقييمات', callback_data='detailed_ratings'),
             InlineKeyboardButton(f'🔔 إعدادات التقييم', callback_data='rating_settings')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            ratings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات.")

async def my_notifications_handler(update: Update, context: CallbackContext):
    """Show user notifications"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Get notifications
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM smart_notifications 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user['id'],))
        notifications = cursor.fetchall()
        
        # Get unread count
        cursor.execute('''
            SELECT COUNT(*) as unread_count
            FROM smart_notifications 
            WHERE user_id = ? AND is_read = 0
        ''', (user['id'],))
        unread_count = cursor.fetchone()['unread_count']
        
        conn.close()
        
        notifications_text = f"""
🔔 **إشعاراتي** 🔔

📨 إجمالي الإشعارات: {len(notifications)}
🔴 غير مقروءة: {unread_count}

📋 **الإشعارات الحديثة:**
"""
        
        if notifications:
            for i, notif in enumerate(notifications[:7], 1):
                status = "🔴" if not notif['is_read'] else "✅"
                priority_emoji = "🚨" if notif['priority'] == 'high' else "📢" if notif['priority'] == 'normal' else "ℹ️"
                
                notifications_text += f"\n{i}. {status} {priority_emoji} **{notif['title']}**"
                notifications_text += f"\n   📝 {notif['message'][:50]}..."
                notifications_text += f"\n   📅 {notif['created_at'][:16]}\n"
        else:
            notifications_text += "\nلا توجد إشعارات حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'✅ تحديد الكل كمقروء', callback_data='mark_all_read'),
             InlineKeyboardButton(f'🗑️ حذف المقروءة', callback_data='delete_read_notifications')],
            [InlineKeyboardButton(f'⚙️ إعدادات الإشعارات', callback_data='notification_settings'),
             InlineKeyboardButton(f'🔔 إشعارات العروض', callback_data='promotion_notifications')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            notifications_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
        # Mark notifications as read when viewed
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE smart_notifications 
                SET is_read = 1, read_at = ?
                WHERE user_id = ? AND is_read = 0
            ''', (datetime.now(), user['id']))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Error marking notifications as read: {e}")
        
    except Exception as e:
        logger.error(f"Error in notifications handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإشعارات.")

async def promotions_handler(update: Update, context: CallbackContext):
    """Show available promotions and offers"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Get active promotions
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM promotions 
            WHERE is_active = 1 
            AND start_date <= ? 
            AND end_date >= ?
            AND (target_user_role IS NULL OR target_user_role = ?)
            ORDER BY created_at DESC
        ''', (datetime.now(), datetime.now(), user['role']))
        promotions = cursor.fetchall()
        
        # Get user's promotion usage
        cursor.execute('''
            SELECT promotion_id, COUNT(*) as usage_count
            FROM promotion_usage 
            WHERE user_id = ?
            GROUP BY promotion_id
        ''', (user['id'],))
        usage_data = {row['promotion_id']: row['usage_count'] for row in cursor.fetchall()}
        
        conn.close()
        
        promotions_text = f"""
🎁 **العروض والخصومات** 🎁

💫 العروض المتاحة لك:
"""
        
        if promotions:
            for i, promo in enumerate(promotions, 1):
                used_count = usage_data.get(promo['id'], 0)
                remaining = promo['max_usage_per_user'] - used_count
                
                if remaining > 0:
                    discount_text = f"{promo['discount_percentage']}%" if promo['discount_percentage'] > 0 else f"{promo['discount_amount']} ريال"
                    
                    promotions_text += f"\n{i}. 🔥 **{promo['title']}**"
                    promotions_text += f"\n   💰 خصم: {discount_text}"
                    promotions_text += f"\n   📝 {promo['description'][:60]}..."
                    promotions_text += f"\n   🔢 متبقي: {remaining} مرة"
                    promotions_text += f"\n   📅 حتى: {promo['end_date'][:10]}\n"
        else:
            promotions_text += "\nلا توجد عروض متاحة حالياً"
        
        promotions_text += f"\n💡 **نصيحة:** استخدم العروض عند الشراء للحصول على أفضل الأسعار!"
        
        keyboard = [
            [InlineKeyboardButton(f'🛒 تسوق بالعروض', callback_data='shop_with_promotions'),
             InlineKeyboardButton(f'📋 عروضي المستخدمة', callback_data='used_promotions')],
            [InlineKeyboardButton(f'🔔 تنبيهات العروض', callback_data='promotion_alerts'),
             InlineKeyboardButton(f'📊 توفيراتي', callback_data='savings_summary')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            promotions_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العروض.")

async def account_settings_handler(update: Update, context: CallbackContext):
    """Account settings and preferences"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم غير موجود.")
            return
        
        # Get notification preferences
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM notification_preferences WHERE user_id = ?
        ''', (user['id'],))
        prefs = cursor.fetchone()
        
        # Get user permissions
        permissions = get_user_permissions(user['id'])
        
        conn.close()
        
        # Default preferences if not set
        if not prefs:
            prefs = {
                'balance_alerts': True,
                'transaction_alerts': True,
                'promotion_alerts': True,
                'system_alerts': True,
                'rating_requests': True
            }
        
        settings_text = f"""
⚙️ **إعدادات الحساب** ⚙️

👤 **معلومات الحساب:**
📛 الاسم: {user['full_name']}
📞 الهاتف: {user['phone']}
🏷️ الدور: {user['role']}
💳 رقم المحفظة: {user['wallet_number']}
✅ الحالة: {"مفعل" if user['is_active'] else "غير مفعل"}

🔔 **إعدادات الإشعارات:**
💰 تنبيهات الرصيد: {"✅" if prefs['balance_alerts'] else "❌"}
💸 تنبيهات المعاملات: {"✅" if prefs['transaction_alerts'] else "❌"}
🎁 تنبيهات العروض: {"✅" if prefs['promotion_alerts'] else "❌"}
🔔 التنبيهات العامة: {"✅" if prefs['system_alerts'] else "❌"}
⭐ طلبات التقييم: {"✅" if prefs['rating_requests'] else "❌"}

🔐 **الصلاحيات الخاصة:**
"""
        
        if permissions:
            for perm in permissions:
                settings_text += f"• {perm}\n"
        else:
            settings_text += "لا توجد صلاحيات خاصة"
        
        keyboard = [
            [InlineKeyboardButton(f'📝 تعديل المعلومات', callback_data='edit_profile'),
             InlineKeyboardButton(f'🔔 إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton(f'🔒 تغيير كلمة المرور', callback_data='change_password'),
             InlineKeyboardButton(f'🛡️ إعدادات الأمان', callback_data='security_settings')],
            [InlineKeyboardButton(f'📱 ربط الجهاز', callback_data='device_linking'),
             InlineKeyboardButton(f'📋 تصدير البيانات', callback_data='export_data')],
            [InlineKeyboardButton(f'{EMOJIS["back"]} العودة للقائمة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            settings_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in account settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإعدادات.")

# Main button handler
async def button_click_handler(update: Update, context: CallbackContext):
    """Handle all button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        data = query.data
        
        logger.info(f'Received callback: {data} from user {query.from_user.id}')
        
        # Route to appropriate handler
        if data == 'buy_cards':
            return await buy_cards(update, context)
        elif data == 'recharge_balance':
            return await recharge_balance_handler(update, context)
        elif data == 'transfer_to_friend':
            return await transfer_to_friend_handler(update, context)
        elif data == 'invite_friends':
            return await invite_friends_handler(update, context)
        elif data == 'customer_help':
            return await customer_help_handler(update, context)
        elif data == 'show_balance':
            return await show_balance(update, context)
        elif data == 'my_stats':
            return await my_stats(update, context)
        elif data == 'main_menu':
            return await main_menu_handler(update, context)
        elif data.startswith('network_'):
            return await select_category(update, context)
        elif data.startswith('category_'):
            return await confirm_purchase(update, context)
        elif data == 'complete_purchase':
            return await complete_purchase(update, context)
        # Enhanced feature routes
        elif data == 'enhanced_wallet':
            return await enhanced_wallet_handler(update, context)
        elif data == 'personal_reports':
            return await personal_reports_handler(update, context)
        elif data == 'my_ratings':
            return await my_ratings_handler(update, context)
        elif data == 'my_notifications':
            return await my_notifications_handler(update, context)
        elif data == 'promotions':
            return await promotions_handler(update, context)
        elif data == 'account_settings':
            return await account_settings_handler(update, context)
        else:
            # Handle not implemented features
            await query.edit_message_text(
                f"{EMOJIS['warning']} **هذه الميزة قيد التطوير**\n\n"
                f"سيتم إضافتها في التحديث القادم قريباً.\n"
                f"شكراً لصبركم!",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')
                ]]),
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Error in button_click_handler: {e}")
        try:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        except:
            pass
        return ConversationHandler.END

def main() -> None:
    """Main function to run the bot"""
    try:
        # Initialize database and setup
        init_db()
        setup_super_admin()
        
        # Create application
        persistence = PicklePersistence(filepath='yemen_net_bot_data')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Set bot commands
        try:
            logger.info("Setting bot commands...")
            application.bot.set_my_commands(QUICK_COMMANDS)
            application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
            logger.info("Bot commands set successfully")
        except Exception as e:
            logger.warning(f'Failed setting commands/menu: {e}')
        
        # Create conversation handler
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', start),
                CommandHandler('menu', quick_menu),
                CommandHandler('balance', show_balance),
                CommandHandler('buy', lambda u, c: buy_cards(u, c)),
                CommandHandler('stats', my_stats),
                CommandHandler('transfer', transfer_to_friend_handler),
                CommandHandler('help', customer_help_handler),
            ],
            states={
                GET_FULL_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_full_name)],
                GET_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
                CHOOSE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_role)],
                SELECT_NETWORK: [CallbackQueryHandler(select_category, pattern='^network_')],
                SELECT_CATEGORY: [CallbackQueryHandler(confirm_purchase, pattern='^category_')],
                CONFIRM_PURCHASE: [CallbackQueryHandler(complete_purchase, pattern='^complete_purchase$')],
                TRANSFER_TARGET: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_target)],
                TRANSFER_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_amount)],
                TRANSFER_CONFIRM: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_confirm)],
            },
            fallbacks=[
                CommandHandler('cancel', cancel),
                CallbackQueryHandler(main_menu_handler, pattern='^main_menu$'),
                CallbackQueryHandler(cancel, pattern='^cancel'),
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), cancel),
            ],
            name='yemen_net_conversation',
            persistent=True,
            allow_reentry=True,
        )
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_click_handler))
        
        # Start the bot
        logger.info(f'{EMOJIS["fire"]} بدء تشغيل بوت كروت الإنترنت اليمني...')
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"Critical error in main: {e}")
        raise

if __name__ == '__main__':
    main()