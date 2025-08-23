#!/usr/bin/env python3
"""
نظام الصلاحيات المتقدم للبوت
Advanced Permissions System
"""

import logging
from functools import wraps
from typing import List, Union
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

# تعريف الأدوار والصلاحيات
ROLES = {
    'super_admin': {
        'name': 'مشرف أعلى',
        'permissions': ['*'],  # جميع الصلاحيات
        'level': 100
    },
    'admin': {
        'name': 'مشرف',
        'permissions': [
            'users:read', 'users:edit', 'users:ban',
            'cards:read', 'cards:create', 'cards:edit',
            'networks:read', 'networks:edit',
            'transactions:read', 'transactions:create',
            'reports:read', 'reports:financial',
            'coupons:read', 'coupons:create'
        ],
        'level': 80
    },
    'supplier': {
        'name': 'مزود',
        'permissions': [
            'networks:create', 'networks:edit_own',
            'cards:create_own', 'cards:read_own',
            'reports:own', 'transactions:read_own',
            'categories:create_own'
        ],
        'level': 60
    },
    'agent': {
        'name': 'وكيل',
        'permissions': [
            'sales:create', 'customers:read',
            'commissions:read_own', 'reports:own',
            'transactions:read_own'
        ],
        'level': 40
    },
    'user': {
        'name': 'عميل',
        'permissions': [
            'cards:buy', 'balance:transfer', 'balance:view_own',
            'transactions:read_own', 'profile:edit_own',
            'coupons:redeem'
        ],
        'level': 20
    }
}

def get_user_role_info(user_id: int) -> dict:
    """الحصول على معلومات دور المستخدم"""
    try:
        from bot_modules.database import get_user
        user = get_user(user_id)
        
        if not user:
            return {'role': 'guest', 'level': 0, 'permissions': []}
        
        role = user.get('role', 'user')
        role_info = ROLES.get(role, ROLES['user'])
        
        return {
            'role': role,
            'name': role_info['name'],
            'level': role_info['level'],
            'permissions': role_info['permissions']
        }
        
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
        return {'role': 'guest', 'level': 0, 'permissions': []}

def has_permission(user_id: int, permission: str) -> bool:
    """التحقق من صلاحية المستخدم"""
    try:
        role_info = get_user_role_info(user_id)
        permissions = role_info['permissions']
        
        # المشرف الأعلى له جميع الصلاحيات
        if '*' in permissions:
            return True
        
        # التحقق من الصلاحية المحددة
        if permission in permissions:
            return True
        
        # التحقق من الصلاحيات العامة (مثل users:* يشمل users:read)
        permission_parts = permission.split(':')
        if len(permission_parts) == 2:
            general_permission = f"{permission_parts[0]}:*"
            if general_permission in permissions:
                return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error checking permission: {e}")
        return False

def require_permission(permission: str):
    """ديكوريتر للتحقق من الصلاحيات"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext):
            try:
                # تحديد معرف المستخدم
                if hasattr(update, 'callback_query') and update.callback_query:
                    user_id = update.callback_query.from_user.id
                    is_callback = True
                else:
                    user_id = update.effective_user.id
                    is_callback = False
                
                # التحقق من الصلاحية
                if not has_permission(user_id, permission):
                    role_info = get_user_role_info(user_id)
                    
                    error_text = f"""
❌ **صلاحية مرفوضة** ❌

🚫 **لا تملك صلاحية:** {permission}
👤 **دورك الحالي:** {role_info['name']}
🔒 **المستوى المطلوب:** أعلى من {role_info['level']}

💡 **للحصول على صلاحيات أكبر:**
• تواصل مع الإدارة
• اطلب ترقية الحساب
• راجع شروط الترقية

📞 **التواصل مع الدعم:**
@YemenNetSupport
"""
                    
                    keyboard = [
                        [InlineKeyboardButton('📞 التواصل مع الدعم', url='https://t.me/YemenNetSupport')],
                        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                    ]
                    
                    if is_callback:
                        await update.callback_query.edit_message_text(
                            error_text, 
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            error_text, 
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    
                    return ConversationHandler.END
                
                # تنفيذ الدالة إذا كانت الصلاحية متاحة
                return await func(update, context)
                
            except Exception as e:
                logger.error(f"Error in permission decorator: {e}")
                
                error_text = f"{EMOJIS.get('error', '❌')} حدث خطأ في التحقق من الصلاحيات."
                
                if hasattr(update, 'callback_query') and update.callback_query:
                    await update.callback_query.edit_message_text(error_text)
                else:
                    await update.message.reply_text(error_text)
                
                return ConversationHandler.END
        
        return wrapper
    return decorator

def require_role(required_role: str):
    """ديكوريتر للتحقق من الدور"""
    def decorator(func):
        @wraps(func)
        async def wrapper(update: Update, context: CallbackContext):
            try:
                # تحديد معرف المستخدم
                if hasattr(update, 'callback_query') and update.callback_query:
                    user_id = update.callback_query.from_user.id
                    is_callback = True
                else:
                    user_id = update.effective_user.id
                    is_callback = False
                
                role_info = get_user_role_info(user_id)
                user_role = role_info['role']
                required_level = ROLES.get(required_role, {}).get('level', 100)
                user_level = role_info['level']
                
                # التحقق من المستوى
                if user_level < required_level:
                    error_text = f"""
❌ **دور غير كافٍ** ❌

🚫 **المطلوب:** {ROLES.get(required_role, {}).get('name', required_role)}
👤 **دورك:** {role_info['name']}
📊 **مستواك:** {user_level} (المطلوب: {required_level})

💡 **للوصول لهذه الميزة:**
• يجب أن تكون {ROLES.get(required_role, {}).get('name', required_role)}
• تواصل مع الإدارة للترقية
"""
                    
                    keyboard = [
                        [InlineKeyboardButton('📞 طلب ترقية', url='https://t.me/YemenNetSupport')],
                        [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                    ]
                    
                    if is_callback:
                        await update.callback_query.edit_message_text(
                            error_text, 
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    else:
                        await update.message.reply_text(
                            error_text, 
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode='Markdown'
                        )
                    
                    return ConversationHandler.END
                
                # تنفيذ الدالة إذا كان الدور مناسباً
                return await func(update, context)
                
            except Exception as e:
                logger.error(f"Error in role decorator: {e}")
                return ConversationHandler.END
        
        return wrapper
    return decorator

def log_user_action(user_id: int, action: str, details: dict = None):
    """تسجيل إجراءات المستخدم للتدقيق"""
    try:
        from bot_modules.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تسجيل الإجراء
        cursor.execute('''
            INSERT INTO accounting_audit_trail
            (action_type, table_name, user_id, user_role, new_values, description, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            action, 'user_actions', user_id, 
            get_user_role_info(user_id)['role'],
            str(details) if details else None,
            f"إجراء المستخدم: {action}"
        ))
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error logging user action: {e}")

# أمثلة على الاستخدام
"""
# في المعالجات:

@require_role('super_admin')
async def super_admin_panel(update, context):
    # كود لوحة المشرف الأعلى
    pass

@require_permission('users:edit')
async def edit_user_balance(update, context):
    # كود تعديل رصيد المستخدم
    pass

@require_permission('networks:create')
async def add_network(update, context):
    # كود إضافة شبكة
    pass
"""