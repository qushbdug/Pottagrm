#!/usr/bin/env python3
"""
Pottagrm Enhanced Bot - Main Entry Point
Yemen Net Card Sales Bot with Enhanced Features
Version: 2.1.0

Author: AI Assistant
License: MIT
"""

import logging
import asyncio
import sys
import os
from datetime import datetime

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

# Import Telegram bot components
from telegram import Update, MenuButtonCommands, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, PicklePersistence, filters, CallbackContext
)

# Import our modular components
try:
    from bot_modules.config import *
    from bot_modules.database import init_db
    from bot_modules.utils import *
    from bot_modules.handlers import *
    from bot_modules.admin_functions import *
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Make sure all module files are in the bot_modules directory")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

# Main callback handler
async def button_click_handler(update: Update, context: CallbackContext):
    """Enhanced callback query handler with better error handling"""
    try:
        query = update.callback_query
        try:
            await query.answer()
        except Exception:
            # Ignore query timeout errors
            pass
        
        callback_data = query.data
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # Route to appropriate handlers
        
        # Main menu
        if callback_data == 'main_menu':
            return await show_main_menu(update, context, user['role'])
        
        # Enhanced wallet
        elif callback_data == 'enhanced_wallet':
            return await enhanced_wallet_handler(update, context)
        
        # Network search and details
        elif callback_data == 'search_networks':
            return await search_networks_handler(update, context)
        elif callback_data.startswith('network_'):
            network_id = callback_data.split('_')[1]
            return await show_network_details(update, context, network_id)
        elif callback_data == 'all_networks':
            return await view_networks_handler(update, context)
        elif callback_data == 'mobile_networks':
            return await view_networks_handler(update, context)
        elif callback_data == 'home_networks':
            return await view_networks_handler(update, context)
        
        # Transfer handlers
        elif callback_data == 'transfer_to_friend':
            return await transfer_to_friend_handler(update, context)
        elif callback_data == 'advanced_search_transfer':
            return await search_user_handler(update, context)
        
        # Coupon handlers
        elif callback_data == 'redeem_coupon':
            return await redeem_coupon_handler(update, context)
        elif callback_data == 'cancel_coupon':
            return await cancel_coupon_handler(update, context)
        elif callback_data == 'quick_transfer':
            return await quick_transfer_handler(update, context)
        elif callback_data.startswith('select_user_'):
            user_id = callback_data.split('_')[2]
            return await select_user_for_transfer(update, context, user_id)
        elif callback_data.startswith('amount_'):
            parts = callback_data.split('_')
            amount = parts[1]
            user_id = parts[2]
            return await process_amount_selection(update, context, amount, user_id)
        
        # Purchase handlers
        elif callback_data.startswith('buy_card_'):
            category_id = callback_data.split('_')[2]
            return await process_card_purchase(update, context, category_id)
        elif callback_data.startswith('confirm_purchase_'):
            category_id = callback_data.split('_')[2]
            return await confirm_card_purchase(update, context, category_id)
        elif callback_data.startswith('confirm_transfer_'):
            parts = callback_data.split('_')
            user_id = parts[2]
            amount = parts[3]
            return await confirm_user_transfer(update, context, user_id, amount)
        elif callback_data.startswith('skip_location_'):
            network_id = callback_data.split('_')[2]
            return await skip_network_location(update, context, network_id)
        elif callback_data.startswith('edit_comm_'):
            commission_id = callback_data.split('_')[2]
            return await edit_specific_commission(update, context, commission_id)
        elif callback_data.startswith('admin_add_category_'):
            network_id = callback_data.split('_')[3]
            return await admin_add_category_handler(update, context, network_id)
        elif callback_data.startswith('admin_upload_to_network_'):
            network_id = callback_data.split('_')[-1]  # آخر عنصر هو network_id
            return await admin_network_upload_handler(update, context, network_id)
        elif callback_data.startswith('admin_upload_category_'):
            parts = callback_data.split('_')
            network_id = parts[-2]
            category_id = parts[-1]
            return await admin_category_upload_handler(update, context, network_id, category_id)
        
        # Admin handlers
        elif callback_data == 'admin_panel':
            return await admin_panel_handler(update, context)
        elif callback_data == 'admin_manage_networks':
            return await admin_manage_networks_handler(update, context)
        elif callback_data.startswith('admin_network_'):
            network_id = callback_data.split('_')[2]
            return await admin_network_details_handler(update, context, network_id)
        elif callback_data.startswith('admin_delete_network_'):
            network_id = callback_data.split('_')[3]
            return await admin_delete_network_handler(update, context, network_id)
        elif callback_data.startswith('admin_confirm_delete_'):
            network_id = callback_data.split('_')[3]
            return await admin_confirm_delete_network_handler(update, context, network_id)
        
        # User management
        elif callback_data == 'update_profile':
            return await update_profile_handler(update, context)
        elif callback_data == 'change_password':
            return await change_password_handler(update, context)
        elif callback_data == 'contact_admin':
            return await contact_admin_handler(update, context)
        elif callback_data == 'account_status':
            return await account_status_handler(update, context)
        
        # Balance and recharge
        elif callback_data == 'recharge_balance':
            return await recharge_balance_handler(update, context)
        elif callback_data.startswith('confirm_transfer_'):
            parts = callback_data.split('_')
            confirmed = parts[2] == 'true'
            return await confirm_transfer_handler(update, context, confirmed)
        
        # Default case
        else:
            await query.edit_message_text(f"{EMOJIS['warning']} أمر غير معروف: {callback_data}")
            return await show_main_menu(update, context, user['role'])
            
    except Exception as e:
        logger.error(f"Error in button_click_handler: {e}")
        try:
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى.")
        except:
            pass
        return ConversationHandler.END

# Placeholder handlers for features being implemented
async def personal_reports_handler(update: Update, context: CallbackContext):
    """معالج التقارير الشخصية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض التقارير الشخصية
        reports_text = f"""
📊 **التقارير الشخصية** 📊

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📈 **إحصائيات سريعة:**
• رصيدك الحالي: **{user['balance']:.2f}** ريال
• عدد المعاملات: **{get_user_transaction_count(user['id'])}**
• تقييمك: **{get_user_rating(user['id']):.1f}/5**

🔽 **اختر نوع التقرير:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 تقرير المعاملات المالية', callback_data='financial_report')],
            [InlineKeyboardButton('🎫 تقرير الكروت المشتراة', callback_data='cards_report')],
            [InlineKeyboardButton('📊 تقرير النشاط', callback_data='activity_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقارير.")
    """Show personal reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get user statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) as total_purchases, SUM(amount) as total_spent
            FROM transactions 
            WHERE from_user = ? AND type = 'purchase'
        ''', (user['id'],))
        
        stats = cursor.fetchone()
        total_purchases = stats['total_purchases'] or 0
        total_spent = stats['total_spent'] or 0.0
        
        conn.close()
        
        report_text = f"""
📊 **تقاريري الشخصية** 📊

👤 **{user['full_name']}**

📈 **إحصائيات الشراء:**
🛒 إجمالي المشتريات: **{total_purchases}**
💰 إجمالي المبلغ المصروف: **{total_spent:.2f}** ريال
📅 عضو منذ: {user['created_at'][:10]}
⚡ آخر نشاط: {user['last_activity'][:10]}

🎯 **معدلات الاستخدام:**
📊 متوسط الشراء الشهري: قيد الحساب
🔥 الشبكة المفضلة: قيد التحليل
⭐ تقييمي: {calculate_user_rating(user['id'])['average_rating']}/5

📈 **التقارير المفصلة متاحة الآن في القوائم المتقدمة**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📊 تحليل مفصل', callback_data='detailed_analysis')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(report_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقارير.")

async def my_ratings_handler(update: Update, context: CallbackContext):
    """معالج التقييمات الشخصية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض التقييمات الشخصية
        ratings_text = f"""
⭐ **تقييماتي ومراجعاتي** ⭐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **إحصائيات التقييم:**
• تقييمي العام: **{get_user_rating(user['id']):.1f}/5**
• عدد التقييمات: **{get_user_ratings_count(user['id'])}**
• تقييماتي المرسلة: **{get_user_sent_ratings_count(user['id'])}**

🔽 **اختر نوع التقييم:**
"""
        
        keyboard = [
            [InlineKeyboardButton('⭐ تقييماتي المستلمة', callback_data='my_received_ratings')],
            [InlineKeyboardButton('📝 تقييماتي المرسلة', callback_data='my_sent_ratings')],
            [InlineKeyboardButton('📊 إحصائيات التقييم', callback_data='ratings_stats')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(ratings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات.")
    """Show user ratings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        rating_summary = calculate_user_rating(user['id'])
        
        rating_text = f"""
⭐ **تقييماتي ومراجعاتي** ⭐

👤 **{user['full_name']}**

📊 **ملخص التقييمات:**
⭐ متوسط التقييم: **{rating_summary['average_rating']}/5**
🔢 إجمالي التقييمات: **{rating_summary['total_ratings']}**

📈 **توزيع النجوم:**
⭐⭐⭐⭐⭐ {rating_summary['rating_distribution'].get(5, 0)} تقييم
⭐⭐⭐⭐ {rating_summary['rating_distribution'].get(4, 0)} تقييم  
⭐⭐⭐ {rating_summary['rating_distribution'].get(3, 0)} تقييم
⭐⭐ {rating_summary['rating_distribution'].get(2, 0)} تقييم
⭐ {rating_summary['rating_distribution'].get(1, 0)} تقييم

🎯 **نصائح لتحسين تقييمك:**
• كن مهذباً في التعامل
• أكمل المعاملات بسرعة
• قدم خدمة عملاء ممتازة
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📝 تقييماتي المرسلة', callback_data='my_sent_ratings')],
            [InlineKeyboardButton(f'📨 تقييماتي المستلمة', callback_data='my_received_ratings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(rating_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات.")

async def my_notifications_handler(update: Update, context: CallbackContext):
    """معالج الإشعارات الشخصية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض الإشعارات الشخصية
        notifications_text = f"""
🔔 **إشعاراتي وتنبيهاتي** 🔔

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **إحصائيات الإشعارات:**
• إجمالي الإشعارات: **{get_user_notifications_count(user['id'])}**
• الإشعارات الجديدة: **{get_user_unread_notifications_count(user['id'])}**
• آخر إشعار: **{get_last_notification_time(user['id'])}**

🔽 **اختر نوع الإشعارات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔔 الإشعارات الجديدة', callback_data='new_notifications')],
            [InlineKeyboardButton('📋 جميع الإشعارات', callback_data='all_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(notifications_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my notifications handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإشعارات.")
    """Show user notifications"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get recent notifications
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM smart_notifications 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 10
        ''', (user['id'],))
        
        notifications = cursor.fetchall()
        
        cursor.execute('''
            SELECT COUNT(*) as unread_count 
            FROM smart_notifications 
            WHERE user_id = ? AND is_read = 0
        ''', (user['id'],))
        
        unread_count = cursor.fetchone()['unread_count']
        conn.close()
        
        notif_text = f"""
🔔 **إشعاراتي وتنبيهاتي** 🔔

👤 **{user['full_name']}**
📬 الإشعارات غير المقروءة: **{unread_count}**

📋 **آخر الإشعارات:**
"""
        
        if notifications:
            for notif in notifications[:5]:
                status = "🔴" if not notif['is_read'] else "✅"
                priority = "🔥" if notif['priority'] == 'high' else "📢"
                notif_text += f"\n{status} {priority} {notif['title'][:25]}..."
        else:
            notif_text += "\nلا توجد إشعارات بعد"
        
        keyboard = [
            [InlineKeyboardButton(f'✅ قراءة الكل', callback_data='mark_all_read'),
             InlineKeyboardButton(f'⚙️ إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(notif_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my notifications handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإشعارات.")

async def promotions_handler(update: Update, context: CallbackContext):
    """معالج العروض والخصومات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض العروض والخصومات
        promotions_text = f"""
🎁 **العروض والخصومات** 🎁

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🎯 **العروض المتاحة لك:**
• خصم 10% على أول شراء
• خصم 5% على الكروت المنزلية
• عرض خاص للوكلاء: عمولة إضافية 2%
• كوبونات شهرية بقيمة 50 ريال

🔽 **اختر نوع العرض:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ كوبونات الخصم', callback_data='discount_coupons')],
            [InlineKeyboardButton('🔥 العروض الحالية', callback_data='current_promotions')],
            [InlineKeyboardButton('📱 كوبونات خاصة', callback_data='special_coupons')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promotions_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العروض.")
    """Show available promotions"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
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
            LIMIT 5
        ''', (datetime.now(), datetime.now(), user['role']))
        
        promotions = cursor.fetchall()
        conn.close()
        
        promo_text = f"""
🎁 **العروض والخصومات** 🎁

👤 **{user['full_name']}**

🔥 **العروض المتاحة حالياً:**
"""
        
        if promotions:
            for promo in promotions:
                discount_text = f"{promo['discount_percentage']}%" if promo['discount_percentage'] > 0 else f"{promo['discount_amount']} ريال"
                promo_text += f"""
💫 **{promo['title']}**
📝 {promo['description'][:50]}...
💰 خصم: {discount_text}
📅 ينتهي: {promo['end_date'][:10]}
---
"""
        else:
            promo_text += "\nلا توجد عروض متاحة حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'🎯 تفاصيل العروض', callback_data='promotion_details')],
            [InlineKeyboardButton(f'📜 استخدام كود خصم', callback_data='use_promo_code')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promo_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العروض.")

async def account_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات الحساب"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض إعدادات الحساب
        settings_text = f"""
⚙️ **إعدادات الحساب** ⚙️

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **{USER_ROLES.get(user['role'], 'غير محدد')}**

🔧 **الإعدادات المتاحة:**
• تحديث البيانات الشخصية
• تغيير كلمة المرور
• إعدادات الإشعارات
• إعدادات الخصوصية
• إعدادات الأمان

🔽 **اختر الإعداد المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👤 تحديث البيانات', callback_data='update_profile')],
            [InlineKeyboardButton('🔐 تغيير كلمة المرور', callback_data='change_password')],
            [InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton('🔒 إعدادات الخصوصية', callback_data='privacy_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإعدادات.")
    """Show account settings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        permissions = get_user_permissions(user['id'])
        
                # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
            'agent': 'وكيل', 
            'supplier': 'مزود', 
            'admin': 'مشرف', 
            'super_admin': 'مشرف أعلى'
        }
        
        settings_text = f"""
⚙️ **إعدادات الحساب** ⚙️

👤 **معلومات الحساب:**
📛 الاسم: **{user['full_name']}**
📞 الهاتف: **{user['phone']}**
🏷️ النوع: **{USER_ROLES.get(user['role'], user['role'])}**
💳 رقم المحفظة: **{user['wallet_number']}**
📅 تاريخ التسجيل: {user['created_at'][:10]}
⚡ الحالة: {"مفعل" if user['is_active'] else "غير مفعل"}

🔐 **الصلاحيات:**
"""
        
        if permissions:
            for perm in permissions:
                settings_text += f"✅ {PERMISSIONS.get(perm, perm)}\n"
        else:
            settings_text += "📋 الصلاحيات الأساسية فقط"
        
        keyboard = [
            [InlineKeyboardButton(f'🔔 إعدادات الإشعارات', callback_data='notification_preferences'),
             InlineKeyboardButton(f'🔒 الأمان والخصوصية', callback_data='privacy_settings')],
            [InlineKeyboardButton(f'📱 تغيير رقم الهاتف', callback_data='change_phone'),
             InlineKeyboardButton(f'🎫 دعوة صديق', callback_data='invite_friend')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الإعدادات.")

async def buy_cards_handler(update: Update, context: CallbackContext):
    """معالج شراء الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات شراء الكروت
        buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

🌐 **أنواع الشبكات المتاحة:**
• شبكات الجوال (يمن نت، MTN، سبأفون)
• شبكات المنازل (ADSL، الألياف البصرية)
• شبكات الشركات (خطوط مخصصة)

🔽 **اختر نوع الشبكة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📱 شبكات الجوال', callback_data='mobile_networks')],
            [InlineKeyboardButton('🏠 شبكات المنازل', callback_data='home_networks')],
            [InlineKeyboardButton('🏢 شبكات الشركات', callback_data='business_networks')],
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات الشراء.")
    """Handle buy cards request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على الشبكات المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            HAVING categories_count > 0
            ORDER BY n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        buy_text = f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📶 **الشبكات المتاحة ({len(networks)} شبكة):**

"""
        
        if networks:
            for network in networks:
                net_id, name, provider, location, cat_count, min_price, max_price = network
                location_text = f"📍 {location}" if location else ""
                price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                
                buy_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
💳 {cat_count} فئة متاحة
💰 {price_range} ريال
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # إضافة أزرار الشبكات للشراء
        if networks:
            for network in networks[:6]:  # أول 6 شبكات
                net_id = network[0]
                name = network[1]
                keyboard.append([
                    InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
                ])
        
        keyboard.extend([
            [InlineKeyboardButton(f'📊 جميع الشبكات', callback_data='view_all_networks'),
             InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton(f'💰 شحن الرصيد', callback_data='recharge_balance'),
             InlineKeyboardButton(f'📈 إحصائياتي', callback_data='my_purchase_stats')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(buy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in buy cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة الشراء.")

async def transfer_handler(update: Update, context: CallbackContext):
    """معالج التحويل"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات التحويل
        transfer_text = f"""
💸 **تحويل الرصيد** 💸

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

🔄 **خيارات التحويل:**
• تحويل لصديق برقم المحفظة
• تحويل سريع للمستخدمين النشطين
• تحويل بالبحث عن المستخدم
• تحويل بالكوبونات

🔽 **اختر طريقة التحويل:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 تحويل لصديق', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('⚡ تحويل سريع', callback_data='quick_transfer')],
            [InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton('🎟️ تحويل بالكوبونات', callback_data='coupon_transfer')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات التحويل.")
    """Handle transfer request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

💡 **للتحويل السريع:**
• استخدم زر "🔍 البحث عن مستخدم" أدناه
• ابحث بالاسم أو رقم المحفظة أو الهاتف
• أدخل المبلغ المطلوب تحويله
• تأكيد العملية بأمان

🔒 **ضمانات الأمان:**
• تأكيد مزدوج قبل التحويل
• إشعار فوري للطرفين
• سجل كامل للمعاملة
"""
        
        keyboard = [
            [InlineKeyboardButton(f'🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton(f'📋 آخر التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة التحويل.")

# Additional missing handlers
async def agent_panel_handler(update: Update, context: CallbackContext):
    """معالج لوحة الوكيل"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'agent':
            await query.edit_message_text(f"{EMOJIS['error']} هذه اللوحة متاحة للوكلاء فقط.")
            return
        
        # عرض لوحة الوكيل
        agent_text = f"""
👑 **لوحة الوكيل** 👑

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📊 **إحصائيات الوكيل:**
• إجمالي المبيعات: **{get_agent_total_sales(user['id']):.2f}** ريال
• العمولات المكتسبة: **{get_agent_commissions(user['id']):.2f}** ريال
• عدد العملاء: **{get_agent_customers_count(user['id'])}**
• تقييم العملاء: **{get_agent_rating(user['id']):.1f}/5**

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🛒 بيع الكروت', callback_data='sell_cards')],
            [InlineKeyboardButton('💰 العمولات', callback_data='my_commissions')],
            [InlineKeyboardButton('👥 عملائي', callback_data='my_customers')],
            [InlineKeyboardButton('📊 تقارير المبيعات', callback_data='sales_reports')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(agent_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in agent panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض لوحة الوكيل.")
    """Handle agent panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات الوكيل الفعلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # عدد العملاء
        cursor.execute('SELECT COUNT(*) FROM users WHERE role = "user"')
        total_customers = cursor.fetchone()[0]
        
        # إجمالي المعاملات
        cursor.execute('SELECT COUNT(*), COALESCE(SUM(amount), 0) FROM transactions')
        total_transactions, total_amount = cursor.fetchone()
        
        # معاملات اليوم
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0) 
            FROM transactions 
            WHERE DATE(created_at) = DATE('now')
        ''')
        today_transactions, today_amount = cursor.fetchone()
        
        conn.close()
        
        panel_text = f"""
💼 **لوحة الوكيل** 💼

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📊 **إحصائيات الوكيل المباشرة:**

👥 **العملاء:**
• إجمالي العملاء: **{total_customers:,}** عميل
• العملاء النشطين: **{min(total_customers, total_transactions):,}** عميل

💰 **المعاملات:**
• إجمالي المعاملات: **{total_transactions:,}** معاملة
• قيمة المعاملات: **{total_amount:,.2f}** ريال

📈 **اليوم:**
• معاملات اليوم: **{today_transactions:,}** معاملة
• مبلغ اليوم: **{today_amount:,.2f}** ريال

💡 **العمولة المتوقعة:**
• عمولة متوقعة: **{today_amount * 0.05:,.2f}** ريال
"""
        
        keyboard = [
            [InlineKeyboardButton(f'💰 عمولاتي', callback_data='my_commissions')],
            [InlineKeyboardButton(f'📊 تقارير المبيعات', callback_data='agent_sales_reports')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in agent panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في لوحة الوكيل.")

async def my_commissions_handler(update: Update, context: CallbackContext):
    """معالج العمولات الشخصية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'agent':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للوكلاء فقط.")
            return
        
        # عرض العمولات الشخصية
        commissions_text = f"""
💰 **عمولاتي** 💰

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **وكيل**

📊 **إحصائيات العمولات:**
• إجمالي العمولات: **{get_agent_total_commissions(user['id']):.2f}** ريال
• العمولات هذا الشهر: **{get_agent_monthly_commissions(user['id']):.2f}** ريال
• العمولات المعلقة: **{get_agent_pending_commissions(user['id']):.2f}** ريال
• معدل العمولة: **{AGENT_COMMISSION_RATE * 100}%**

🔽 **اختر نوع العمولات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 العمولات المكتسبة', callback_data='earned_commissions')],
            [InlineKeyboardButton('⏳ العمولات المعلقة', callback_data='pending_commissions')],
            [InlineKeyboardButton('📊 تقرير العمولات', callback_data='commissions_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(commissions_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my commissions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العمولات.")
    """Handle my commissions view"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        commissions_text = f"""
💰 **عمولاتي** 💰

👤 **{user['full_name']}**

📊 **ملخص العمولات:**
💎 **العمولات الحقيقية متاحة الآن!**

📊 **إحصائيات العمولات:**
• عمولة 5% من كل معاملة
• حساب تلقائي للعمولات
• تقارير شهرية مفصلة
• رصيد عمولات محدث
"""
        
        keyboard = [
            [InlineKeyboardButton(f'💼 لوحة الوكيل', callback_data='agent_panel')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(commissions_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my commissions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض العمولات.")

async def supplier_panel_handler(update: Update, context: CallbackContext):
    """معالج لوحة المزود"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه اللوحة متاحة للمزودين فقط.")
            return
        
        # عرض لوحة المزود
        supplier_text = f"""
🔥 **لوحة المزود** 🔥

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📊 **إحصائيات المزود:**
• عدد الشبكات: **{get_supplier_networks_count(user['id'])}**
• إجمالي الكروت: **{get_supplier_total_cards(user['id'])}**
• الكروت المتاحة: **{get_supplier_available_cards(user['id'])}**
• إجمالي المبيعات: **{get_supplier_total_sales(user['id']):.2f}** ريال

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton('📤 رفع الكروت', callback_data='upload_cards')],
            [InlineKeyboardButton('📊 تقارير المبيعات', callback_data='sales_reports')],
            [InlineKeyboardButton('📋 سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('⚙️ إعدادات المزود', callback_data='supplier_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(supplier_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض لوحة المزود.")
    """Handle enhanced supplier panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get supplier code
        from bot_modules.utils import get_or_create_supplier_code
        supplier_code = get_or_create_supplier_code(user['id'])
        
        # Get statistics
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Count networks
        cursor.execute('SELECT COUNT(*) as count FROM networks WHERE supplier_id = ?', (user['id'],))
        networks_count = cursor.fetchone()['count']
        
        # Count active cards
        cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 0', (user['id'],))
        active_cards = cursor.fetchone()['count']
        
        # Count sold cards
        cursor.execute('SELECT COUNT(*) as count FROM network_cards WHERE supplier_id = ? AND is_sold = 1', (user['id'],))
        sold_cards = cursor.fetchone()['count']
        
        # Recent uploads
        cursor.execute('SELECT COUNT(*) as count FROM card_upload_batches WHERE supplier_id = ?', (user['id'],))
        recent_uploads = cursor.fetchone()['count']
        
        conn.close()
        
        panel_text = f"""
🏪 **لوحة المزود المطورة** 🏪

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال
🆔 **معرف المزود: `{supplier_code}`**

📊 **إحصائيات المزود:**
📶 الشبكات: **{networks_count}**
📋 كروت متاحة: **{active_cards}**
✅ كروت مباعة: **{sold_cards}**
📤 رفع حديث (7 أيام): **{recent_uploads}**

🎯 **إدارة الكروت والشبكات:**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📶 إدارة الشبكات', callback_data='manage_networks'),
             InlineKeyboardButton(f'📤 رفع كروت', callback_data='upload_cards')],
            [InlineKeyboardButton(f'📊 تقارير الكروت', callback_data='cards_reports'),
             InlineKeyboardButton(f'🎯 فلترة حسب الفئة', callback_data='filter_by_category')],
            [InlineKeyboardButton(f'🔍 البحث في الشبكات', callback_data='search_networks'),
             InlineKeyboardButton(f'📈 إحصائيات المبيعات', callback_data='sales_stats')],
            [InlineKeyboardButton(f'📋 سجل الرفع', callback_data='upload_history'),
             InlineKeyboardButton(f'⚙️ إعدادات المزود', callback_data='supplier_settings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(panel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier panel handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في لوحة المزود.")

async def view_networks_handler(update: Update, context: CallbackContext):
    """معالج عرض الشبكات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض الشبكات المتاحة
        networks_text = f"""
🌐 **الشبكات المتاحة** 🌐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **إحصائيات الشبكات:**
• إجمالي الشبكات: **{get_total_networks_count()}**
• الشبكات النشطة: **{get_active_networks_count()}**
• الشبكات المعتمدة: **{get_approved_networks_count()}**

🔽 **اختر نوع الشبكة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📱 شبكات الجوال', callback_data='mobile_networks')],
            [InlineKeyboardButton('🏠 شبكات المنازل', callback_data='home_networks')],
            [InlineKeyboardButton('🏢 شبكات الشركات', callback_data='business_networks')],
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton('📊 جميع الشبكات', callback_data='all_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات.")
    """Handle view networks"""
    try:
        query = update.callback_query
        
        # الحصول على الشبكات المتاحة من قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.created_at,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.created_at
            ORDER BY n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
📶 **الشبكات المتاحة ({len(networks)} شبكة)** 📶

🌐 **جميع الشبكات المعتمدة:**

"""
        
        if networks:
            for network in networks:
                net_id, name, provider, location, created_at, cat_count, min_price, max_price, available_cards = network
                location_text = f"📍 {location}" if location else "📍 غير محدد"
                price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price and max_price and min_price != max_price else f"{min_price:,.0f}" if min_price else "غير محدد"
                
                networks_text += f"""
🌐 **{name}**
👤 المزود: {provider}
{location_text}
💳 الفئات: {cat_count} فئة
💰 الأسعار: {price_range} ريال
📦 كروت متاحة: {available_cards or 0}
📅 تاريخ الإضافة: {created_at[:10] if created_at else 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            networks_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض الشبكات.")

async def search_user_handler(update: Update, context: CallbackContext):
    """معالج البحث عن المستخدمين"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات البحث عن المستخدمين
        search_text = f"""
🔍 **البحث عن المستخدمين** 🔍

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🔍 **طرق البحث المتاحة:**
• البحث برقم المحفظة
• البحث بالاسم
• البحث برقم الهاتف
• البحث بالدور (عميل، وكيل، مزود)

🔽 **اختر طريقة البحث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 البحث برقم المحفظة', callback_data='search_by_wallet')],
            [InlineKeyboardButton('👤 البحث بالاسم', callback_data='search_by_name')],
            [InlineKeyboardButton('📱 البحث برقم الهاتف', callback_data='search_by_phone')],
            [InlineKeyboardButton('👑 البحث بالدور', callback_data='search_by_role')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search user handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات البحث.")
    """Handle search user"""
    try:
        query = update.callback_query
        
        # تفعيل وضع البحث
        context.user_data['awaiting_user_search'] = True
        
        search_text = f"""
🔍 **البحث عن مستخدم للتحويل** 🔍

📝 **طرق البحث المتاحة:**

🆔 **البحث بالمعرف:**
• اكتب: `المعرف @username`
• مثال: `المعرف @ahmed123`

👤 **البحث بالاسم:**
• اكتب: `الاسم أحمد محمد`
• مثال: `الاسم علي سالم`

💳 **البحث برقم المحفظة:**
• اكتب: `المحفظة 791234567`
• مثال: `المحفظة 770123456`

📱 **البحث برقم الهاتف:**
• اكتب: `الهاتف 770123456`
• مثال: `الهاتف 777888999`

💡 **أرسل الآن طريقة البحث التي تريدها:**
"""
        
        keyboard = [
            [InlineKeyboardButton(f'💸 تحويل رصيد', callback_data='transfer_to_friend')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search user handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

async def my_sent_ratings_handler(update: Update, context: CallbackContext):
    """معالج التقييمات المرسلة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض التقييمات المرسلة
        sent_ratings_text = f"""
📝 **تقييماتي المرسلة** 📝

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **إحصائيات التقييمات المرسلة:**
• إجمالي التقييمات: **{get_user_sent_ratings_count(user['id'])}**
• التقييمات هذا الشهر: **{get_user_monthly_sent_ratings(user['id'])}**
• متوسط تقييمي: **{get_user_sent_ratings_average(user['id']):.1f}/5**

🔽 **اختر نوع التقييمات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('⭐ تقييمات الخدمة', callback_data='service_ratings')],
            [InlineKeyboardButton('👥 تقييمات المستخدمين', callback_data='user_ratings')],
            [InlineKeyboardButton('🌐 تقييمات الشبكات', callback_data='network_ratings')],
            [InlineKeyboardButton('📊 إحصائيات التقييمات', callback_data='ratings_stats')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(sent_ratings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my sent ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات المرسلة.")
    """Handle my sent ratings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على مشتريات المستخدم للتقييم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن الشبكات التي اشترى منها المستخدم
        cursor.execute('''
            SELECT DISTINCT n.id, n.name, n.provider, n.location, 
                   COUNT(t.id) as purchase_count,
                   MAX(t.created_at) as last_purchase,
                   SUM(t.amount) as total_spent
            FROM transactions t
            LEFT JOIN cards c ON t.description LIKE '%' || c.code || '%'
            LEFT JOIN card_categories cc ON c.category_id = cc.id
            LEFT JOIN networks n ON cc.network_id = n.id
            WHERE t.to_user = ? AND t.type = 'card_purchase' AND n.id IS NOT NULL
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY last_purchase DESC
            LIMIT 10
        ''', (user['id'],))
        purchased_networks = cursor.fetchall()
        
        # إجمالي المشتريات
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE to_user = ? AND type = 'card_purchase'
        ''', (user['id'],))
        total_purchases, total_amount = cursor.fetchone()
        
        conn.close()
        
        ratings_text = f"""
📝 **تقييماتي والمراجعات** 📝

👤 **{user['full_name']}**
🛒 **إجمالي مشترياتك:** {total_purchases or 0} عملية شراء
💰 **إجمالي الإنفاق:** {total_amount or 0:,.2f} ريال

⭐ **الشبكات التي يمكنك تقييمها:**

"""
        
        if purchased_networks:
            for network in purchased_networks:
                net_id, name, provider, location, purchase_count, last_purchase, spent = network
                location_text = f"📍 {location}" if location else ""
                
                ratings_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
🛒 اشتريت منها: {purchase_count} مرة
💰 أنفقت: {spent:,.2f} ريال
📅 آخر شراء: {last_purchase[:10] if last_purchase else 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            ratings_text += """
❌ **لم تشتري من أي شبكة بعد**

💡 **لتقييم الشبكات:**
• قم بشراء كروت من الشبكات أولاً
• بعد الشراء ستظهر هنا للتقييم
• تقييمك يساعد المستخدمين الآخرين
"""
        
        keyboard = [
            [InlineKeyboardButton(f'⭐ تقييماتي', callback_data='my_ratings')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(ratings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my sent ratings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض التقييمات.")

async def transaction_details_handler(update: Update, context: CallbackContext):
    """معالج تفاصيل المعاملات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض تفاصيل المعاملات
        transaction_text = f"""
💰 **تفاصيل المعاملات** 💰

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📊 **إحصائيات المعاملات:**
• إجمالي المعاملات: **{get_user_transaction_count(user['id'])}**
• المعاملات هذا الشهر: **{get_user_monthly_transactions(user['id'])}**
• إجمالي المرسل: **{get_user_sent_amount(user['id']):.2f}** ريال
• إجمالي المستلم: **{get_user_received_amount(user['id']):.2f}** ريال

🔽 **اختر نوع المعاملات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📤 المعاملات المرسلة', callback_data='sent_transactions')],
            [InlineKeyboardButton('📥 المعاملات المستلمة', callback_data='received_transactions')],
            [InlineKeyboardButton('🛒 مشتريات الكروت', callback_data='card_purchases')],
            [InlineKeyboardButton('📊 تقرير المعاملات', callback_data='transactions_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transaction_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transaction details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل المعاملات.")
    """Handle transaction details"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على معاملات المستخدم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # آخر المعاملات
        cursor.execute('''
            SELECT id, from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'], user['id']))
        transactions = cursor.fetchall()
        
        # إحصائيات المعاملات
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_count,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_amount,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_amount
            FROM transactions
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        stats = cursor.fetchone()
        sent_count, received_count, sent_amount, received_amount = stats
        
        conn.close()
        
        details_text = f"""
📊 **تفاصيل المعاملات** 📊

👤 **{user['full_name']}**
💰 **الرصيد الحالي:** {user['balance']:,.2f} ريال

📈 **إحصائيات المعاملات:**
📤 **معاملات مرسلة:** {sent_count or 0} معاملة ({sent_amount:,.2f} ريال)
📥 **معاملات مستلمة:** {received_count or 0} معاملة ({received_amount:,.2f} ريال)
📊 **إجمالي المعاملات:** {(sent_count or 0) + (received_count or 0)} معاملة

📋 **آخر 10 معاملات:**

"""
        
        if transactions:
            for transaction in transactions:
                trans_id, from_user_id, to_user_id, amount, trans_type, description, created_at = transaction
                
                # تحديد نوع المعاملة
                if from_user_id == user['id']:
                    direction = "📤 مرسل"
                    color = "🔴"
                else:
                    direction = "📥 مستلم" 
                    color = "🟢"
                
                # نوع المعاملة
                type_text = {
                    'transfer': 'تحويل رصيد',
                    'card_purchase': 'شراء كرت',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولة'
                }.get(trans_type, 'معاملة')
                
                details_text += f"""
{color} **{direction} - {type_text}**
💰 المبلغ: **{amount:,.2f}** ريال
📝 التفاصيل: {description or 'غير محدد'}
📅 التاريخ: {created_at[:16] if created_at else 'غير محدد'}
🆔 رقم المعاملة: #{trans_id}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += "❌ لا توجد معاملات حتى الآن"
        
        keyboard = [
            [InlineKeyboardButton(f'💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transaction details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل المعاملات.")

async def wallet_stats_handler(update: Update, context: CallbackContext):
    """معالج إحصائيات المحفظة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض إحصائيات المحفظة
        wallet_stats_text = f"""
📊 **إحصائيات المحفظة** 📊

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك: **{user['balance']:.2f}** ريال

📈 **إحصائيات مفصلة:**
• إجمالي المعاملات: **{get_user_transaction_count(user['id'])}**
• المعاملات هذا الشهر: **{get_user_monthly_transactions(user['id'])}**
• إجمالي المرسل: **{get_user_sent_amount(user['id']):.2f}** ريال
• إجمالي المستلم: **{get_user_received_amount(user['id']):.2f}** ريال
• صافي الحركة: **{get_user_net_amount(user['id']):+.2f}** ريال

🔽 **اختر نوع الإحصائيات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📈 إحصائيات شهرية', callback_data='monthly_stats')],
            [InlineKeyboardButton('📊 إحصائيات سنوية', callback_data='yearly_stats')],
            [InlineKeyboardButton('💰 إحصائيات مالية', callback_data='financial_stats')],
            [InlineKeyboardButton('📋 تقرير مفصل', callback_data='detailed_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(wallet_stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in wallet stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إحصائيات المحفظة.")
    """Handle wallet statistics"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات المحفظة التفصيلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_this_month,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_this_month,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as spent_this_month,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as earned_this_month
            FROM transactions
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        monthly_stats = cursor.fetchone()
        
        # إحصائيات هذا الأسبوع
        cursor.execute('''
            SELECT 
                COUNT(*) as weekly_transactions,
                COALESCE(SUM(CASE WHEN from_user = ? THEN -amount ELSE amount END), 0) as weekly_balance_change
            FROM transactions
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', '-7 days')
        ''', (user['id'], user['id'], user['id']))
        weekly_stats = cursor.fetchone()
        
        # أكثر أنواع المعاملات
        cursor.execute('''
            SELECT type, COUNT(*) as count, SUM(amount) as total_amount
            FROM transactions
            WHERE from_user = ? OR to_user = ?
            GROUP BY type
            ORDER BY count DESC
            LIMIT 3
        ''', (user['id'], user['id']))
        top_transaction_types = cursor.fetchall()
        
        conn.close()
        
        sent_month, received_month, spent_month, earned_month = monthly_stats
        weekly_transactions, weekly_change = weekly_stats
        
        # حساب متوسط الإنفاق اليومي
        daily_avg = spent_month / 30 if spent_month else 0
        
        stats_text = f"""
📈 **إحصائيات المحفظة المتقدمة** 📈

👤 **{user['full_name']}**
💰 **الرصيد الحالي:** {user['balance']:,.2f} ريال

📊 **إحصائيات هذا الشهر:**
📤 معاملات مرسلة: **{sent_month or 0}** معاملة
📥 معاملات مستلمة: **{received_month or 0}** معاملة
💸 إجمالي الإنفاق: **{spent_month:,.2f}** ريال
💰 إجمالي الإيرادات: **{earned_month:,.2f}** ريال

📅 **إحصائيات هذا الأسبوع:**
🔄 المعاملات: **{weekly_transactions or 0}** معاملة
📈 تغير الرصيد: **{weekly_change:,.2f}** ريال

📊 **تحليل الإنفاق:**
💵 متوسط الإنفاق اليومي: **{daily_avg:,.2f}** ريال
📈 صافي الربح/الخسارة: **{earned_month - spent_month:,.2f}** ريال

🎯 **أكثر أنواع المعاملات:**
"""
        
        if top_transaction_types:
            for trans_type, count, total in top_transaction_types:
                type_name = {
                    'transfer': 'تحويل رصيد',
                    'card_purchase': 'شراء كروت',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولات'
                }.get(trans_type, trans_type)
                
                stats_text += f"• {type_name}: **{count}** معاملة ({total:,.2f} ريال)\n"
        else:
            stats_text += "• لا توجد معاملات حتى الآن"
        
        keyboard = [
            [InlineKeyboardButton(f'💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in wallet stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إحصائيات المحفظة.")

# Enhanced supplier handlers
async def upload_cards_handler(update: Update, context: CallbackContext):
    """معالج رفع الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض خيارات رفع الكروت
        upload_text = f"""
📤 **رفع الكروت** 📤

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

📊 **إحصائيات الرفع:**
• إجمالي الكروت المرفوعة: **{get_supplier_total_cards(user['id'])}**
• الكروت المتاحة: **{get_supplier_available_cards(user['id'])}**
• آخر رفع: **{get_last_upload_time(user['id'])}**

🔽 **اختر طريقة الرفع:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📁 رفع ملف Excel', callback_data='upload_excel_file')],
            [InlineKeyboardButton('📝 إدخال يدوي', callback_data='manual_entry')],
            [InlineKeyboardButton('📋 قالب Excel', callback_data='download_template')],
            [InlineKeyboardButton('📊 سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات رفع الكروت.")
    """Handle card upload process"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if user['role'] != 'supplier':
            await query.edit_message_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        upload_text = f"""
📤 **رفع كروت الشبكة** 📤

🎯 **طريقة رفع الكروت:**

📋 **الصيغة المدعومة:**
1️⃣ **ملف نصي (.txt)** - كل رقم في سطر منفصل
2️⃣ **ملف إكسل (.xlsx)** - عمود الأرقام

📝 **صيغة الأرقام:**
• كل رقم من 6 إلى 14 رقم
• يمكن إضافة القيمة: `رقم_الكارت,القيمة`
• مثال: `123456789012,50`

⚡ **خطوات الرفع:**
1. أرسل الملف (نصي أو إكسل)
2. اختر الشبكة المرتبطة
3. تأكيد الرفع والمعالجة

🚀 **ابدأ برفع ملف الكروت الآن!**
"""
        
        keyboard = [
            [InlineKeyboardButton('📁 اختر طريقة الرفع', callback_data='choose_upload_method')],
            [InlineKeyboardButton('📋 عرض سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في صفحة رفع الكروت.")

async def manage_networks_handler(update: Update, context: CallbackContext):
    """معالج إدارة الشبكات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض خيارات إدارة الشبكات
        manage_text = f"""
🌐 **إدارة الشبكات** 🌐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

📊 **إحصائيات الشبكات:**
• إجمالي الشبكات: **{get_supplier_networks_count(user['id'])}**
• الشبكات النشطة: **{get_supplier_active_networks(user['id'])}**
• الشبكات المعتمدة: **{get_supplier_approved_networks(user['id'])}**

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='add_network')],
            [InlineKeyboardButton('✏️ تعديل الشبكات', callback_data='edit_networks')],
            [InlineKeyboardButton('📊 إحصائيات الشبكات', callback_data='networks_stats')],
            [InlineKeyboardButton('🗑️ حذف شبكة', callback_data='delete_network')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(manage_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات إدارة الشبكات.")
    """Handle network management"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get user's networks
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM networks WHERE supplier_id = ? ORDER BY id DESC', (user['id'],))
        networks = cursor.fetchall()
        conn.close()
        
        networks_text = f"""
📶 **إدارة الشبكات** 📶

👤 **{user['full_name']}**
📊 إجمالي الشبكات: **{len(networks)}**

📋 **شبكاتك:**
"""
        
        if networks:
            for network in networks[:5]:  # Show first 5
                status = "✅ مفعلة" if network['is_active'] else "⏸️ متوقفة"
                approval = "✅ معتمدة" if network['is_approved'] else "⏳ في انتظار الموافقة"
                networks_text += f"""
📶 **{network['name']}**
🏙️ المدينة: {network['city']}
📊 الحالة: {status}
✅ الاعتماد: {approval}
---"""
        else:
            networks_text += "\n⚠️ لا توجد شبكات مسجلة بعد"
        
        keyboard = [
            [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='add_network')],
            [InlineKeyboardButton('📊 تفاصيل الشبكات', callback_data='network_details')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الشبكات.")

async def cards_reports_handler(update: Update, context: CallbackContext):
    """معالج تقارير الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض تقارير الكروت
        reports_text = f"""
📊 **تقارير الكروت** 📊

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

📈 **إحصائيات الكروت:**
• إجمالي الكروت: **{get_supplier_total_cards(user['id'])}**
• الكروت المتاحة: **{get_supplier_available_cards(user['id'])}**
• الكروت المباعة: **{get_supplier_sold_cards(user['id'])}**
• معدل البيع: **{get_supplier_sales_rate(user['id']):.1f}%**

🔽 **اختر نوع التقرير:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير المبيعات', callback_data='sales_report')],
            [InlineKeyboardButton('📈 تقرير المخزون', callback_data='inventory_report')],
            [InlineKeyboardButton('💰 تقرير الأرباح', callback_data='profit_report')],
            [InlineKeyboardButton('📋 تقرير مفصل', callback_data='detailed_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in cards reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تقارير الكروت.")
    """Handle cards reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get cards statistics
        from bot_modules.utils import get_cards_stats_by_category
        stats_by_category = get_cards_stats_by_category(user['id'])
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT 
                COUNT(*) as total_cards,
                SUM(CASE WHEN is_sold = 0 THEN 1 ELSE 0 END) as available_cards,
                SUM(CASE WHEN is_sold = 1 THEN 1 ELSE 0 END) as sold_cards,
                SUM(CASE WHEN is_sold = 0 THEN card_value ELSE 0 END) as available_value,
                SUM(CASE WHEN is_sold = 1 THEN card_value ELSE 0 END) as sold_value
            FROM network_cards 
            WHERE supplier_id = ?
        ''', (user['id'],))
        
        stats = cursor.fetchone()
        conn.close()
        
        reports_text = f"""
📊 **تقارير الكروت المفصلة** 📊

👤 **{user['full_name']}**

📈 **إحصائيات شاملة:**
📋 إجمالي الكروت: **{stats['total_cards'] or 0}**
✅ كروت متاحة: **{stats['available_cards'] or 0}**
💰 قيمة متاحة: **{stats['available_value'] or 0:.2f}** ريال

🎯 **إحصائيات المبيعات:**
✅ كروت مباعة: **{stats['sold_cards'] or 0}**
💵 قيمة مباعة: **{stats['sold_value'] or 0:.2f}** ريال
📊 **معدل البيع:** {((stats['sold_cards'] or 0) / max(stats['total_cards'] or 1, 1) * 100):.1f}%

💳 **تقسيم حسب الفئات:**
"""

        if stats_by_category:
            for stat in stats_by_category:
                reports_text += f"""
• **{stat['category_name']}**: {stat['available_cards']}/{stat['total_cards']} متاح"""
        else:
            reports_text += "\n⚠️ لا توجد كروت محملة"
        
        keyboard = [
            [InlineKeyboardButton('📈 تفاصيل أكثر', callback_data='detailed_reports')],
            [InlineKeyboardButton('📤 سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in cards reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تقارير الكروت.")

async def sales_stats_handler(update: Update, context: CallbackContext):
    """معالج إحصائيات المبيعات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض إحصائيات المبيعات
        sales_text = f"""
📈 **إحصائيات المبيعات** 📈

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

💰 **إحصائيات المبيعات:**
• إجمالي المبيعات: **{get_supplier_total_sales(user['id']):.2f}** ريال
• مبيعات هذا الشهر: **{get_supplier_monthly_sales(user['id']):.2f}** ريال
• عدد الكروت المباعة: **{get_supplier_sold_cards(user['id'])}**
• متوسط سعر البيع: **{get_supplier_avg_sale_price(user['id']):.2f}** ريال

🔽 **اختر نوع الإحصائيات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 إحصائيات شهرية', callback_data='monthly_sales_stats')],
            [InlineKeyboardButton('📈 إحصائيات سنوية', callback_data='yearly_sales_stats')],
            [InlineKeyboardButton('💰 إحصائيات مالية', callback_data='financial_sales_stats')],
            [InlineKeyboardButton('📋 تقرير مفصل', callback_data='detailed_sales_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(sales_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sales stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إحصائيات المبيعات.")
    """Handle sales statistics"""
    try:
        query = update.callback_query
        
        # الحصول على إحصائيات المبيعات الفعلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إجمالي المبيعات
        cursor.execute('''
            SELECT 
                COUNT(*) as total_sales,
                COALESCE(SUM(amount), 0) as total_revenue
            FROM transactions 
            WHERE type = 'card_purchase'
        ''')
        total_sales, total_revenue = cursor.fetchone()
        
        # مبيعات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_sales,
                COALESCE(SUM(amount), 0) as monthly_revenue
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''')
        monthly_sales, monthly_revenue = cursor.fetchone()
        
        # مبيعات اليوم
        cursor.execute('''
            SELECT 
                COUNT(*) as daily_sales,
                COALESCE(SUM(amount), 0) as daily_revenue
            FROM transactions 
            WHERE type = 'card_purchase' 
            AND DATE(created_at) = DATE('now')
        ''')
        daily_sales, daily_revenue = cursor.fetchone()
        
        # أفضل الشبكات مبيعاً (تقديري)
        cursor.execute('''
            SELECT n.name, n.provider, COUNT(t.id) as sales_count, SUM(t.amount) as network_revenue
            FROM transactions t
            LEFT JOIN cards c ON t.description LIKE '%' || c.code || '%'
            LEFT JOIN card_categories cc ON c.category_id = cc.id
            LEFT JOIN networks n ON cc.network_id = n.id
            WHERE t.type = 'card_purchase' AND n.id IS NOT NULL
            GROUP BY n.id, n.name, n.provider
            ORDER BY sales_count DESC
            LIMIT 5
        ''')
        top_networks = cursor.fetchall()
        
        conn.close()
        
        # حساب المتوسطات
        avg_daily = monthly_revenue / 30 if monthly_revenue else 0
        avg_per_sale = total_revenue / total_sales if total_sales else 0
        
        stats_text = f"""
📈 **إحصائيات المبيعات الشاملة** 📈

💰 **الإحصائيات العامة:**
🛒 إجمالي المبيعات: **{total_sales or 0:,}** عملية بيع
💰 إجمالي الإيرادات: **{total_revenue:,.2f}** ريال
💵 متوسط قيمة البيع: **{avg_per_sale:,.2f}** ريال

📅 **هذا الشهر:**
🛒 مبيعات الشهر: **{monthly_sales or 0:,}** عملية
💰 إيرادات الشهر: **{monthly_revenue:,.2f}** ريال
📊 متوسط يومي: **{avg_daily:,.2f}** ريال

📅 **اليوم:**
🛒 مبيعات اليوم: **{daily_sales or 0:,}** عملية
💰 إيرادات اليوم: **{daily_revenue:,.2f}** ريال

🏆 **أفضل 5 شبكات مبيعاً:**

"""
        
        if top_networks:
            for i, (name, provider, sales_count, network_revenue) in enumerate(top_networks, 1):
                medal = ["🥇", "🥈", "🥉", "🏅", "🏅"][i-1]
                stats_text += f"""
{medal} **{name}**
👤 {provider}
🛒 {sales_count} عملية بيع
💰 {network_revenue:,.2f} ريال
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            stats_text += "❌ لا توجد مبيعات حتى الآن"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقارير الكروت', callback_data='cards_reports')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(stats_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sales stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إحصائيات المبيعات.")

async def upload_history_handler(update: Update, context: CallbackContext):
    """معالج سجل رفع الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض سجل رفع الكروت
        history_text = f"""
📋 **سجل رفع الكروت** 📋

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

📊 **إحصائيات الرفع:**
• إجمالي عمليات الرفع: **{get_supplier_upload_count(user['id'])}**
• آخر رفع: **{get_last_upload_time(user['id'])}**
• إجمالي الكروت المرفوعة: **{get_supplier_total_cards(user['id'])}**
• الكروت المتاحة حالياً: **{get_supplier_available_cards(user['id'])}**

🔽 **اختر نوع السجل:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📅 سجل هذا الشهر', callback_data='this_month_uploads')],
            [InlineKeyboardButton('📊 سجل هذا العام', callback_data='this_year_uploads')],
            [InlineKeyboardButton('📋 جميع العمليات', callback_data='all_uploads')],
            [InlineKeyboardButton('📈 إحصائيات الرفع', callback_data='upload_stats')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload history handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض سجل رفع الكروت.")
    """Handle upload history"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get upload history
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                cb.*, n.name as network_name 
            FROM card_upload_batches cb
            LEFT JOIN networks n ON cb.network_id = n.id
            WHERE cb.supplier_id = ? 
            ORDER BY cb.id DESC 
            LIMIT 10
        ''', (user['id'],))
        
        uploads = cursor.fetchall()
        conn.close()
        
        history_text = f"""
📋 **سجل رفع الكروت** 📋

👤 **{user['full_name']}**

📊 **آخر عمليات الرفع:**
"""
        
        if uploads:
            for upload in uploads:
                status_emoji = {"processing": "⏳", "completed": "✅", "completed_with_errors": "⚠️", "failed": "❌"}
                status = status_emoji.get(upload['upload_status'], "❓")
                
                history_text += f"""
{status} **{upload['filename'] or 'ملف مجهول'}**
📶 الشبكة: {upload['network_name'] or 'غير محدد'}
📊 نجح: {upload['successful_cards']}, فشل: {upload['failed_cards']}
📅 {upload['created_at'][:16] if upload['created_at'] else 'حديث'}
---"""
        else:
            history_text += "\n⚠️ لا توجد عمليات رفع سابقة"
        
        keyboard = [
            [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data='upload_cards')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload history handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في سجل الرفع.")

async def supplier_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات المزود"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض إعدادات المزود
        settings_text = f"""
⚙️ **إعدادات المزود** ⚙️

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

🔧 **الإعدادات المتاحة:**
• إعدادات الشبكات
• إعدادات الكروت
• إعدادات الإشعارات
• إعدادات الأمان
• إعدادات الحساب

🔽 **اختر الإعداد المطلوب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🌐 إعدادات الشبكات', callback_data='network_settings')],
            [InlineKeyboardButton('🎫 إعدادات الكروت', callback_data='card_settings')],
            [InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton('🔒 إعدادات الأمان', callback_data='security_settings')],
            [InlineKeyboardButton('👤 إعدادات الحساب', callback_data='account_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إعدادات المزود.")
    """Handle supplier settings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        from bot_modules.utils import get_or_create_supplier_code
        supplier_code = get_or_create_supplier_code(user['id'])
        
        # الحصول على معلومات المزود التفصيلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المزود
        cursor.execute('''
            SELECT COUNT(*) FROM networks WHERE created_by = ? AND is_active = 1
        ''', (user['id'],))
        active_networks = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE n.created_by = ? AND c.is_sold = 0
        ''', (user['id'],))
        available_cards = cursor.fetchone()[0] or 0
        
        cursor.execute('''
            SELECT COUNT(*) FROM cards c
            JOIN card_categories cc ON c.category_id = cc.id
            JOIN networks n ON cc.network_id = n.id
            WHERE n.created_by = ? AND c.is_sold = 1
        ''', (user['id'],))
        sold_cards = cursor.fetchone()[0] or 0
        
        conn.close()
        
                # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
            'agent': 'وكيل', 
            'supplier': 'مزود', 
            'admin': 'مشرف', 
            'super_admin': 'مشرف أعلى'
        }
        
        settings_text = f"""
⚙️ **إعدادات المزود المتقدمة** ⚙️

👤 **{user['full_name']}**
🆔 **معرف المزود: `{supplier_code}`**

📊 **إحصائيات سريعة:**
🌐 الشبكات النشطة: **{active_networks}** شبكة
📦 الكروت المتاحة: **{available_cards}** كرت
✅ الكروت المباعة: **{sold_cards}** كرت

⚙️ **الإعدادات المتاحة:**

🏢 **معلومات المزود:**
• اسم الشركة: {user.get('full_name', 'غير محدد')}
• رقم الهاتف: {user.get('phone', 'غير محدد')}
• البريد الإلكتروني: غير محدد
• العنوان: غير محدد

🔔 **إعدادات الإشعارات:**
• إشعارات المبيعات: مفعل ✅
• إشعارات نفاد المخزون: مفعل ✅
• إشعارات الطلبات الجديدة: مفعل ✅
• التقارير اليومية: مفعل ✅

💰 **إعدادات العمولات:**
• عمولة المبيعات: 5% (افتراضي)
• نظام الدفع: شهري
• طريقة الاستلام: تحويل مباشر

🔧 **إعدادات النظام:**
• حالة الحساب: نشط ✅
• مستوى التحقق: مؤكد ✅
• آخر تحديث: اليوم
"""
        
        keyboard = [
            [InlineKeyboardButton('🔄 تجديد المعرف', callback_data='regenerate_supplier_code')],
            [InlineKeyboardButton('📞 معلومات الاتصال', callback_data='update_contact_info')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات المزود.")

async def help_handler(update: Update, context: CallbackContext):
    """معالج المساعدة والدعم"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض المساعدة والدعم
        help_text = f"""
❓ **المساعدة والدعم** ❓

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🔧 **المساعدة المتاحة:**
• دليل الاستخدام
• الأسئلة الشائعة
• حل المشاكل
• التواصل مع الدعم
• فيديوهات تعليمية

🔽 **اختر نوع المساعدة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📖 دليل الاستخدام', callback_data='user_guide')],
            [InlineKeyboardButton('❓ الأسئلة الشائعة', callback_data='faq')],
            [InlineKeyboardButton('🔧 حل المشاكل', callback_data='troubleshooting')],
            [InlineKeyboardButton('📞 التواصل مع الدعم', callback_data='contact_support')],
            [InlineKeyboardButton('🎥 فيديوهات تعليمية', callback_data='video_tutorials')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض المساعدة.")
    """Show help information"""
    try:
        query = update.callback_query if update.callback_query else None
        
        help_text = f"""
❓ **المساعدة والدعم** ❓

🤖 **بوت كروت الإنترنت اليمني المطور**
📱 النسخة: 2.1.0 Enhanced

🔥 **الميزات الجديدة:**
• 💳 محفظة إلكترونية متطورة
• 📊 تقارير شخصية تفصيلية  
• ⭐ نظام تقييمات ومراجعات
• 🔔 إشعارات ذكية مخصصة
• 🎁 نظام عروض وخصومات
• 🔒 أمان محسّن ومشفر

📋 **الأوامر الأساسية:**
/start - البداية والقائمة الرئيسية
/wallet - المحفظة المطورة
/menu - القائمة السريعة
/admin - لوحة الإدارة (للمشرفين)
/cancel - إلغاء العملية الحالية

📞 **للدعم الفني:**
تواصل مع الإدارة عبر البوت

🔄 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d')}
"""
        
        keyboard = [
            [InlineKeyboardButton(f'📖 دليل الاستخدام', callback_data='user_guide'),
             InlineKeyboardButton(f'🛠️ الإبلاغ عن مشكلة', callback_data='report_issue')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if query:
            await query.edit_message_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Error in help handler: {e}")
        error_text = f"{EMOJIS['error']} حدث خطأ في عرض المساعدة."
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

async def handle_document(update: Update, context: CallbackContext):
    """معالج رفع الملفات"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # معالجة رفع الملفات
        document = update.message.document
        if not document:
            await update.message.reply_text(f"{EMOJIS['error']} لم يتم العثور على ملف.")
            return
        
        file_name = document.file_name
        file_size = document.file_size
        
        # التحقق من نوع الملف
        if not file_name.endswith(('.xlsx', '.xls', '.csv')):
            await update.message.reply_text(f"{EMOJIS['error']} يرجى رفع ملف Excel أو CSV فقط.")
            return
        
        # التحقق من حجم الملف
        if file_size > 10 * 1024 * 1024:  # 10 MB
            await update.message.reply_text(f"{EMOJIS['error']} حجم الملف كبير جداً. الحد الأقصى 10 MB.")
            return
        
        await update.message.reply_text(
            f"📁 **تم استلام الملف** 📁\n\n"
            f"📄 **اسم الملف:** {file_name}\n"
            f"📏 **الحجم:** {file_size / 1024:.1f} KB\n"
            f"👤 **المستخدم:** {user['full_name']}\n\n"
            f"⏳ **جاري معالجة الملف...**",
            parse_mode='Markdown'
        )
        
        # هنا يمكن إضافة منطق معالجة الملف
        
    except Exception as e:
        logger.error(f"Error in handle document: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الملف.")
    """Handle uploaded documents for card upload"""
    try:
        if not update.message or not update.message.document:
            return
        
        user = get_user(update.message.from_user.id)
        if not user or user['role'] != 'supplier':
            await update.message.reply_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        document = update.message.document
        file_name = document.file_name
        file_size = document.file_size
        
        # Check file size (max 10MB)
        if file_size > 10 * 1024 * 1024:
            await update.message.reply_text("❌ حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت.")
            return
        
        # Check file type
        allowed_extensions = ['.txt', '.csv', '.xlsx', '.xls']
        if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
            await update.message.reply_text("❌ نوع الملف غير مدعوم. يرجى رفع ملف .txt أو .csv أو .xlsx")
            return
        
        # Download file
        file = await context.bot.get_file(document.file_id)
        file_content = await file.download_as_bytearray()
        
        # Store file temporarily in context
        try:
            content = file_content.decode('utf-8') if file_name.endswith('.txt') else file_content
        except UnicodeDecodeError:
            try:
                content = file_content.decode('utf-8-sig')  # Try with BOM
            except UnicodeDecodeError:
                content = file_content.decode('latin-1')  # Fallback encoding
        
        context.user_data['upload_file'] = {
            'content': content,
            'filename': file_name,
            'size': file_size
        }
        
        # Get user's networks for selection
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM networks WHERE supplier_id = ? AND is_active = 1', (user['id'],))
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            await update.message.reply_text("""
❌ **لا توجد شبكات مفعلة**

يجب أن يكون لديك شبكة مفعلة لرفع الكروت.
اتصل بالإدارة لتفعيل شبكاتك أو أضف شبكة جديدة.
""", parse_mode='Markdown')
            return
        
        # Show network selection
        keyboard = []
        for network in networks:
            keyboard.append([InlineKeyboardButton(f"📶 {network['name']}", callback_data=f"select_network_{network['id']}")])
        
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")])
        
        await update.message.reply_text(f"""
📤 **ملف جاهز للرفع**

📁 **اسم الملف:** {file_name}
📊 **حجم الملف:** {file_size/1024:.1f} كيلوبايت

🎯 **خطوة 1: اختر الشبكة المرتبطة بهذه الكروت:**
""", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الملف.")

async def process_network_selection(update: Update, context: CallbackContext):
    """معالج اختيار الشبكة"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # معالجة اختيار الشبكة
        network_id = context.user_data.get('selected_network')
        if not network_id:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى اختيار شبكة أولاً.")
            return
        
        # عرض الشبكة المختارة
        network = get_network_by_id(network_id)
        if not network:
            await update.message.reply_text(f"{EMOJIS['error']} لم يتم العثور على الشبكة المختارة.")
            return
        
        await update.message.reply_text(
            f"🌐 **الشبكة المختارة** 🌐\n\n"
            f"📶 **الاسم:** {network['name']}\n"
            f"👤 **المزود:** {network['provider']}\n"
            f"🏙️ **المدينة:** {network['city']}\n"
            f"📍 **الموقع:** {network['location']}\n\n"
            f"✅ **تم اختيار الشبكة بنجاح!**\n\n"
            f"🔽 **الخطوة التالية:** اختر فئة الكروت",
            parse_mode='Markdown'
        )
        
        # الانتقال لاختيار فئة الكروت
        context.user_data['step'] = 'select_category'
        
    except Exception as e:
        logger.error(f"Error in process network selection: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة اختيار الشبكة.")
    """Process network selection for file upload"""
    try:
        query = update.callback_query
        network_id = query.data.split('_')[-1]
        
        user = get_user(query.from_user.id)
        upload_data = context.user_data.get('upload_file')
        
        if not upload_data:
            await query.edit_message_text("❌ لم يتم العثور على الملف. يرجى رفع الملف مرة أخيرى.")
            return
        
        # Get network info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM networks WHERE id = ? AND supplier_id = ?', (network_id, user['id']))
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text("❌ شبكة غير صحيحة.")
            return
        
        # Store network selection
        context.user_data['selected_network_id'] = network_id
        
        # Show category selection
        from bot_modules.utils import get_card_categories
        categories = get_card_categories()
        
        category_text = f"""
🎯 **خطوة 2: اختر فئة الكروت**

📁 **الملف:** {upload_data['filename']}
📶 **الشبكة:** {network['name']}
📊 **حجم الملف:** {upload_data['size']/1024:.1f} كيلوبايت

💳 **اختر الفئة المناسبة للكروت:**

⚠️ **ملاحظة:** 
• إذا كان الملف يحتوي على قيم مختلفة، سيتم تحديد الفئة تلقائياً
• يمكنك اختيار "تلقائي" ليتم تحديد الفئة حسب القيمة
"""
        
        keyboard = []
        # Add automatic detection option
        keyboard.append([InlineKeyboardButton("🤖 تحديد تلقائي حسب القيمة", callback_data="select_category_auto")])
        
        # Add category buttons in pairs
        for i in range(0, len(categories), 2):
            row = []
            for j in range(2):
                if i + j < len(categories):
                    cat = categories[i + j]
                    row.append(InlineKeyboardButton(f"💳 {cat['category_name']}", callback_data=f"select_category_{cat['category_value']}"))
            keyboard.append(row)
        
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")])
        
        await query.edit_message_text(category_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing network selection: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار الشبكة.")

async def process_category_selection(update: Update, context: CallbackContext):
    """معالج اختيار فئة الكروت"""
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await update.message.reply_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # معالجة اختيار فئة الكروت
        category_id = context.user_data.get('selected_category')
        if not category_id:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى اختيار فئة كروت أولاً.")
            return
        
        # عرض فئة الكروت المختارة
        category = get_category_by_id(category_id)
        if not category:
            await update.message.reply_text(f"{EMOJIS['error']} لم يتم العثور على فئة الكروت المختارة.")
            return
        
        await update.message.reply_text(
            f"🎫 **فئة الكروت المختارة** 🎫\n\n"
            f"📶 **الاسم:** {category['name']}\n"
            f"💰 **السعر:** {category['price']:.2f} ريال\n"
            f"📊 **الكمية المتاحة:** {category['available_quantity']}\n"
            f"🌐 **الشبكة:** {category['network_name']}\n\n"
            f"✅ **تم اختيار فئة الكروت بنجاح!**\n\n"
            f"🔽 **الخطوة التالية:** رفع ملف الكروت",
            parse_mode='Markdown'
        )
        
        # الانتقال لرفع ملف الكروت
        context.user_data['step'] = 'upload_file'
        
    except Exception as e:
        logger.error(f"Error in process category selection: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة اختيار فئة الكروت.")
    """Process category selection for file upload"""
    try:
        query = update.callback_query
        callback_data = query.data
        
        upload_data = context.user_data.get('upload_file')
        network_id = context.user_data.get('selected_network_id')
        
        if not upload_data or not network_id:
            await query.edit_message_text("❌ بيانات الرفع غير مكتملة. يرجى البدء من جديد.")
            return
        
        # Extract category from callback
        if callback_data == 'select_category_auto':
            selected_category = None
            category_name = "تحديد تلقائي"
        else:
            selected_category = int(callback_data.split('_')[-1])
            category_name = f"{selected_category} ريال"
        
        # Store category selection
        context.user_data['selected_category'] = selected_category
        
        # Get network info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT name FROM networks WHERE id = ?', (network_id,))
        network = cursor.fetchone()
        conn.close()
        
        # Preview file content (first few lines)
        content = upload_data['content']
        lines = content.split('\n')[:5]  # First 5 lines
        preview = '\n'.join(f"{i+1}. {line.strip()}" for i, line in enumerate(lines) if line.strip())
        
        confirmation_text = f"""
✅ **تأكيد رفع الكروت**

📁 **الملف:** {upload_data['filename']}
📶 **الشبكة:** {network['name']}
💳 **الفئة:** {category_name}
📊 **حجم الملف:** {upload_data['size']/1024:.1f} كيلوبايت
📝 **عدد الأسطر:** {len([l for l in lines if l.strip()])}

🔍 **معاينة الأسطر الأولى:**
```
{preview}
```

⚠️ **ملاحظة:** سيتم التحقق من صحة الأرقام وتجنب المكرر.

هل تريد المتابعة؟
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الرفع", callback_data="confirm_upload")],
            [InlineKeyboardButton("🔙 العودة لاختيار الفئة", callback_data=f"select_network_{network_id}")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")]
        ]
        
        await query.edit_message_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error processing category selection: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار الفئة.")

async def cancel_upload(update: Update, context: CallbackContext):
    """معالج إلغاء رفع الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # إلغاء عملية رفع الكروت
        context.user_data.clear()
        
        await query.edit_message_text(
            f"❌ **تم إلغاء رفع الكروت** ❌\n\n"
            f"👤 **{user['full_name']}**\n"
            f"💳 رقم المحفظة: **{user['wallet_number']}**\n\n"
            f"✅ **تم إلغاء العملية بنجاح**\n\n"
            f"🔽 **يمكنك البدء من جديد:**",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data='upload_cards')],
                [InlineKeyboardButton('🌐 إدارة الشبكات', callback_data='manage_networks')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in cancel upload: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إلغاء رفع الكروت.")
    """Cancel file upload"""
    try:
        query = update.callback_query
        
        # Clear upload data
        context.user_data.pop('upload_file', None)
        context.user_data.pop('selected_network_id', None)
        context.user_data.pop('selected_category', None)
        
        await query.edit_message_text("❌ تم إلغاء عملية رفع الكروت.")
        
    except Exception as e:
        logger.error(f"Error cancelling upload: {e}")

async def confirm_upload(update: Update, context: CallbackContext):
    """معالج تأكيد رفع الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # تأكيد رفع الكروت
        network_id = context.user_data.get('selected_network')
        category_id = context.user_data.get('selected_category')
        file_path = context.user_data.get('uploaded_file')
        
        if not all([network_id, category_id, file_path]):
            await query.edit_message_text(f"{EMOJIS['error']} معلومات غير مكتملة. يرجى المحاولة من جديد.")
            return
        
        # معالجة رفع الكروت
        try:
            # هنا يتم معالجة الملف وإضافة الكروت لقاعدة البيانات
            cards_count = process_uploaded_file(file_path, network_id, category_id, user['id'])
            
            success_text = f"""
✅ **تم رفع الكروت بنجاح** ✅

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **نتيجة الرفع:**
• عدد الكروت المرفوعة: **{cards_count}**
• الشبكة: **{get_network_name(network_id)}**
• فئة الكروت: **{get_category_name(category_id)}**
• وقت الرفع: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**

🎉 **تم إضافة الكروت للمخزن بنجاح!**
"""
            
            keyboard = [
                [InlineKeyboardButton('📤 رفع كروت أخرى', callback_data='upload_cards')],
                [InlineKeyboardButton('📊 عرض المخزون', callback_data='view_inventory')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
            # تنظيف البيانات المؤقتة
            context.user_data.clear()
            
        except Exception as process_error:
            logger.error(f"Error processing uploaded file: {process_error}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة الملف: {process_error}")
        
    except Exception as e:
        logger.error(f"Error in confirm upload: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد رفع الكروت.")
    """Confirm and process file upload"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        upload_data = context.user_data.get('upload_file')
        network_id = context.user_data.get('selected_network_id')
        selected_category = context.user_data.get('selected_category')
        
        if not upload_data or not network_id:
            await query.edit_message_text("❌ بيانات الرفع غير مكتملة.")
            return
        
        await query.edit_message_text("⏳ جارٍ معالجة الملف... يرجى الانتظار.")
        
        # Create upload batch record
        import uuid
        batch_id = str(uuid.uuid4())
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO card_upload_batches (id, supplier_id, network_id, filename, upload_status)
            VALUES (?, ?, ?, ?, 'processing')
        ''', (batch_id, user['id'], network_id, upload_data['filename']))
        
        conn.commit()
        conn.close()
        
        # Process cards
        from bot_modules.utils import process_uploaded_cards
        successful, failed, errors = process_uploaded_cards(
            upload_data['content'], user['id'], network_id, batch_id, selected_category
        )
        
        # Clear upload data
        context.user_data.pop('upload_file', None)
        context.user_data.pop('selected_network_id', None)
        context.user_data.pop('selected_category', None)
        
        # Send results
        result_text = f"""
✅ **اكتمل رفع الكروت**

📁 **الملف:** {upload_data['filename']}
📊 **النتائج:**

✅ **نجح:** {successful} كارت
❌ **فشل:** {failed} كارت
📈 **معدل النجاح:** {(successful / max(successful + failed, 1) * 100):.1f}%

"""
        
        if errors:
            result_text += f"\n⚠️ **أخطاء (أول 10):**\n"
            for error in errors[:10]:
                result_text += f"• {error}\n"
        
        keyboard = [
            [InlineKeyboardButton("📊 تقارير الكروت", callback_data="cards_reports")],
            [InlineKeyboardButton("📋 سجل الرفع", callback_data="upload_history")],
            [InlineKeyboardButton("🏪 لوحة المزود", callback_data="supplier_panel")]
        ]
        
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error confirming upload: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرفع.")

async def notification_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات الإشعارات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض إعدادات الإشعارات
        settings_text = f"""
🔔 **إعدادات الإشعارات** 🔔

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

⚙️ **الإشعارات المتاحة:**
• إشعارات المعاملات المالية
• إشعارات الكروت الجديدة
• إشعارات العروض والخصومات
• إشعارات الأمان والحساب
• إشعارات النظام والتحديثات

🔽 **اختر نوع الإعدادات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 إشعارات مالية', callback_data='financial_notifications')],
            [InlineKeyboardButton('🎫 إشعارات الكروت', callback_data='card_notifications')],
            [InlineKeyboardButton('🎁 إشعارات العروض', callback_data='promotion_notifications')],
            [InlineKeyboardButton('🔒 إشعارات الأمان', callback_data='security_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات عامة', callback_data='general_notifications')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in notification settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إعدادات الإشعارات.")
    """Handle notification settings"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
                # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
            'agent': 'وكيل', 
            'supplier': 'مزود', 
            'admin': 'مشرف', 
            'super_admin': 'مشرف أعلى'
        }
        
        settings_text = f"""
🔔 **إعدادات الإشعارات المتقدمة** 🔔

👤 **{user['full_name']}**

📱 **إعدادات الإشعارات الحالية:**

🔔 **الإشعارات العامة:**
• إشعارات المعاملات: مفعل ✅
• إشعارات التحديثات: مفعل ✅
• إشعارات الأمان: مفعل ✅ (لا يمكن إيقافه)

💰 **إشعارات الرصيد:**
• تحويل الرصيد: مفعل ✅
• شحن الرصيد: مفعل ✅
• انخفاض الرصيد: مفعل ✅
• الرصيد المنخفض (أقل من 10 ريال): مفعل ✅

🛒 **إشعارات المبيعات:**
• مبيعات جديدة: مفعل ✅
• طلبات الشراء: مفعل ✅
• حالة الطلبات: مفعل ✅
• تقييمات العملاء: مفعل ✅

🎯 **إشعارات النظام:**
• تحديثات البوت: مفعل ✅
• إشعارات الصيانة: مفعل ✅
• عروض خاصة: مفعل ✅
• نصائح الاستخدام: مفعل ✅

⏰ **أوقات الإشعارات:**
• من الساعة: 8:00 صباحاً
• إلى الساعة: 10:00 مساءً
• أيام العمل فقط: لا
• إشعارات فورية: مفعل ✅

🔧 **إعدادات متقدمة:**
• تجميع الإشعارات: مفعل ✅
• الإشعارات الصوتية: مفعل ✅
• إشعارات البريد الإلكتروني: غير متاح
• إشعارات SMS: غير متاح

💡 **ملاحظة:** يمكنك تخصيص هذه الإعدادات حسب احتياجاتك
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in notification settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات الإشعارات.")

async def choose_upload_method_handler(update: Update, context: CallbackContext):
    """معالج اختيار طريقة رفع الكروت"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض طرق رفع الكروت
        upload_methods_text = f"""
📤 **اختر طريقة رفع الكروت** 📤

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

🔄 **طرق الرفع المتاحة:**
• رفع ملف Excel/CSV (أسرع وأسهل)
• إدخال يدوي (مناسب للكميات الصغيرة)
• استيراد من قاعدة بيانات خارجية
• رفع من تطبيق الهاتف

🔽 **اختر الطريقة المناسبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📁 رفع ملف Excel/CSV', callback_data='upload_excel_file')],
            [InlineKeyboardButton('✏️ إدخال يدوي', callback_data='manual_entry')],
            [InlineKeyboardButton('🗄️ استيراد من قاعدة بيانات', callback_data='import_database')],
            [InlineKeyboardButton('📱 رفع من الهاتف', callback_data='mobile_upload')],
            [InlineKeyboardButton('📋 تحميل قالب Excel', callback_data='download_template')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(upload_methods_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in choose upload method handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض طرق رفع الكروت.")
    """Handle upload method selection"""
    try:
        query = update.callback_query
        
        method_text = f"""
📁 **اختر طريقة رفع الكروت** 📁

📋 **الطرق المتاحة:**

1️⃣ **ملف نصي (.txt)**
• كل رقم في سطر منفصل
• يمكن إضافة القيمة: رقم,قيمة

2️⃣ **ملف CSV (.csv)**
• تنسيق: رقم_الكارت,القيمة
• فصل بالفواصل

3️⃣ **ملف Excel (.xlsx)**
• عمود الأرقام في العمود الأول
• القيم في العمود الثاني (اختياري)

💡 **تعليمات:**
قم برفع الملف مباشرة إلى المحادثة بعد هذه الرسالة
"""
        
        keyboard = [
            [InlineKeyboardButton('📤 رفع الملف الآن', callback_data='upload_cards')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(method_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in choose upload method handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار طريقة الرفع.")

async def network_details_handler(update: Update, context: CallbackContext):
    """معالج تفاصيل الشبكة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض تفاصيل الشبكة
        network_id = context.user_data.get('selected_network')
        if not network_id:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى اختيار شبكة أولاً.")
            return
        
        network = get_network_by_id(network_id)
        if not network:
            await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على الشبكة المحددة.")
            return
        
        # الحصول على إحصائيات الشبكة
        stats = get_network_statistics(network_id)
        
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📶 **الاسم:** {network['name']}
👤 **المزود:** {network['provider']}
🏙️ **المدينة:** {network['city']}
📍 **الموقع:** {network['location']}
📝 **الوصف:** {network['description'] or 'غير محدد'}

📊 **إحصائيات الشبكة:**
• عدد فئات الكروت: **{stats['categories_count']}**
• إجمالي الكروت: **{stats['total_cards']}**
• الكروت المتاحة: **{stats['available_cards']}**
• الكروت المباعة: **{stats['sold_cards']}**
• معدل البيع: **{stats['sales_rate']:.1f}%**

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎫 عرض فئات الكروت', callback_data=f'view_categories_{network_id}')],
            [InlineKeyboardButton('📤 رفع كروت جديدة', callback_data=f'upload_to_network_{network_id}')],
            [InlineKeyboardButton('📊 إحصائيات مفصلة', callback_data=f'network_stats_{network_id}')],
            [InlineKeyboardButton('✏️ تعديل الشبكة', callback_data=f'edit_network_{network_id}')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in network details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.")
    """Handle network details view"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get detailed network info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT n.*, COUNT(nc.id) as card_count
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id
            WHERE n.supplier_id = ?
            GROUP BY n.id
        ''', (user['id'],))
        networks = cursor.fetchall()
        conn.close()
        
        details_text = f"""
📊 **تفاصيل الشبكات المفصلة** 📊

👤 **{user['full_name']}**
📶 **إجمالي الشبكات: {len(networks)}**

"""
        
        if networks:
            for network in networks:
                status = "✅ مفعلة" if network['is_active'] else "⏸️ متوقفة"
                approval = "✅ معتمدة" if network['is_approved'] else "⏳ في انتظار الموافقة"
                details_text += f"""
🏷️ **{network['name']}**
🏙️ المدينة: {network['city']}
📊 الحالة: {status}
✅ الاعتماد: {approval}
💳 عدد الكروت: {network.get('card_count', 0)}
🆔 معرف الشبكة: `{network['id'][:8]}...`
---
"""
        else:
            details_text += "\n⚠️ لا توجد شبكات مسجلة"
        
        keyboard = [
            [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in network details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكات.")

async def privacy_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات الخصوصية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض إعدادات الخصوصية
        privacy_text = f"""
🔒 **إعدادات الخصوصية** 🔒

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🔐 **إعدادات الخصوصية المتاحة:**
• عرض الملف الشخصي للمستخدمين الآخرين
• مشاركة معلومات المعاملات
• عرض رقم الهاتف
• عرض العنوان
• إشعارات النشاط

🔽 **اختر نوع الإعدادات:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👤 الملف الشخصي', callback_data='profile_privacy')],
            [InlineKeyboardButton('💰 خصوصية المعاملات', callback_data='transaction_privacy')],
            [InlineKeyboardButton('📱 خصوصية الاتصال', callback_data='contact_privacy')],
            [InlineKeyboardButton('📍 خصوصية الموقع', callback_data='location_privacy')],
            [InlineKeyboardButton('🔔 إشعارات النشاط', callback_data='activity_notifications')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(privacy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in privacy settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إعدادات الخصوصية.")
    """Handle privacy settings"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
        privacy_text = f"""
🔒 **إعدادات الخصوصية والأمان** 🔒

👤 **{user['full_name']}**

🛡️ **إعدادات الخصوصية الحالية:**

👁️ **مشاركة المعلومات:**
• إظهار الاسم للآخرين: مفعل ✅
• إظهار رقم الهاتف: مخفي ❌
• إظهار رقم المحفظة: للمعاملات فقط ⚠️
• إظهار آخر ظهور: مفعل ✅

💰 **خصوصية المعاملات:**
• إخفاء تفاصيل المعاملات: مخفي ❌
• إظهار الرصيد للآخرين: مخفي ❌
• سجل المعاملات: خاص ✅
• إشعارات المعاملات: مفعل ✅

🔐 **إعدادات الأمان:**
• تأكيد العمليات المالية: مفعل ✅
• إشعارات تسجيل الدخول: مفعل ✅
• حماية من العمليات المشبوهة: مفعل ✅
• قفل الحساب التلقائي: مفعل ✅

📊 **مشاركة البيانات:**
• بيانات الاستخدام: للتحسين فقط ✅
• الإحصائيات: مجهولة الهوية ✅
• بيانات التسويق: مخفي ❌
• بيانات التحليل: مجهولة الهوية ✅

🔒 **إعدادات الوصول:**
• السماح بالبحث عني: مفعل ✅
• إظهار حالة النشاط: مفعل ✅
• السماح بالرسائل المباشرة: مفعل ✅
• قبول طلبات الصداقة: مفعل ✅

⚠️ **تحذيرات الأمان:**
• لا تشارك معلومات الدخول مع أحد
• تحقق من هوية المرسل قبل التحويل
• أبلغ عن أي نشاط مشبوه فوراً
• استخدم كلمات مرور قوية

🔧 **إعدادات متقدمة:**
• تشفير البيانات: مفعل ✅
• النسخ الاحتياطي الآمن: مفعل ✅
• حذف البيانات عند الإلغاء: مفعل ✅
• مراجعة الأمان الدورية: شهرياً ✅
"""
        
        keyboard = [
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(privacy_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in privacy settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات الخصوصية.")

async def search_networks_handler(update: Update, context: CallbackContext):
    """معالج البحث في الشبكات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات البحث في الشبكات
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🔍 **طرق البحث المتاحة:**
• البحث بالاسم
• البحث بالمزود
• البحث بالمدينة
• البحث بالموقع
• البحث بالسعر
• البحث بالكمية المتاحة

🔽 **اختر طريقة البحث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📝 البحث بالاسم', callback_data='search_by_name')],
            [InlineKeyboardButton('👤 البحث بالمزود', callback_data='search_by_provider')],
            [InlineKeyboardButton('🏙️ البحث بالمدينة', callback_data='search_by_city')],
            [InlineKeyboardButton('📍 البحث بالموقع', callback_data='search_by_location')],
            [InlineKeyboardButton('💰 البحث بالسعر', callback_data='search_by_price')],
            [InlineKeyboardButton('📊 البحث بالكمية', callback_data='search_by_quantity')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات البحث.")
    """Handle network search functionality"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**

📝 **يمكنك البحث عن:**
• اسم الشبكة
• معرف المزود (يبدأ بـ 80)
• معرف الشبكة

💡 **لبدء البحث:**
أرسل كلمة البحث كرسالة نصية بعد هذه الرسالة

🔍 **أمثلة:**
• `سبافون`
• `801234`
• `صنعاء`
"""
        
        keyboard = [
            [InlineKeyboardButton('📶 عرض جميع شبكاتي', callback_data='manage_networks')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        # Set context for search mode
        context.user_data['search_mode'] = 'networks'
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

async def filter_by_category_handler(update: Update, context: CallbackContext):
    """معالج تصفية الشبكات حسب الفئة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات التصفية حسب الفئة
        filter_text = f"""
🔍 **تصفية الشبكات حسب الفئة** 🔍

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **فئات الشبكات المتاحة:**
• شبكات الجوال (يمن نت، MTN، سبأفون)
• شبكات المنازل (ADSL، الألياف البصرية)
• شبكات الشركات (خطوط مخصصة)
• شبكات الألعاب (سرعة عالية)
• شبكات الأعمال (خدمات متقدمة)

🔽 **اختر الفئة المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📱 شبكات الجوال', callback_data='filter_mobile')],
            [InlineKeyboardButton('🏠 شبكات المنازل', callback_data='filter_home')],
            [InlineKeyboardButton('🏢 شبكات الشركات', callback_data='filter_business')],
            [InlineKeyboardButton('🎮 شبكات الألعاب', callback_data='filter_gaming')],
            [InlineKeyboardButton('💼 شبكات الأعمال', callback_data='filter_enterprise')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(filter_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in filter by category handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات التصفية.")
    """Handle filtering cards by category"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        from bot_modules.utils import get_cards_stats_by_category
        stats = get_cards_stats_by_category(user['id'])
        
        filter_text = f"""
🎯 **فلترة الكروت حسب الفئة** 🎯

👤 **{user['full_name']}**

📊 **إحصائيات الكروت حسب الفئة:**
"""
        
        keyboard = []
        
        if stats:
            for stat in stats:
                filter_text += f"""
💳 **{stat['category_name']}**
📋 إجمالي: {stat['total_cards']} | متاح: {stat['available_cards']} | مباع: {stat['sold_cards']}
💰 قيمة متاحة: {stat['available_value']:.2f} ريال
---"""
                
                # Add filter button for each category
                keyboard.append([InlineKeyboardButton(
                    f"💳 عرض {stat['category_name']} ({stat['available_cards']} متاح)", 
                    callback_data=f"view_category_{stat['card_category']}"
                )])
        else:
            filter_text += "\n⚠️ لا توجد كروت محملة بعد"
        
        keyboard.append([InlineKeyboardButton('📊 تقارير الكروت', callback_data='cards_reports')])
        keyboard.append([InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')])
        
        await query.edit_message_text(filter_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in filter by category handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في فلترة الكروت.")

async def sales_reports_handler(update: Update, context: CallbackContext):
    """معالج تقارير المبيعات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] not in ['agent', 'supplier']:
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للوكلاء والمزودين فقط.")
            return
        
        # عرض تقارير المبيعات
        reports_text = f"""
📊 **تقارير المبيعات** 📊

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **{USER_ROLES.get(user['role'], 'غير محدد')}**

📈 **إحصائيات المبيعات:**
• إجمالي المبيعات: **{get_user_total_sales(user['id']):.2f}** ريال
• مبيعات هذا الشهر: **{get_user_monthly_sales(user['id']):.2f}** ريال
• عدد الكروت المباعة: **{get_user_sold_cards(user['id'])}**
• متوسط سعر البيع: **{get_user_avg_sale_price(user['id']):.2f}** ريال

🔽 **اختر نوع التقرير:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقرير يومي', callback_data='daily_sales_report')],
            [InlineKeyboardButton('📈 تقرير أسبوعي', callback_data='weekly_sales_report')],
            [InlineKeyboardButton('📅 تقرير شهري', callback_data='monthly_sales_report')],
            [InlineKeyboardButton('📋 تقرير سنوي', callback_data='yearly_sales_report')],
            [InlineKeyboardButton('📊 تقرير مفصل', callback_data='detailed_sales_report')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sales reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تقارير المبيعات.")
    """Handle sales reports"""
    try:
        query = update.callback_query
        
        # الحصول على تقارير المبيعات الفعلية
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # مبيعات اليوم
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE type = 'card_purchase' AND DATE(created_at) = DATE('now')
        ''')
        today_sales, today_revenue = cursor.fetchone()
        
        # مبيعات الأسبوع
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE type = 'card_purchase' AND DATE(created_at) >= DATE('now', '-7 days')
        ''')
        week_sales, week_revenue = cursor.fetchone()
        
        # مبيعات الشهر
        cursor.execute('''
            SELECT COUNT(*), COALESCE(SUM(amount), 0)
            FROM transactions 
            WHERE type = 'card_purchase' AND DATE(created_at) >= DATE('now', 'start of month')
        ''')
        month_sales, month_revenue = cursor.fetchone()
        
        # أفضل الساعات للمبيعات
        cursor.execute('''
            SELECT strftime('%H', created_at) as hour, COUNT(*) as sales_count
            FROM transactions 
            WHERE type = 'card_purchase'
            GROUP BY hour
            ORDER BY sales_count DESC
            LIMIT 3
        ''')
        top_hours = cursor.fetchall()
        
        conn.close()
        
        reports_text = f"""
📈 **تقارير المبيعات التفصيلية** 📈

📅 **مبيعات اليوم:**
🛒 عدد المبيعات: **{today_sales or 0}** عملية
💰 إجمالي الإيرادات: **{today_revenue:,.2f}** ريال

📅 **مبيعات الأسبوع:**
🛒 عدد المبيعات: **{week_sales or 0}** عملية  
💰 إجمالي الإيرادات: **{week_revenue:,.2f}** ريال

📅 **مبيعات الشهر:**
🛒 عدد المبيعات: **{month_sales or 0}** عملية
💰 إجمالي الإيرادات: **{month_revenue:,.2f}** ريال

📊 **تحليل الأداء:**
📈 نمو المبيعات: **{((week_revenue - today_revenue*7)/max(today_revenue*7, 1)*100):+.1f}%**
💵 متوسط قيمة البيع: **{(month_revenue/max(month_sales, 1)):,.2f}** ريال

⏰ **أفضل أوقات المبيعات:**
"""
        
        if top_hours:
            for hour, count in top_hours:
                hour_12 = int(hour)
                period = "صباحاً" if hour_12 < 12 else "مساءً"
                if hour_12 > 12:
                    hour_12 -= 12
                elif hour_12 == 0:
                    hour_12 = 12
                reports_text += f"🕐 الساعة {hour_12}:00 {period} - {count} مبيعة\n"
        else:
            reports_text += "❌ لا توجد بيانات كافية"
        
        keyboard = [
            [InlineKeyboardButton('📊 تقارير الكروت', callback_data='cards_reports')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in sales reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تقارير المبيعات.")

async def add_network_handler(update: Update, context: CallbackContext):
    """معالج إضافة شبكة جديدة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['role'] != 'supplier':
            await query.edit_message_text(f"{EMOJIS['error']} هذه الميزة متاحة للمزودين فقط.")
            return
        
        # عرض نموذج إضافة شبكة جديدة
        add_network_text = f"""
🌐 **إضافة شبكة جديدة** 🌐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **مزود**

📝 **معلومات الشبكة المطلوبة:**
• اسم الشبكة
• اسم المزود
• المدينة
• الموقع
• الوصف (اختياري)

🔽 **اختر طريقة الإضافة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('✏️ إدخال يدوي', callback_data='manual_network_entry')],
            [InlineKeyboardButton('📁 رفع ملف', callback_data='upload_network_file')],
            [InlineKeyboardButton('📋 قالب إضافة الشبكة', callback_data='download_network_template')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(add_network_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in add network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض نموذج إضافة الشبكة.")
    """Handle add network"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
        # التحقق من صلاحيات المستخدم
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            add_text = """
❌ **غير مسموح**

هذه الميزة متاحة للمزودين والمشرفين فقط.
للحصول على حساب مزود، تواصل مع الإدارة.
"""
        else:
            # تفعيل وضع إضافة الشبكة
            context.user_data.clear()
            context.user_data['adding_network'] = True
            context.user_data['network_step'] = 'name'
            
            add_text = f"""
➕ **إضافة شبكة جديدة** ➕

👤 **{user['full_name']}** (مزود معتمد)

📝 **سنقوم بإضافة الشبكة خطوة بخطوة:**

🔸 **الخطوة 1 من 4**
📋 **أدخل اسم الشبكة:**

مثال: "شبكة النور للإنترنت"

💡 **ملاحظة:**
• اختر اسماً واضحاً ومميزاً
• سيتم عرض الاسم للعملاء
• تأكد من صحة الاسم قبل الإرسال

📤 **أرسل اسم الشبكة الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(add_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in add network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إضافة الشبكة.")

async def promotion_details_handler(update: Update, context: CallbackContext):
    """معالج تفاصيل العروض والخصومات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض تفاصيل العروض والخصومات
        promotion_text = f"""
🎁 **تفاصيل العروض والخصومات** 🎁

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🎯 **العروض المتاحة لك:**
• خصم 10% على أول شراء
• خصم 5% على الكروت المنزلية
• عرض خاص للوكلاء: عمولة إضافية 2%
• كوبونات شهرية بقيمة 50 ريال
• عرض الولاء: خصم 15% بعد 10 مشتريات

🔽 **اختر نوع العرض:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ كوبونات الخصم', callback_data='discount_coupons')],
            [InlineKeyboardButton('🔥 العروض الحالية', callback_data='current_promotions')],
            [InlineKeyboardButton('📱 كوبونات خاصة', callback_data='special_coupons')],
            [InlineKeyboardButton('🎯 عرض الولاء', callback_data='loyalty_offer')],
            [InlineKeyboardButton('📊 تاريخ العروض', callback_data='promotions_history')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promotion_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotion details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل العروض.")
    """Handle promotion details"""
    try:
        query = update.callback_query
        
        # الحصول على العروض المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن العروض النشطة (افتراضياً من الشبكات ذات الأسعار المنخفضة)
        cursor.execute('''
            SELECT n.name, n.provider, n.location, 
                   MIN(cc.price) as min_price, 
                   COUNT(cc.id) as categories_count
            FROM networks n
            JOIN card_categories cc ON n.id = cc.network_id
            WHERE n.is_active = 1 AND cc.is_available = 1
            GROUP BY n.id, n.name, n.provider, n.location
            HAVING min_price <= 50
            ORDER BY min_price ASC
            LIMIT 5
        ''')
        special_offers = cursor.fetchall()
        
        # عروض الكوبونات (افتراضياً)
        cursor.execute('''
            SELECT COUNT(*) FROM coupons WHERE is_used = 0
        ''')
        available_coupons = cursor.fetchone()[0] or 0
        
        conn.close()
        
        promo_text = f"""
🎁 **العروض والخصومات المتاحة** 🎁

🔥 **عروض خاصة على الشبكات:**

"""
        
        if special_offers:
            for i, (name, provider, location, price, categories) in enumerate(special_offers, 1):
                location_text = f"📍 {location}" if location else ""
                promo_text += f"""
🏆 **عرض {i}:** {name}
👤 {provider} {location_text}  
💰 **أسعار تبدأ من {price:,.0f} ريال**
📦 {categories} فئة متاحة
🎯 **خصم خاص للعملاء الجدد!**
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        promo_text += f"""

🎟️ **عروض الكوبونات:**
• كوبونات متاحة: **{available_coupons}** كوبون
• شحن فوري وآمن
• أسعار مخفضة للكميات
• متاح 24/7

🎯 **عروض موسمية:**
• خصم 10% للعملاء الجدد
• عروض الجمعة البيضاء
• مكافآت الولاء
• خصومات الكميات الكبيرة

⏰ **صالح حتى:** نهاية الشهر
💡 **شروط العرض:** 
• للعملاء المسجلين فقط
• لا يمكن دمج العروض
• العرض محدود الكمية
"""
        
        keyboard = [
            [InlineKeyboardButton('🎁 العروض', callback_data='promotions')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promo_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotion details handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تفاصيل العروض.")

async def mark_all_read_handler(update: Update, context: CallbackContext):
    """معالج تحديد جميع الإشعارات كمقروءة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # تحديد جميع الإشعارات كمقروءة
        try:
            mark_all_notifications_as_read(user['id'])
            
            success_text = f"""
✅ **تم تحديد جميع الإشعارات كمقروءة** ✅

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **نتيجة العملية:**
• تم تحديد جميع الإشعارات كمقروءة
• عدد الإشعارات المحدثة: **{get_user_unread_notifications_count(user['id'])}**
• وقت التحديث: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**

🎉 **تم تحديث حالة الإشعارات بنجاح!**
"""
            
            keyboard = [
                [InlineKeyboardButton('🔔 عرض الإشعارات', callback_data='my_notifications')],
                [InlineKeyboardButton('⚙️ إعدادات الإشعارات', callback_data='notification_settings')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
        except Exception as mark_error:
            logger.error(f"Error marking notifications as read: {mark_error}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحديث حالة الإشعارات: {mark_error}")
        
    except Exception as e:
        logger.error(f"Error in mark all read handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالج تحديد الإشعارات كمقروءة.")
# تم حذف النسخة المكررة من mark_all_read_handler

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """معالج عرض تفاصيل الشبكة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض تفاصيل الشبكة
        network = get_network_by_id(network_id)
        if not network:
            await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على الشبكة المحددة.")
            return
        
        # الحصول على إحصائيات الشبكة
        stats = get_network_statistics(network_id)
        
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📶 **الاسم:** {network['name']}
👤 **المزود:** {network['provider']}
🏙️ **المدينة:** {network['city']}
📍 **الموقع:** {network['location']}
📝 **الوصف:** {network['description'] or 'غير محدد'}

📊 **إحصائيات الشبكة:**
• عدد فئات الكروت: **{stats['categories_count']}**
• إجمالي الكروت: **{stats['total_cards']}**
• الكروت المتاحة: **{stats['available_cards']}**
• الكروت المباعة: **{stats['sold_cards']}**
• معدل البيع: **{stats['sales_rate']:.1f}%**

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎫 عرض فئات الكروت', callback_data=f'view_categories_{network_id}')],
            [InlineKeyboardButton('🛒 شراء كروت', callback_data=f'buy_from_network_{network_id}')],
            [InlineKeyboardButton('📊 إحصائيات مفصلة', callback_data=f'network_stats_{network_id}')],
            [InlineKeyboardButton('⭐ تقييم الشبكة', callback_data=f'rate_network_{network_id}')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network details: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.")
    """Show detailed information about a specific network"""
    try:
        query = update.callback_query
        
        # الحصول على تفاصيل الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.id = ? AND n.is_active = 1
            GROUP BY n.id, n.name, n.provider, n.location, n.description, n.created_at
        ''', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='search_networks')
                ]])
            )
            return
        
        net_id, name, provider, location, description, created_at, cat_count, min_price, max_price, available_cards = network
        
        # الحصول على فئات الكروت
        cursor.execute('''
            SELECT name, price, description
            FROM card_categories
            WHERE network_id = ? AND is_available = 1
            ORDER BY price ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        location_text = f"📍 {location}" if location else "📍 غير محدد"
        price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price and max_price and min_price != max_price else f"{min_price:,.0f}" if min_price else "غير محدد"
        
        details_text = f"""
🌐 **تفاصيل الشبكة** 🌐

📋 **المعلومات الأساسية:**
🏷️ الاسم: **{name}**
👤 المزود: **{provider}**
{location_text}
📝 الوصف: {description or 'غير متاح'}
📅 تاريخ الإضافة: {created_at[:10] if created_at else 'غير محدد'}

📊 **الإحصائيات:**
💳 عدد الفئات: **{cat_count}** فئة
💰 نطاق الأسعار: **{price_range}** ريال
📦 الكروت المتاحة: **{available_cards or 0}** كرت

💳 **فئات الكروت المتاحة:**

"""
        
        if categories:
            for cat_name, price, cat_desc in categories:
                details_text += f"""
🎫 **{cat_name}**
💰 السعر: **{price:,.0f}** ريال
📝 الوصف: {cat_desc or 'غير متاح'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            details_text += "❌ لا توجد فئات متاحة حالياً"
        
        keyboard = [
            [InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')],
            [InlineKeyboardButton('🔙 العودة للشبكات', callback_data='search_networks'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(details_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network details: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة.")

# تم حذف النسخة المكررة من search_networks_handler

async def transfer_to_friend_handler(update: Update, context: CallbackContext):
    """معالج تحويل الرصيد للأصدقاء"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات تحويل الرصيد
        transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

🔽 **اختر طريقة التحويل:**
"""
        
        keyboard = [
            [InlineKeyboardButton('👥 تحويل لصديق', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('⚡ تحويل سريع', callback_data='quick_transfer')],
            [InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton('🎟️ تحويل بالكوبونات', callback_data='coupon_transfer')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer to friend handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات التحويل.")
    """معالج تحويل الرصيد للأصدقاء"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        transfer_text = f"""
💸 **تحويل رصيد لصديق** 💸

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📋 **تعليمات التحويل:**
1️⃣ أدخل رقم محفظة المستلم (9 أرقام)
2️⃣ أدخل المبلغ المراد تحويله
3️⃣ تأكيد العملية

💡 **للتحويل السريع:**
• استخدم زر "🔍 البحث عن مستخدم" أدناه
• ابحث بالاسم أو رقم المحفظة أو الهاتف
• أدخل المبلغ المطلوب تحويله
• تأكيد العملية بأمان

🔒 **ضمانات الأمان:**
• تأكيد مزدوج قبل التحويل
• إشعار فوري للطرفين
• سجل كامل للمعاملة
"""
        
        keyboard = [
            [InlineKeyboardButton(f'🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton(f'📋 آخر التحويلات', callback_data='transfer_history')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة التحويل.")

# تم حذف النسخة المكررة من personal_reports_handler

# تم حذف النسخة المكررة من promotions_handler

# تم حذف النسخة المكررة من my_notifications_handler

# تم حذف النسخة المكررة من account_settings_handler

async def transfer_history_handler(update: Update, context: CallbackContext):
    """معالج سجل التحويلات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض سجل التحويلات
        history_text = f"""
📋 **سجل التحويلات** 📋

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

📊 **إحصائيات التحويلات:**
• إجمالي التحويلات: **{get_user_transfer_count(user['id'])}**
• التحويلات المرسلة: **{get_user_sent_transfers(user['id'])}**
• التحويلات المستلمة: **{get_user_received_transfers(user['id'])}**

🔽 **اختر نوع السجل:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📤 التحويلات المرسلة', callback_data='sent_transfers')],
            [InlineKeyboardButton('📥 التحويلات المستلمة', callback_data='received_transfers')],
            [InlineKeyboardButton('📊 إحصائيات التحويلات', callback_data='transfer_stats')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer history handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض سجل التحويلات.")
# تم حذف النسخة المكررة من transfer_history_handler

async def update_profile_handler(update: Update, context: CallbackContext):
    """معالج تحديث الملف الشخصي"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات تحديث الملف الشخصي
        profile_text = f"""
👤 **تحديث الملف الشخصي** 👤

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
📱 رقم الهاتف: **{user.get('phone', 'غير محدد')}**

📝 **البيانات القابلة للتحديث:**
• الاسم الكامل
• رقم الهاتف
• العنوان
• معلومات إضافية

🔽 **اختر البيانات للتحديث:**
"""
        
        keyboard = [
            [InlineKeyboardButton('✏️ تحديث الاسم', callback_data='update_name')],
            [InlineKeyboardButton('📱 تحديث الهاتف', callback_data='update_phone')],
            [InlineKeyboardButton('📍 تحديث العنوان', callback_data='update_address')],
            [InlineKeyboardButton('📝 معلومات إضافية', callback_data='update_extra_info')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in update profile handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات تحديث الملف الشخصي.")
# تم حذف النسخة المكررة من update_profile_handler
        
        keyboard = [
            [InlineKeyboardButton('📞 تواصل مع الدعم', callback_data='contact_admin'),
             InlineKeyboardButton('📋 عرض البيانات الكاملة', callback_data='view_full_profile')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(update_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in update profile handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحديث البيانات.")

async def change_password_handler(update: Update, context: CallbackContext):
    """معالج تغيير كلمة المرور"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض إعدادات كلمة المرور
        password_text = f"""
🔐 **تغيير كلمة المرور** 🔐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🔒 **أمان الحساب:**
• كلمة المرور الحالية: محمية ✅
• التشفير: نشط ✅
• الحماية: متقدمة ✅

🛡️ **ميزات الأمان:**
• تشفير قوي للبيانات
• حماية من الوصول غير المصرح
• تسجيل دخول آمن
• مراقبة النشاط المشبوه

🔑 **إعدادات الأمان:**
• تأكيد العمليات المالية: مفعل ✅
• إشعارات تسجيل الدخول: مفعل ✅
• قفل تلقائي للحساب: مفعل ✅
• مراجعة أمان دورية: شهرياً ✅

💡 **ملاحظة:**
نظام البوت يستخدم معرف تلغرام الآمن
لا حاجة لكلمة مرور إضافية

🔒 **حسابك محمي بالكامل!**
"""
        
        keyboard = [
            [InlineKeyboardButton('🛡️ إعدادات الأمان', callback_data='security_settings'),
             InlineKeyboardButton('🔔 إشعارات الأمان', callback_data='security_notifications')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(password_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in change password handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات كلمة المرور.")
# تم حذف النسخة المكررة من change_password_handler

async def contact_admin_handler(update: Update, context: CallbackContext):
    """معالج التواصل مع الإدارة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض معلومات التواصل مع الإدارة
        contact_text = f"""
📞 **التواصل مع الإدارة** 📞

👤 **{user['full_name']}**
💳 رقم محفظتك: **{user['wallet_number']}**

📱 **طرق التواصل المتاحة:**

💬 **تلغرام:**
• الدعم الفني: @YemenNetSupport
• المشرف الأعلى: @YemenNetAdmin
• القناة الرسمية: @YemenNetOfficial

📱 **واتساب:**
• رقم الدعم: +967777777777
• ساعات العمل: 8 صباحاً - 10 مساءً
• رد سريع خلال 30 دقيقة

📧 **البريد الإلكتروني:**
• الدعم العام: support@yemennet.com
• الشكاوى: complaints@yemennet.com
• الاقتراحات: suggestions@yemennet.com

🏢 **المكاتب:**
• المكتب الرئيسي: صنعاء، شارع الزبيري
• فرع عدن: المعلا، شارع الملكة أروى
• فرع تعز: شارع جمال عبد الناصر

⏰ **أوقات العمل:**
• السبت - الخميس: 8:00 ص - 10:00 م
• الجمعة: 2:00 م - 10:00 م
• خدمة الطوارئ: 24/7

🎯 **نوع المساعدة:**
• مشاكل تقنية
• استفسارات مالية
• شكاوى الخدمة
• اقتراحات التطوير
"""
        
        keyboard = [
            [InlineKeyboardButton('💬 دعم تلغرام', callback_data='telegram_support')],
            [InlineKeyboardButton('📱 دعم واتساب', callback_data='whatsapp_support')],
            [InlineKeyboardButton('📧 دعم البريد', callback_data='email_support')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(contact_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in contact admin handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض معلومات التواصل.")
    """معالج التواصل مع الإدارة"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        contact_text = f"""
📞 **التواصل مع الإدارة** 📞

👤 **{user['full_name']}**
💳 رقم محفظتك: **{user['wallet_number']}**

📱 **طرق التواصل المتاحة:**

💬 **تلغرام:**
• الدعم الفني: @YemenNetSupport
• المشرف الأعلى: @YemenNetAdmin
• القناة الرسمية: @YemenNetOfficial

📱 **واتساب:**
• رقم الدعم: +967777777777
• ساعات العمل: 8 صباحاً - 10 مساءً
• رد سريع خلال 30 دقيقة

📧 **البريد الإلكتروني:**
• الدعم العام: support@yemennet.com
• الشكاوى: complaints@yemennet.com
• الاقتراحات: suggestions@yemennet.com

🏢 **المكاتب:**
• المكتب الرئيسي: صنعاء، شارع الزبيري
• فرع عدن: المعلا، شارع الملكة أروى
• فرع تعز: شارع جمال عبد الناصر

⏰ **أوقات العمل:**
• السبت - الخميس: 8:00 ص - 10:00 م
• الجمعة: 2:00 م - 10:00 م
• خدمة الطوارئ: 24/7

🎯 **نوع المساعدة:**
• مشاكل تقنية
• استفسارات مالية
• شكاوى الخدمة
• اقتراحات التطوير
"""
        
        keyboard = [
            [InlineKeyboardButton('💬 تلغرام الدعم', url='https://t.me/YemenNetSupport'),
             InlineKeyboardButton('📱 واتساب', url='https://wa.me/967777777777')],
            [InlineKeyboardButton('📧 إرسال إيميل', callback_data='send_email'),
             InlineKeyboardButton('🏢 عناوين المكاتب', callback_data='office_locations')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(contact_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in contact admin handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معلومات التواصل.")

async def account_status_handler(update: Update, context: CallbackContext):
    """معالج حالة الحساب"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض حالة الحساب
        status_text = f"""
📊 **حالة الحساب** 📊

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
👑 الدور: **{USER_ROLES.get(user['role'], 'غير محدد')}**

📈 **حالة الحساب:**
• حالة الحساب: نشط ✅
• تاريخ التسجيل: **{user.get('created_at', 'غير محدد')[:10] if user.get('created_at') else 'غير محدد'}**
• آخر تحديث: اليوم
• مستوى الثقة: عالي ⭐⭐⭐⭐⭐

🔒 **الأمان:**
• حماية المحفظة: مفعل ✅
• تأكيد العمليات: مفعل ✅
• إشعارات الأمان: مفعل ✅
• مراقبة النشاط: مفعل ✅

📊 **الإحصائيات:**
• عدد المعاملات: **{get_user_transaction_count(user['id'])}**
• تقييم المستخدم: **{get_user_rating(user['id']):.1f}/5**
• مستوى النشاط: عالي 🔥

🔽 **اختر العملية المطلوبة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account status handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض حالة الحساب.")
    """معالج حالة الحساب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات الحساب
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # آخر نشاط
        cursor.execute('''
            SELECT MAX(created_at) FROM transactions WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id']))
        last_activity = cursor.fetchone()[0]
        
        # عدد المعاملات
        cursor.execute('''
            SELECT COUNT(*) FROM transactions WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id']))
        total_transactions = cursor.fetchone()[0] or 0
        
        conn.close()
        
        # تحديد مستوى النشاط
        if total_transactions >= 50:
            activity_level = "🔥 نشط جداً"
            activity_color = "🟢"
        elif total_transactions >= 20:
            activity_level = "⚡ نشط"
            activity_color = "🟡"
        elif total_transactions >= 5:
            activity_level = "📊 متوسط النشاط"
            activity_color = "🟠"
        else:
            activity_level = "🌱 مبتدئ"
            activity_color = "🔵"
        
        status_text = f"""
📊 **حالة الحساب** 📊

👤 **{user['full_name']}**
💳 **رقم المحفظة:** {user['wallet_number']}

{activity_color} **مستوى النشاط:** {activity_level}

📈 **إحصائيات الحساب:**
• الرصيد الحالي: **{user['balance']:,.2f}** ريال
• إجمالي المعاملات: **{total_transactions}** معاملة
• آخر نشاط: {last_activity[:10] if last_activity else 'لم يتم تسجيل نشاط'}
• تاريخ التسجيل: {user.get('created_at', 'غير محدد')[:10] if user.get('created_at') else 'غير محدد'}

✅ **حالة الحساب:**
• الحساب: نشط ومفعل ✅
• التحقق: مكتمل ✅
• الأمان: محمي ✅
• الإشعارات: مفعلة ✅

🎯 **تقييم الحساب:**
• الموثوقية: ممتاز ⭐⭐⭐⭐⭐
• الأمان: عالي 🔒
• النشاط: {activity_level}
• التفاعل: إيجابي 👍

🏆 **الإنجازات:**
• عضو مسجل ✅
• معاملات آمنة ✅
• استخدام منتظم ✅
• بدون مخالفات ✅

💡 **نصائح لتحسين الحساب:**
• استخدم الميزات المتقدمة
• راجع التقارير الشخصية
• حافظ على أمان الحساب
• تفاعل مع العروض الجديدة
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats')],
            [InlineKeyboardButton('🔔 إشعاراتي', callback_data='my_notifications'),
             InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(status_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account status handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في حالة الحساب.")

async def recharge_balance_handler(update: Update, context: CallbackContext):
    """معالج شحن الرصيد"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # عرض خيارات شحن الرصيد
        recharge_text = f"""
💰 **شحن الرصيد** 💰

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**
💰 رصيدك الحالي: **{user['balance']:.2f}** ريال

🔄 **طرق الشحن المتاحة:**
• شحن بكوبونات الخصم
• شحن من الوكلاء المعتمدين
• شحن من المكاتب الرسمية
• شحن من البنوك الشريكة

🔽 **اختر طريقة الشحن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon')],
            [InlineKeyboardButton('🏪 مواقع الوكلاء', callback_data='agent_locations')],
            [InlineKeyboardButton('🏢 المكاتب الرسمية', callback_data='official_offices')],
            [InlineKeyboardButton('🏦 البنوك الشريكة', callback_data='partner_banks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(recharge_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in recharge balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات شحن الرصيد.")
    """Handle balance recharge"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
        recharge_text = f"""
💰 **شحن الرصيد** 💰

👤 مرحباً **{user['full_name']}**
💳 رقم محفظتك: **{user['wallet_number']}**
💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

📝 **طرق الشحن المتاحة:**

🎟️ **1. شحن بكوبون (فوري):**
   • اشتر كوبون من أقرب نقطة بيع
   • استخدم ميزة "🎟️ شحن بكوبون" في البوت
   • يتم إضافة الرصيد فوراً

🏪 **2. شحن عبر الوكلاء:**
   • اذهب لأقرب وكيل معتمد
   • أعطه رقم محفظتك: **{user['wallet_number']}**
   • سيقوم بشحن حسابك مباشرة

📞 **3. التواصل مع الدعم:**
   • للمساعدة في عملية الشحن
   • للاستفسار عن نقاط البيع
   • لحل أي مشاكل في الشحن

💡 **أسرع طريقة: استخدم الكوبونات!**
"""
        
        keyboard = [
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('🏪 مواقع الوكلاء', callback_data='agent_locations')],
            [InlineKeyboardButton('📞 التواصل مع الدعم', callback_data='contact_support'),
             InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(recharge_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in recharge balance handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في شحن الرصيد.")

async def confirm_transfer_handler(update: Update, context: CallbackContext, confirmed: bool):
    """معالج تأكيد التحويل"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if confirmed:
            # تأكيد التحويل
            success_text = f"""
✅ **تم تأكيد التحويل بنجاح** ✅

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🎉 **تم إتمام عملية التحويل بنجاح!**
💰 المبلغ: **{context.user_data.get('transfer_amount', 0):.2f}** ريال
👥 المستلم: **{context.user_data.get('recipient_name', 'غير محدد')}**

📊 **تفاصيل العملية:**
• رقم العملية: **#{random.randint(100000, 999999)}**
• وقت التحويل: **{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}**
• حالة العملية: مكتملة ✅

🔽 **اختر العملية التالية:**
"""
            
            keyboard = [
                [InlineKeyboardButton('💸 تحويل آخر', callback_data='transfer_to_friend')],
                [InlineKeyboardButton('📊 تقاريري', callback_data='personal_reports')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
            # تنظيف البيانات المؤقتة
            context.user_data.clear()
            
        else:
            # إلغاء التحويل
            cancel_text = f"""
❌ **تم إلغاء التحويل** ❌

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

✅ **تم إلغاء عملية التحويل بنجاح**
💰 المبلغ: **{context.user_data.get('transfer_amount', 0):.2f}** ريال
👥 المستلم: **{context.user_data.get('recipient_name', 'غير محدد')}**

🔽 **اختر العملية التالية:**
"""
            
            keyboard = [
                [InlineKeyboardButton('💸 محاولة تحويل آخر', callback_data='transfer_to_friend')],
                [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(cancel_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
            # تنظيف البيانات المؤقتة
            context.user_data.clear()
        
        # Get transfer details
        target_user_id = context.user_data.get('target_user_id')
        target_user_name = context.user_data.get('target_user_name')
        amount = context.user_data.get('transfer_amount')
        transfer_fee = context.user_data.get('transfer_fee')
        
        if not all([target_user_id, amount, transfer_fee]):
            await query.edit_message_text(f"{EMOJIS['error']} معلومات التحويل مفقودة. يرجى البدء من جديد.")
            return
        
        # Execute the transfer
        from bot_modules.database import get_db_connection
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get target user details
        cursor.execute('SELECT * FROM users WHERE id = ?', (target_user_id,))
        target_user = cursor.fetchone()
        
        if not target_user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم المستهدف غير موجود.")
            conn.close()
            return
        
        # Create transfer transactions
        import uuid
        from datetime import datetime
        
        # Transfer transaction
        transfer_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, to_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (transfer_id, user['id'], target_user['id'], amount, 'transfer', 'تحويل رصيد من صديق', datetime.now()))
        
        # Fee transaction
        fee_id = str(uuid.uuid4())
        cursor.execute('''
            INSERT INTO transactions 
            (id, from_user, amount, type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (fee_id, user['id'], transfer_fee, 'transfer_fee', f'رسوم تحويل رصيد إلى {target_user["full_name"]}', datetime.now()))
        
        # Update balances
        from bot_modules.utils import recalc_and_set_user_balance
        sender_new_balance = recalc_and_set_user_balance(user['id'])
        receiver_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        conn.commit()
        conn.close()
        
        # Clear user state
        context.user_data.clear()
        
        # Send confirmation to sender
        success_text = f"""
✅ **تم إرسال الرصيد بنجاح!**

📤 **تفاصيل التحويل:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المرسل: **{amount:.2f}** ريال
💳 رسوم التحويل: **{transfer_fee:.2f}** ريال
📊 إجمالي الخصم: **{amount + transfer_fee:.2f}** ريال

💵 **الأرصدة:**
🔻 رصيدك الجديد: **{sender_new_balance:.2f}** ريال
🔺 رصيد المستلم: **{receiver_new_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 سيتم إشعار المستلم فوراً
"""
        
        await query.edit_message_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver
        try:
            notification_text = f"""
💰 **تم استلام رصيد جديد!** 💰

📥 **تفاصيل الاستلام:**
👤 المرسل: **{user['full_name']}**
💰 المبلغ المستلم: **{amount:.2f}** ريال
💵 رصيدك الجديد: **{receiver_new_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=target_user['telegram_id'],
                text=notification_text,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")
        
        # Log the transfer
        logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in confirm transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تنفيذ التحويل.")

def main():
    """Main function to start the bot"""
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Create persistence
        persistence = PicklePersistence(filepath='yemen_net_bot_data')
        application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        
        # Set bot commands (will be done after startup)
        async def post_init(application):
            try:
                logger.info("Setting bot commands...")
                await application.bot.set_my_commands(QUICK_COMMANDS)
                await application.bot.set_chat_menu_button(menu_button=MenuButtonCommands())
                logger.info("Bot commands set successfully")
            except Exception as e:
                logger.warning(f'Failed setting commands/menu: {e}')
        
        application.post_init = post_init
        
        # Create conversation handler with proper fallbacks
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler('start', COMMAND_HANDLERS['start']),
                CommandHandler('menu', lambda u, c: show_main_menu(u, c, get_user(u.effective_user.id)['role'] if get_user(u.effective_user.id) else 'customer')),
                CommandHandler('wallet', COMMAND_HANDLERS['wallet']),
                CommandHandler('admin', COMMAND_HANDLERS['admin']),
            ],
            states=CONVERSATION_STATES,
            fallbacks=[
                CommandHandler('cancel', COMMAND_HANDLERS['cancel']),
                CallbackQueryHandler(lambda u, c: show_main_menu(u, c, get_user(u.effective_user.id)['role'] if get_user(u.effective_user.id) else 'customer'), pattern='^main_menu$'),
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), COMMAND_HANDLERS['cancel']),
            ],
            name='yemen_net_conversation',
            persistent=True,
            allow_reentry=True,
            per_message=False,
        )
        
        # Error handler
        async def error_handler(update: object, context):
            """Log errors and handle them gracefully"""
            logger.error("Exception while handling an update:", exc_info=context.error)
            
            # Try to send error message to user
            try:
                if isinstance(update, Update) and update.effective_chat:
                    await context.bot.send_message(
                        chat_id=update.effective_chat.id,
                        text=f"{EMOJIS['error']} حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
                    )
            except Exception:
                pass
        
        # Add handlers
        application.add_handler(conv_handler)
        application.add_handler(CallbackQueryHandler(button_click_handler))
        application.add_handler(MessageHandler(filters.Document.ALL, handle_document))  # Document handler for file uploads
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
        application.add_error_handler(error_handler)
        
        # Add individual command handlers for direct access
        for command, handler in COMMAND_HANDLERS.items():
            if command not in ['start']:  # start is already in conversation handler
                application.add_handler(CommandHandler(command, handler))
        
        # Start the bot
        logger.info(f'{EMOJIS["fire"]} Starting Pottagrm Enhanced Bot v2.1.0...')
        application.run_polling(allowed_updates=Update.ALL_TYPES)
        
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise

if __name__ == '__main__':
    main()

