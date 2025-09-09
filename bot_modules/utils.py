#!/usr/bin/env python3
"""
Utilities module for Pottagrm Enhanced Bot
Contains helper functions and common operations
"""

import logging
import uuid
import base64
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Tuple, Any
from bot_modules.config import *
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

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

# User management utilities
def get_user(telegram_id: int):
    """Get user by telegram ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE telegram_id = ?', (telegram_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        return None

def get_user_by_id(user_id: int):
    """Get user by internal database ID"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger.error(f"Error getting user by ID: {e}")
        return None

def update_user_activity(user_id: int):
    """Update user's last activity timestamp"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET last_activity = ? WHERE id = ?', 
                      (datetime.now(), user_id))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error updating user activity: {e}")

def log_system_action(user_id: int, action: str, details: str):
    """Log system action for audit trail"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO system_logs (user_id, action, details) 
            VALUES (?, ?, ?)
        ''', (user_id, action, details))
        conn.commit()
        conn.close()
    except Exception as e:
        logger.error(f"Error logging system action: {e}")

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
        # Silently fail for logging to avoid disrupting user experience
        logger.error(f"Error logging activity: {e}")
        pass

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

# Permission management
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

# Utility functions for UI
def format_user_info(user) -> str:
    """Format user information for display"""
    if not user:
        return "معلومات المستخدم غير متوفرة"
    
    role_name = USER_ROLES.get(user['role'], user['role'])
    status = "مفعل" if user['is_active'] else "غير مفعل"
    
    return f"""
{EMOJIS['user']} **{user['full_name']}**
{EMOJIS['phone']} {user['phone']}
🏷️ {role_name}
{EMOJIS['wallet']} {user['balance']:.2f} ريال
{EMOJIS['id']} {user['wallet_number']}
📊 حالة الحساب: {status}
"""

def create_transaction(from_user: int, to_user: int, amount: float, 
                      transaction_type: str, reference_id: str = None,
                      description: str = None, commission_amount: float = 0.0):
    """Create a transaction record"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        transaction_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, reference_id, description, commission_amount)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (transaction_id, from_user, to_user, amount, transaction_type, 
              reference_id, description, commission_amount))
        
        conn.commit()
        conn.close()
        return transaction_id
    except Exception as e:
        logger.error(f"Error creating transaction: {e}")
        return None

def recalc_and_set_user_balance(user_id: int):
    """Recalculate and update user balance"""
    import time
    max_retries = 3
    retry_delay = 0.1
    
    for attempt in range(max_retries):
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Calculate balance from transactions (no status check as it may not exist)
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as credits,
                    COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as debits
                FROM transactions 
                WHERE to_user = ? OR from_user = ?
            ''', (user_id, user_id, user_id, user_id))
            
            result = cursor.fetchone()
            credits = result[0] if result[0] else 0
            debits = result[1] if result[1] else 0
            new_balance = credits - debits
            
            # Update user balance
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_balance, user_id))
            
            conn.commit()
            conn.close()
            return new_balance
            
        except Exception as e:
            try:
                if 'conn' in locals():
                    conn.close()
            except:
                pass
                
            if "database is locked" in str(e).lower() and attempt < max_retries - 1:
                # Reduce logging noise and use shorter delays
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 1.5, 0.5)  # Cap at 0.5 seconds
                continue
            else:
                # Only log final failure, not individual retries
                if attempt == max_retries - 1:
                    logger.debug(f"Balance calculation skipped for user {user_id} (database busy)")
                return 0
    
    return 0

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

def is_super_admin(user_id: int) -> bool:
    """Check if user is super admin"""
    user = get_user(user_id)
    return user and user['role'] == 'super_admin'

def is_admin(user_id: int) -> bool:
    """Check if user is admin or super admin"""
    user = get_user(user_id)
    return user and user['role'] in ['admin', 'super_admin']

# Enhanced supplier functions
def generate_supplier_code():
    """Generate a unique 6-digit supplier code starting with 80"""
    import random
    conn = get_db_connection()
    cursor = conn.cursor()
    
    for _ in range(100):  # Try up to 100 times
        # Generate 6-digit code starting with 80
        code = '80' + ''.join(str(random.randint(0, 9)) for _ in range(4))
        
        # Check if code already exists
        cursor.execute('SELECT 1 FROM supplier_codes WHERE supplier_code = ?', (code,))
        if not cursor.fetchone():
            conn.close()
            return code
    
    conn.close()
    # If all attempts fail, use timestamp-based approach
    import time
    return '80' + str(int(time.time()))[-4:]

def get_or_create_supplier_code(supplier_id):
    """Get existing supplier code or create new one"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if supplier already has a code
    cursor.execute('SELECT supplier_code FROM supplier_codes WHERE supplier_id = ?', (supplier_id,))
    result = cursor.fetchone()
    
    if result:
        conn.close()
        return result['supplier_code']
    
    # Create new code
    code = generate_supplier_code()
    code_id = str(uuid.uuid4())
    
    cursor.execute('''
        INSERT INTO supplier_codes (id, supplier_id, supplier_code)
        VALUES (?, ?, ?)
    ''', (code_id, supplier_id, code))
    
    conn.commit()
    conn.close()
    return code

def validate_card_code(card_code):
    """Validate Yemen network card code (6-14 digits)"""
    if not card_code:
        return False, "رقم الكارت فارغ"
    
    # Remove any spaces or special characters
    cleaned_code = ''.join(filter(str.isdigit, str(card_code)))
    
    if len(cleaned_code) < 6:
        return False, "رقم الكارت يجب أن يحتوي على 6 أرقام على الأقل"
    
    if len(cleaned_code) > 14:
        return False, "رقم الكارت يجب ألا يزيد عن 14 رقم"
    
    return True, cleaned_code

def process_uploaded_cards(file_content, supplier_id, network_id, batch_id, selected_category=None):
    """Process uploaded cards from text or Excel file with category support"""
    import io
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    successful_cards = 0
    failed_cards = 0
    errors = []
    
    try:
        # Try to parse as text first
        lines = file_content.strip().split('\n')
        
        for line_num, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
                
            # Try to parse line format: "card_code,value,category" or "card_code,value" or just "card_code"
            parts = line.split(',')
            card_code = parts[0].strip()
            
            # Default value or from file
            if len(parts) > 1:
                try:
                    card_value = float(parts[1].strip())
                except ValueError:
                    card_value = 0.0
                    errors.append(f"السطر {line_num}: قيمة غير صحيحة '{parts[1]}', تم استخدام 0")
            else:
                card_value = 0.0
            
            # Category handling
            if len(parts) > 2:
                try:
                    card_category = int(parts[2].strip())
                    # Validate category
                    if card_category not in [200, 300, 500, 1000, 2000, 5000, 10000]:
                        card_category = selected_category or 200
                        errors.append(f"السطر {line_num}: فئة غير صحيحة '{parts[2]}', تم استخدام {card_category}")
                except ValueError:
                    card_category = selected_category or 200
                    errors.append(f"السطر {line_num}: فئة غير صحيحة '{parts[2]}', تم استخدام {card_category}")
            else:
                card_category = selected_category or 200
            
            # Auto-detect category from value if not specified
            if card_value > 0 and (selected_category is None and len(parts) <= 2):
                if card_value <= 200:
                    card_category = 200
                elif card_value <= 300:
                    card_category = 300
                elif card_value <= 500:
                    card_category = 500
                elif card_value <= 1000:
                    card_category = 1000
                elif card_value <= 2000:
                    card_category = 2000
                elif card_value <= 5000:
                    card_category = 5000
                else:
                    card_category = 10000
            
            # Validate card code
            is_valid, result = validate_card_code(card_code)
            if not is_valid:
                failed_cards += 1
                errors.append(f"السطر {line_num}: {result} - '{card_code}'")
                continue
            
            card_code = result
            
            # Check if card already exists
            cursor.execute('SELECT 1 FROM network_cards WHERE card_code = ?', (card_code,))
            if cursor.fetchone():
                failed_cards += 1
                errors.append(f"السطر {line_num}: الكارت موجود مسبقاً - '{card_code}'")
                continue
            
            # Insert card
            card_id = str(uuid.uuid4())
            cursor.execute('''
                INSERT INTO network_cards (id, supplier_id, network_id, card_code, card_value, card_category, upload_batch_id)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (card_id, supplier_id, network_id, card_code, card_value, card_category, batch_id))
            
            successful_cards += 1
        
        # Update batch statistics
        cursor.execute('''
            UPDATE card_upload_batches 
            SET successful_cards = ?, failed_cards = ?, upload_status = ?, error_details = ?
            WHERE id = ?
        ''', (successful_cards, failed_cards, 
              'completed' if failed_cards == 0 else 'completed_with_errors',
              '\n'.join(errors[:50]),  # Limit error details
              batch_id))
        
        conn.commit()
        
    except Exception as e:
        logger.error(f"Error processing uploaded cards: {e}")
        cursor.execute('''
            UPDATE card_upload_batches 
            SET upload_status = 'failed', error_details = ?
            WHERE id = ?
        ''', (str(e), batch_id))
        conn.commit()
        raise
    
    finally:
        conn.close()
    
    return successful_cards, failed_cards, errors

def search_networks(search_term, user_id=None):
    """Search networks by name or supplier code"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Search by network name or supplier code
    if user_id:
        # Search user's own networks
        cursor.execute('''
            SELECT n.*, sc.supplier_code, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN supplier_codes sc ON n.supplier_id = sc.supplier_id
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.supplier_id = ? AND (
                n.name LIKE ? OR 
                sc.supplier_code LIKE ?
            )
            ORDER BY n.name
        ''', (user_id, f'%{search_term}%', f'%{search_term}%'))
    else:
        # Search all networks (for admins)
        cursor.execute('''
            SELECT n.*, sc.supplier_code, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN supplier_codes sc ON n.supplier_id = sc.supplier_id
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.name LIKE ? OR sc.supplier_code LIKE ?
            ORDER BY n.name
        ''', (f'%{search_term}%', f'%{search_term}%'))
    
    results = cursor.fetchall()
    conn.close()
    return results

def search_cards_by_category(supplier_id, category=None, network_id=None):
    """Search cards by category and network"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            nc.*, 
            n.name as network_name,
            ccr.category_name
        FROM network_cards nc
        LEFT JOIN networks n ON nc.network_id = n.id
        LEFT JOIN card_categories_ref ccr ON nc.card_category = ccr.category_value
        WHERE nc.supplier_id = ?
    '''
    
    params = [supplier_id]
    
    if category:
        query += ' AND nc.card_category = ?'
        params.append(category)
    
    if network_id:
        query += ' AND nc.network_id = ?'
        params.append(network_id)
    
    query += ' ORDER BY nc.card_category, nc.id'
    
    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()
    return results

def get_card_categories():
    """Get all available card categories"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM card_categories_ref WHERE is_active = 1 ORDER BY display_order')
    categories = cursor.fetchall()
    conn.close()
    return categories

def get_cards_stats_by_category(supplier_id):
    """Get card statistics grouped by category"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT 
            nc.card_category,
            ccr.category_name,
            COUNT(*) as total_cards,
            SUM(CASE WHEN nc.is_sold = 0 THEN 1 ELSE 0 END) as available_cards,
            SUM(CASE WHEN nc.is_sold = 1 THEN 1 ELSE 0 END) as sold_cards,
            SUM(CASE WHEN nc.is_sold = 0 THEN nc.card_value ELSE 0 END) as available_value,
            SUM(CASE WHEN nc.is_sold = 1 THEN nc.card_value ELSE 0 END) as sold_value
        FROM network_cards nc
        LEFT JOIN card_categories_ref ccr ON nc.card_category = ccr.category_value
        WHERE nc.supplier_id = ?
        GROUP BY nc.card_category, ccr.category_name
        ORDER BY nc.card_category
    ''', (supplier_id,))
    
    stats = cursor.fetchall()
    conn.close()
    return stats

def process_referral_commission(buyer_user_id: int, purchase_amount: float, transaction_id: str):
    """معالجة عمولة الإحالة عند الشراء"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن الشخص الذي أحال هذا المشتري
        cursor.execute('SELECT referred_by FROM users WHERE id = ?', (buyer_user_id,))
        result = cursor.fetchone()
        
        if not result or not result[0]:
            conn.close()
            return False  # لا يوجد محيل
            
        referrer_id = result[0]
        
        # حساب العمولة (5%)
        commission_rate = 0.05
        commission_amount = purchase_amount * commission_rate
        
        # إنشاء سجل العمولة
        import uuid
        commission_id = str(uuid.uuid4())
        
        cursor.execute('''
            INSERT INTO referral_commissions 
            (id, referrer_id, referred_user_id, transaction_id, purchase_amount, 
             commission_amount, commission_rate, paid, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0, datetime('now'))
        ''', (commission_id, referrer_id, buyer_user_id, transaction_id, 
              purchase_amount, commission_amount, commission_rate))
        
        # إضافة العمولة لرصيد المحيل
        cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', 
                      (commission_amount, referrer_id))
        
        # إنشاء معاملة العمولة
        commission_transaction_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (commission_transaction_id, None, referrer_id, commission_amount, 
              'commission', f'عمولة إحالة 5% من شراء بقيمة {purchase_amount:.2f} ريال'))
        
        # تحديث حالة الدفع
        cursor.execute('UPDATE referral_commissions SET paid = 1, paid_at = datetime("now") WHERE id = ?', 
                      (commission_id,))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Referral commission {commission_amount:.2f} paid to user {referrer_id} for purchase {transaction_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing referral commission: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def get_referral_stats(user_id: int):
    """الحصول على إحصائيات الإحالات والعمولات"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # عدد الإحالات
        cursor.execute('SELECT COUNT(*) FROM users WHERE referred_by = ?', (user_id,))
        result = cursor.fetchone()
        total_referrals = result[0] if result else 0
        
        # إجمالي العمولات المكتسبة
        cursor.execute('''
            SELECT 
                COUNT(*) as commission_count,
                COALESCE(SUM(commission_amount), 0) as total_commissions,
                COALESCE(SUM(purchase_amount), 0) as total_referred_purchases
            FROM referral_commissions 
            WHERE referrer_id = ? AND paid = 1
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            commission_count, total_commissions, total_referred_purchases = result
        else:
            commission_count, total_commissions, total_referred_purchases = 0, 0, 0
        
        # العمولات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_commissions,
                COALESCE(SUM(commission_amount), 0) as monthly_commission_amount
            FROM referral_commissions 
            WHERE referrer_id = ? AND paid = 1 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            monthly_commissions, monthly_commission_amount = result
        else:
            monthly_commissions, monthly_commission_amount = 0, 0
        
        conn.close()
        
        return {
            'total_referrals': total_referrals,
            'commission_count': commission_count,
            'total_commissions': total_commissions,
            'total_referred_purchases': total_referred_purchases,
            'monthly_commissions': monthly_commissions,
            'monthly_commission_amount': monthly_commission_amount
        }
        
    except Exception as e:
        logger.error(f"Error getting referral stats: {e}")
        return {
            'total_referrals': 0,
            'commission_count': 0,
            'total_commissions': 0,
            'total_referred_purchases': 0,
            'monthly_commissions': 0,
            'monthly_commission_amount': 0
        }

def generate_supplier_share_link(network_id: str, bot_username: str = "YemenNetBot"):
    """إنشاء رابط مشاركة للمزود لفتح شبكته مباشرة"""
    # إنشاء deep link للشبكة
    deep_link = f"https://t.me/{bot_username}?start=network_{network_id}"
    return deep_link

def get_network_share_info(network_id: str, supplier_id: int):
    """الحصول على معلومات الشبكة للمشاركة"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.name, n.provider, n.location, n.city, 
                   COUNT(nc.id) as total_cards,
                   COUNT(CASE WHEN nc.is_sold = 0 THEN 1 END) as available_cards,
                   MIN(nc.card_value) as min_price,
                   MAX(nc.card_value) as max_price
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id
            WHERE n.id = ? AND n.supplier_id = ?
            GROUP BY n.id
        ''', (network_id, supplier_id))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'name': result[0],
                'provider': result[1], 
                'location': result[2],
                'city': result[3],
                'total_cards': result[4] or 0,
                'available_cards': result[5] or 0,
                'min_price': result[6] or 0,
                'max_price': result[7] or 0
            }
        return None
        
    except Exception as e:
        logger.error(f"Error getting network share info: {e}")
        return None