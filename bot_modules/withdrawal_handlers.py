#!/usr/bin/env python3
"""
Withdrawal Handlers Module
معالجات طلبات السحب
"""

import logging
import uuid
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import (
    get_user, get_or_create_supplier_code, get_provider_withdrawable_amount,
    can_request_withdrawal, create_withdrawal_request
)
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages

logger = logging.getLogger(__name__)

async def request_withdrawal_handler(update: Update, context: CallbackContext):
    """معالج طلب سحب الأرباح للمزود"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} غير مخول لك الوصول لهذه الميزة")
            return
        
        # الحصول على المبلغ القابل للسحب
        withdrawable_info = get_provider_withdrawable_amount(user['id'])
        can_withdraw = can_request_withdrawal()
        
        # التحقق من وجود طلب معلق
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM withdrawals 
            WHERE provider_id = ? AND status = 'Pending'
        ''', (user['id'],))
        result = cursor.fetchone()
        pending_requests = result[0] if result else 0
        conn.close()
        
        withdrawal_text = f"""
💰 **طلب سحب الأرباح** 💰

👤 **{user['full_name']}**
🆔 **معرف المزود:** `{get_or_create_supplier_code(user['id'])}`

📊 **ملخص الأرباح:**
💰 إجمالي الأرباح: **{withdrawable_info['total_earnings']:,.2f}** ريال
📤 تم سحبه/معلق: **{withdrawable_info['withdrawn_amount']:,.2f}** ريال
✅ المتاح للسحب: **{withdrawable_info['available_amount']:,.2f}** ريال

📅 **شروط السحب:**
• يمكن طلب السحب فقط يوم الجمعة
• الحد الأدنى للسحب: 100 ريال
• يتم التحويل يدوياً من الإدارة
• مدة المعالجة: 1-3 أيام عمل

🕐 **حالة اليوم:** {'✅ يمكن طلب السحب (يوم الجمعة)' if can_withdraw else '❌ لا يمكن طلب السحب (ليس يوم الجمعة)'}
"""
        
        if pending_requests > 0:
            withdrawal_text += f"\n⏳ **لديك {pending_requests} طلب معلق بالفعل**"
        
        keyboard = []
        
        if can_withdraw and withdrawable_info['available_amount'] >= 100 and pending_requests == 0:
            keyboard.append([InlineKeyboardButton('💰 تقديم طلب سحب', callback_data='submit_withdrawal_request')])
        
        keyboard.extend([
            [InlineKeyboardButton('📋 عرض طلبات السحب', callback_data='view_my_withdrawals')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(withdrawal_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in request withdrawal handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض معلومات السحب")

async def submit_withdrawal_request_handler(update: Update, context: CallbackContext):
    """معالج تقديم طلب السحب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} غير مخول لك الوصول لهذه الميزة")
            return
        
        # بدء عملية جمع بيانات السحب
        context.user_data['withdrawal_step'] = 'name'
        
        submit_text = f"""
📝 **تقديم طلب سحب** 📝

👤 **{user['full_name']}**

📋 **المطلوب إدخال البيانات التالية:**

1️⃣ **اسم المستفيد** (كما هو في الحساب البنكي)
2️⃣ **رقم الحساب أو بيانات التحويل**
3️⃣ **طريقة التحويل** (القطيبي، الكريمي، شبكة صرافة)

💡 **يرجى كتابة اسم المستفيد أولاً:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء الطلب', callback_data='request_withdrawal')]
        ]
        
        await query.edit_message_text(submit_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in submit withdrawal request handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تقديم الطلب")

async def view_my_withdrawals_handler(update: Update, context: CallbackContext):
    """معالج عرض طلبات السحب الخاصة بالمزود"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} غير مخول لك الوصول لهذه الميزة")
            return
        
        # الحصول على طلبات السحب
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT withdrawal_id, amount, method, status, requested_at, confirmed_at
            FROM withdrawals 
            WHERE provider_id = ?
            ORDER BY requested_at DESC
            LIMIT 10
        ''', (user['id'],))
        
        withdrawals = cursor.fetchall()
        conn.close()
        
        withdrawals_text = f"""
📋 **طلبات السحب** 📋

👤 **{user['full_name']}**

📊 **آخر الطلبات:**
"""
        
        if withdrawals:
            status_icons = {
                'Pending': '⏳',
                'Approved': '✅', 
                'Rejected': '❌'
            }
            
            for withdrawal in withdrawals:
                w_id, amount, method, status, requested_at, confirmed_at = withdrawal
                status_icon = status_icons.get(status, '❓')
                date_str = requested_at[:10] if requested_at else 'غير محدد'
                
                withdrawals_text += f"""
{status_icon} **{amount:,.2f} ريال**
📅 تاريخ الطلب: {date_str}
💳 طريقة التحويل: {method}
📊 الحالة: {status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            withdrawals_text += """
❌ **لا توجد طلبات سحب**

💡 يمكنك تقديم طلب سحب يوم الجمعة عندما يكون لديك أرباح متاحة.
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 طلب سحب جديد', callback_data='request_withdrawal')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(withdrawals_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view my withdrawals handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض طلبات السحب")

async def process_withdrawal_step(update: Update, context: CallbackContext, message_text: str):
    """معالجة خطوات طلب السحب"""
    try:
        user = get_user(update.effective_user.id)
        step = context.user_data.get('withdrawal_step')
        
        if step == 'name':
            # حفظ اسم المستفيد
            context.user_data['withdrawal_name'] = message_text.strip()
            context.user_data['withdrawal_step'] = 'account'
            
            await update.message.reply_text(f"""
💳 **تم حفظ الاسم:** {message_text}

2️⃣ **الآن يرجى كتابة رقم الحساب أو بيانات التحويل:**

💡 **أمثلة:**
• رقم حساب القطيبي: 1234567890
• رقم محفظة الكريمي: 777123456
• اسم الصرافة ورقم الحساب: صرافة الأمل - 987654321
""", reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('❌ إلغاء الطلب', callback_data='request_withdrawal')]
            ]))
            
        elif step == 'account':
            # حفظ رقم الحساب
            context.user_data['withdrawal_account'] = message_text.strip()
            context.user_data['withdrawal_step'] = 'method'
            
            method_text = f"""
🏦 **تم حفظ بيانات الحساب:** {message_text}

3️⃣ **اختر طريقة التحويل:**
"""
            
            keyboard = [
                [InlineKeyboardButton('🏦 القطيبي', callback_data='withdrawal_method_القطيبي')],
                [InlineKeyboardButton('💳 الكريمي', callback_data='withdrawal_method_الكريمي')],
                [InlineKeyboardButton('🏪 شبكة صرافة', callback_data='withdrawal_method_شبكة صرافة')],
                [InlineKeyboardButton('❌ إلغاء الطلب', callback_data='request_withdrawal')]
            ]
            
            await update.message.reply_text(method_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in process withdrawal step: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة البيانات")

async def confirm_withdrawal_request_handler(update: Update, context: CallbackContext, method: str):
    """تأكيد طلب السحب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} غير مخول لك الوصول لهذه الميزة")
            return
        
        # التحقق من البيانات المطلوبة
        withdrawal_name = context.user_data.get('withdrawal_name')
        withdrawal_account = context.user_data.get('withdrawal_account')
        
        if not withdrawal_name or not withdrawal_account:
            await query.edit_message_text(f"{EMOJIS['error']} بيانات الطلب غير مكتملة. يرجى البدء من جديد.")
            return
        
        # الحصول على المبلغ المتاح
        withdrawable_info = get_provider_withdrawable_amount(user['id'])
        amount = withdrawable_info['available_amount']
        
        if amount < 100:
            await query.edit_message_text(f"{EMOJIS['error']} المبلغ المتاح ({amount:.2f} ريال) أقل من الحد الأدنى (100 ريال)")
            return
        
        # إنشاء طلب السحب
        result = create_withdrawal_request(user['id'], withdrawal_name, withdrawal_account, method, amount)
        
        if result['success']:
            # مسح بيانات الطلب
            context.user_data.clear()
            
            success_text = f"""
✅ **تم تقديم طلب السحب بنجاح!** ✅

👤 **المستفيد:** {withdrawal_name}
💳 **بيانات الحساب:** {withdrawal_account}
🏦 **طريقة التحويل:** {method}
💰 **المبلغ:** {amount:,.2f} ريال

📋 **معرف الطلب:** `{result['withdrawal_id'][:8]}...`

⏳ **حالة الطلب:** معلق - في انتظار موافقة الإدارة

📱 **ما يحدث الآن:**
• تم إرسال إشعار للمشرف الأعلى
• سيتم مراجعة الطلب خلال 1-3 أيام عمل
• ستحصل على إشعار عند الموافقة أو الرفض
• يمكنك متابعة حالة الطلب من "عرض طلبات السحب"

💡 **ملاحظة:** التحويل يتم يدوياً من الإدارة بعد الموافقة
"""
            
            keyboard = [
                [InlineKeyboardButton('📋 عرض طلبات السحب', callback_data='view_my_withdrawals')],
                [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        else:
            await query.edit_message_text(f"{EMOJIS['error']} {result['error']}")
            
    except Exception as e:
        logger.error(f"Error in confirm withdrawal request: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد الطلب")

async def approve_withdrawal_handler(update: Update, context: CallbackContext, withdrawal_id: str):
    """موافقة المشرف على طلب السحب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # تحديث حالة الطلب
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE withdrawals 
            SET status = 'Approved', confirmed_at = datetime('now'), confirmed_by = ?
            WHERE withdrawal_id = ?
        ''', (user['id'], withdrawal_id))
        
        # الحصول على تفاصيل الطلب للإشعار
        cursor.execute('''
            SELECT w.provider_id, w.provider_name, w.amount, u.full_name
            FROM withdrawals w
            JOIN users u ON w.provider_id = u.id
            WHERE w.withdrawal_id = ?
        ''', (withdrawal_id,))
        
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        if result:
            provider_id, provider_name, amount, provider_full_name = result
            
            success_text = f"""
✅ **تمت الموافقة على طلب السحب** ✅

👤 **المزود:** {provider_full_name} ({provider_name})
💰 **المبلغ:** {amount:,.2f} ريال
🆔 **معرف الطلب:** `{withdrawal_id[:8]}...`
📅 **تاريخ الموافقة:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 **تم إرسال إشعار للمزود بالموافقة**
"""
        else:
            success_text = "✅ تمت الموافقة على الطلب بنجاح"
        
        keyboard = [
            [InlineKeyboardButton('💰 طلبات السحب', callback_data='admin_withdrawals')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in approve withdrawal: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في الموافقة")

async def reject_withdrawal_handler(update: Update, context: CallbackContext, withdrawal_id: str):
    """رفض المشرف لطلب السحب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
            return
        
        # تحديث حالة الطلب
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE withdrawals 
            SET status = 'Rejected', confirmed_at = datetime('now'), confirmed_by = ?, 
                rejection_reason = 'تم الرفض من قبل المشرف الأعلى'
            WHERE withdrawal_id = ?
        ''', (user['id'], withdrawal_id))
        
        # الحصول على تفاصيل الطلب
        cursor.execute('''
            SELECT w.provider_name, w.amount, u.full_name
            FROM withdrawals w
            JOIN users u ON w.provider_id = u.id
            WHERE w.withdrawal_id = ?
        ''', (withdrawal_id,))
        
        result = cursor.fetchone()
        
        conn.commit()
        conn.close()
        
        if result:
            provider_name, amount, provider_full_name = result
            
            reject_text = f"""
❌ **تم رفض طلب السحب** ❌

👤 **المزود:** {provider_full_name} ({provider_name})
💰 **المبلغ:** {amount:,.2f} ريال
🆔 **معرف الطلب:** `{withdrawal_id[:8]}...`
📅 **تاريخ الرفض:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

💡 **تم إرسال إشعار للمزود بالرفض**
"""
        else:
            reject_text = "❌ تم رفض الطلب"
        
        keyboard = [
            [InlineKeyboardButton('💰 طلبات السحب', callback_data='admin_withdrawals')],
            [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(reject_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in reject withdrawal: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في الرفض")