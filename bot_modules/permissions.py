#!/usr/bin/env python3
"""
Advanced Permissions Management System for Yemen Net Bot
نظام إدارة الصلاحيات المتقدم لبوت اليمن نت
"""

import logging
from datetime import datetime
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user
from bot_modules.enhanced_error_messages import perm_error, db_error

logger = logging.getLogger(__name__)

# الصلاحيات الأساسية الخمس كما طلبها المستخدم
AVAILABLE_PERMISSIONS = {
    'add_offers': {
        'name_ar': 'إضافة عروض',
        'description': 'القدرة على إضافة وإدارة العروض والخصومات',
        'category': 'content'
    },
    'activate_providers': {
        'name_ar': 'تفعيل مزودين',
        'description': 'تفعيل وإلغاء تفعيل حسابات المزودين',
        'category': 'users'
    },
    'accounting_access': {
        'name_ar': 'الوصول للنظام المحاسبي',
        'description': 'الوصول للتقارير المالية والمحاسبية',
        'category': 'finance'
    },
    'send_message': {
        'name_ar': 'إرسال رسالة في البوت',
        'description': 'إرسال رسائل جماعية ومراسلة المستخدمين',
        'category': 'communication'
    },
    'manage_clients': {
        'name_ar': 'إدارة العملاء',
        'description': 'إدارة حسابات العملاء وعرض تفاصيلهم',
        'category': 'users'
    }
}

def has_permission(admin_id: int, permission: str) -> bool:
    """
    فحص ما إذا كان المشرف يملك صلاحية معينة
    Check if admin has a specific permission
    
    Args:
        admin_id (int): معرف تلجرام للمشرف
        permission (str): اسم الصلاحية
    
    Returns:
        bool: True إذا كان يملك الصلاحية، False إذا لم يملكها
    """
    try:
        # التحقق من أن المستخدم مشرف أولاً (استخدام معرف تلجرام)
        user = get_user(admin_id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            logger.warning(f"Permission check failed: User telegram_id {admin_id} is not an admin, role: {user['role'] if user else 'User not found'}")
            return False
        
        # المشرف الأعلى يملك جميع الصلاحيات
        if user['role'] == 'super_admin':
            logger.info(f"Super admin telegram_id {admin_id} (db_id: {user['id']}) granted permission '{permission}' automatically")
            return True
        
        # فحص الصلاحية من قاعدة البيانات (استخدام معرف قاعدة البيانات الداخلي)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT permission_value 
            FROM admin_permissions 
            WHERE admin_id = ? AND permission_name = ?
        ''', (user['id'], permission))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            has_perm = bool(result['permission_value'])
            logger.info(f"Permission check for admin {admin_id}, permission '{permission}': {has_perm}")
            return has_perm
        else:
            # إذا لم تجد الصلاحية، قم بإنشائها بقيمة افتراضية
            logger.info(f"Permission '{permission}' not found for admin telegram_id {admin_id} (db_id: {user['id']}), creating with default value")
            return create_default_permission(user['id'], permission)
            
    except Exception as e:
        logger.error(f"Error checking permission '{permission}' for admin {admin_id}: {e}")
        return False

def create_default_permission(admin_db_id: int, permission: str) -> bool:
    """
    إنشاء صلاحية افتراضية للمشرف
    Create default permission for admin
    
    Args:
        admin_db_id (int): معرف قاعدة البيانات الداخلي للمشرف
        permission (str): اسم الصلاحية
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الصلاحيات الافتراضية للمشرف العادي
        default_permissions = {
            'add_offers': True,
            'activate_providers': False,  # مقتصرة على المشرف الأعلى
            'accounting_access': False,   # مقتصرة على المشرف الأعلى
            'send_message': True,
            'manage_clients': True
        }
        
        permission_value = default_permissions.get(permission, False)
        
        cursor.execute('''
            INSERT OR IGNORE INTO admin_permissions 
            (admin_id, permission_name, permission_value, granted_by) 
            VALUES (?, ?, ?, ?)
        ''', (admin_db_id, permission, permission_value, admin_db_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created default permission '{permission}' = {permission_value} for admin db_id {admin_db_id}")
        return permission_value
        
    except Exception as e:
        logger.error(f"Error creating default permission '{permission}' for admin db_id {admin_db_id}: {e}")
        return False

def grant_permission(admin_id: int, permission: str, granted_by: int) -> bool:
    """
    منح صلاحية للمشرف
    Grant permission to admin
    
    Args:
        admin_id (int): معرف المشرف المستهدف
        permission (str): اسم الصلاحية
        granted_by (int): معرف من منح الصلاحية
    
    Returns:
        bool: True إذا نجحت العملية
    """
    try:
        # التحقق من أن من يمنح الصلاحية هو مشرف أعلى
        granter = get_user(granted_by)
        if not granter or granter['role'] != 'super_admin':
            logger.warning(f"Permission grant denied: {granted_by} is not a super admin")
            return False
        
        # التحقق من أن المستهدف مشرف
        target = get_user(admin_id)
        if not target or target['role'] not in ['admin', 'super_admin']:
            logger.warning(f"Permission grant denied: {admin_id} is not an admin")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO admin_permissions 
            (admin_id, permission_name, permission_value, granted_by, updated_at) 
            VALUES (?, ?, ?, ?, ?)
        ''', (admin_id, permission, True, granted_by, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Permission '{permission}' granted to admin {admin_id} by {granted_by}")
        return True
        
    except Exception as e:
        logger.error(f"Error granting permission '{permission}' to admin {admin_id}: {e}")
        return False

def revoke_permission(admin_id: int, permission: str, revoked_by: int) -> bool:
    """
    سحب صلاحية من المشرف
    Revoke permission from admin
    
    Args:
        admin_id (int): معرف المشرف المستهدف
        permission (str): اسم الصلاحية
        revoked_by (int): معرف من سحب الصلاحية
    
    Returns:
        bool: True إذا نجحت العملية
    """
    try:
        # التحقق من أن من يسحب الصلاحية هو مشرف أعلى
        revoker = get_user(revoked_by)
        if not revoker or revoker['role'] != 'super_admin':
            logger.warning(f"Permission revoke denied: {revoked_by} is not a super admin")
            return False
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO admin_permissions 
            (admin_id, permission_name, permission_value, granted_by, updated_at) 
            VALUES (?, ?, ?, ?, ?)
        ''', (admin_id, permission, False, revoked_by, datetime.now()))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Permission '{permission}' revoked from admin {admin_id} by {revoked_by}")
        return True
        
    except Exception as e:
        logger.error(f"Error revoking permission '{permission}' from admin {admin_id}: {e}")
        return False

def get_admin_permissions(admin_id: int) -> dict:
    """
    الحصول على جميع صلاحيات المشرف
    Get all permissions for an admin
    
    Args:
        admin_id (int): معرف المشرف
    
    Returns:
        dict: قاموس بالصلاحيات {permission_name: bool}
    """
    try:
        user = get_user(admin_id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            return {}
        
        # المشرف الأعلى يملك جميع الصلاحيات
        if user['role'] == 'super_admin':
            return {perm: True for perm in AVAILABLE_PERMISSIONS.keys()}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT permission_name, permission_value 
            FROM admin_permissions 
            WHERE admin_id = ?
        ''', (admin_id,))
        
        results = cursor.fetchall()
        conn.close()
        
        permissions = {}
        
        # إضافة الصلاحيات الموجودة
        for row in results:
            permissions[row['permission_name']] = bool(row['permission_value'])
        
        # إضافة الصلاحيات المفقودة بقيم افتراضية
        for perm in AVAILABLE_PERMISSIONS.keys():
            if perm not in permissions:
                permissions[perm] = create_default_permission(admin_id, perm)
        
        return permissions
        
    except Exception as e:
        logger.error(f"Error getting permissions for admin {admin_id}: {e}")
        return {}

def get_all_admins_with_permissions() -> list:
    """
    الحصول على جميع المشرفين مع صلاحياتهم
    Get all admins with their permissions
    
    Returns:
        list: قائمة بالمشرفين وصلاحياتهم
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, telegram_id, full_name, role, is_active 
            FROM users 
            WHERE role IN ('admin', 'super_admin')
            ORDER BY role DESC, full_name ASC
        ''')
        
        admins = cursor.fetchall()
        conn.close()
        
        admin_list = []
        for admin in admins:
            admin_data = {
                'id': admin['id'],
                'telegram_id': admin['telegram_id'],
                'full_name': admin['full_name'],
                'role': admin['role'],
                'is_active': admin['is_active'],
                'permissions': get_admin_permissions(admin['id'])
            }
            admin_list.append(admin_data)
        
        return admin_list
        
    except Exception as e:
        logger.error(f"Error getting all admins with permissions: {e}")
        return []

def check_permission_or_deny(admin_id: int, permission: str, action_name: str = "هذه العملية") -> str:
    """
    فحص الصلاحية وإرجاع رسالة خطأ إذا لم تكن متاحة
    Check permission and return error message if not available
    
    Args:
        admin_id (int): معرف المشرف
        permission (str): اسم الصلاحية
        action_name (str): اسم العملية المطلوبة
    
    Returns:
        str: رسالة خطأ إذا لم تكن الصلاحية متاحة، أو None إذا كانت متاحة
    """
    if has_permission(admin_id, permission):
        return None  # الصلاحية متاحة
    
    # رسالة خطأ مفصلة
    permission_info = AVAILABLE_PERMISSIONS.get(permission, {})
    permission_name_ar = permission_info.get('name_ar', permission)
    
    error_message = f"""
❌ **ليس لديك صلاحية** ❌

🔒 **العملية المطلوبة:** {action_name}
🔑 **الصلاحية المطلوبة:** {permission_name_ar}

💡 **للحصول على هذه الصلاحية:**
تواصل مع المشرف الأعلى ليمنحك صلاحية "{permission_name_ar}"

🔧 **كود الصلاحية:** `{permission}`
"""
    
    return error_message

def initialize_admin_permissions(admin_id: int) -> bool:
    """
    تهيئة صلاحيات افتراضية لمشرف جديد
    Initialize default permissions for new admin
    """
    try:
        for permission in AVAILABLE_PERMISSIONS.keys():
            create_default_permission(admin_id, permission)
        
        logger.info(f"Initialized permissions for new admin {admin_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing permissions for admin {admin_id}: {e}")
        return False

# دالة مساعدة للتحقق من صلاحيات متعددة
def has_any_permission(admin_id: int, permissions: list) -> bool:
    """
    فحص ما إذا كان المشرف يملك أي من الصلاحيات المحددة
    Check if admin has any of the specified permissions
    """
    return any(has_permission(admin_id, perm) for perm in permissions)

def has_all_permissions(admin_id: int, permissions: list) -> bool:
    """
    فحص ما إذا كان المشرف يملك جميع الصلاحيات المحددة
    Check if admin has all of the specified permissions
    """
    return all(has_permission(admin_id, perm) for perm in permissions)

# للاستخدام مع decorators
def require_permission(permission: str):
    """
    ديكوريتر للتحقق من الصلاحية قبل تنفيذ دالة
    Decorator to check permission before executing function
    """
    def decorator(func):
        def wrapper(update, context, *args, **kwargs):
            user_id = update.effective_user.id
            if not has_permission(user_id, permission):
                error_msg = check_permission_or_deny(user_id, permission, func.__name__)
                if hasattr(update, 'callback_query') and update.callback_query:
                    return update.callback_query.edit_message_text(error_msg)
                else:
                    return update.message.reply_text(error_msg)
            return func(update, context, *args, **kwargs)
        return wrapper
    return decorator

def initialize_admin_permissions(admin_db_id: int) -> bool:
    """
    تهيئة صلاحيات افتراضية للمشرف الجديد
    Initialize default permissions for new admin
    
    Args:
        admin_db_id (int): معرف قاعدة البيانات للمشرف
        
    Returns:
        bool: True if successful
    """
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الصلاحيات الافتراضية للمشرف العادي
        default_permissions = {
            'add_offers': True,
            'activate_providers': False,
            'accounting_access': False,
            'send_message': True,
            'manage_clients': True
        }
        
        # إضافة الصلاحيات الافتراضية
        for permission, value in default_permissions.items():
            cursor.execute('''
                INSERT OR REPLACE INTO admin_permissions 
                (admin_id, permission_name, permission_value, granted_by, granted_at, updated_at)
                VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (admin_db_id, permission, value, admin_db_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Initialized permissions for admin DB ID: {admin_db_id}")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing admin permissions: {e}")
        return False