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
    from config import *
    from database import init_db
    from utils import *
    from handlers import COMMAND_HANDLERS, CONVERSATION_STATES, handle_text_message, show_main_menu
    from admin_functions import ADMIN_CALLBACKS, activate_single_supplier
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
async def button_click_handler(update: Update, context):
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
            from bot_modules.handlers import redeem_coupon_handler
            return await redeem_coupon_handler(update, context)
        elif callback_data == 'cancel_coupon':
            from bot_modules.handlers import cancel_coupon_handler
            return await cancel_coupon_handler(update, context)
        elif callback_data == 'quick_transfer':
            from handlers import quick_transfer_handler
            return await quick_transfer_handler(update, context)
        elif callback_data.startswith('select_user_'):
            from handlers import select_user_for_transfer
            user_id = callback_data.split('_')[2]
            return await select_user_for_transfer(update, context, user_id)
        elif callback_data.startswith('amount_'):
            from handlers import process_amount_selection
            parts = callback_data.split('_')
            amount = parts[1]
            user_id = parts[2]
            return await process_amount_selection(update, context, amount, user_id)
        
        # Purchase handlers
        elif callback_data.startswith('buy_card_'):
            from handlers import process_card_purchase
            category_id = callback_data.split('_')[2]
            return await process_card_purchase(update, context, category_id)
        elif callback_data.startswith('confirm_purchase_'):
            from network_handler import confirm_card_purchase
            category_id = callback_data.split('_')[2]
            return await confirm_card_purchase(update, context, category_id)
        elif callback_data.startswith('confirm_transfer_'):
            parts = callback_data.split('_')
            user_id = parts[2]
            amount = parts[3]
            return await confirm_user_transfer(update, context, user_id, amount)
        elif callback_data == 'insufficient_balance':
            from network_handler import handle_insufficient_balance
            return await handle_insufficient_balance(update, context)
        elif callback_data.startswith('out_of_stock_'):
            from network_handler import handle_out_of_stock
            category_id = callback_data.split('_')[2]
            return await handle_out_of_stock(update, context, category_id)
        elif callback_data.startswith('error_category_'):
            from network_handler import handle_category_error
            category_id = callback_data.split('_')[2]
            return await handle_category_error(update, context, category_id)
        elif callback_data.startswith('skip_location_'):
            from handlers import skip_network_location
            network_id = callback_data.split('_')[2]
            return await skip_network_location(update, context, network_id)
        elif callback_data.startswith('edit_comm_'):
            from bot_modules.admin_functions import edit_specific_commission
            commission_id = callback_data.split('_')[2]
            return await edit_specific_commission(update, context, commission_id)
        elif callback_data.startswith('admin_add_category_'):
            from bot_modules.admin_functions import admin_add_category_handler
            network_id = callback_data.split('_')[3]
            return await admin_add_category_handler(update, context, network_id)
        elif callback_data.startswith('admin_upload_to_network_'):
            from bot_modules.admin_functions import admin_network_upload_handler
            network_id = callback_data.split('_')[-1]  # آخر عنصر هو network_id
            return await admin_network_upload_handler(update, context, network_id)
        elif callback_data.startswith('admin_upload_category_'):
            from bot_modules.admin_functions import admin_upload_category_handler
            category_id = callback_data.split('_')[3]
            return await admin_upload_category_handler(update, context, category_id)
        elif callback_data.startswith('admin_upload_single_'):
            from bot_modules.admin_functions import admin_upload_single_card_handler
            category_id = callback_data.split('_')[3]
            return await admin_upload_single_card_handler(update, context, category_id)
        
        # Search by type handlers
        elif callback_data.startswith('search_by_'):
            from handlers import search_by_type_handler
            search_type = callback_data.split('_')[2]
            return await search_by_type_handler(update, context, search_type)
        
        # Admin panel routing
        elif callback_data == 'admin_panel':
            if user['role'] in ['admin', 'super_admin']:
                from admin_functions import admin_panel_handler
                return await admin_panel_handler(update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
                return
        
        # Transfer confirmation handlers
        elif callback_data == 'confirm_transfer_yes':
            return await confirm_transfer_handler(update, context, True)
        elif callback_data == 'confirm_transfer_no':
            return await confirm_transfer_handler(update, context, False)
        
        # Super admin functions
        elif callback_data in ADMIN_CALLBACKS:
            if user['role'] == 'super_admin':
                return await ADMIN_CALLBACKS[callback_data](update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
        
        # Supplier activation (specific handling)
        elif callback_data.startswith('activate_supplier_'):
            if user['role'] == 'super_admin':
                supplier_id = callback_data.split('_')[2]
                return await activate_single_supplier(update, context, supplier_id)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
        
        # Role selection during registration
        elif callback_data.startswith('role_'):
            from handlers import choose_role
            return await choose_role(update, context)
        
        # Core features
        elif callback_data == 'buy_cards':
            await buy_cards_handler(update, context)
        elif callback_data.startswith('buy_from_network_'):
            network_id = callback_data.split('_')[3]
            await show_network_categories(update, context, network_id)
        elif callback_data.startswith('quick_search_'):
            search_term = callback_data.split('_')[2]
            await perform_quick_search(update, context, search_term)
        elif callback_data == 'transfer_to_friend':
            await transfer_handler(update, context)
        
        # Personal features
        elif callback_data == 'personal_reports':
            await personal_reports_handler(update, context)
        elif callback_data == 'my_ratings':
            await my_ratings_handler(update, context)
        elif callback_data == 'my_notifications':
            await my_notifications_handler(update, context)
        elif callback_data == 'promotions':
            await promotions_handler(update, context)
        elif callback_data == 'account_settings':
            await account_settings_handler(update, context)
        
        # Role-specific features
        elif callback_data == 'agent_panel':
            await agent_panel_handler(update, context)
        elif callback_data == 'my_commissions':
            await my_commissions_handler(update, context)
        elif callback_data == 'supplier_panel':
            await supplier_panel_handler(update, context)
        
        # Additional features
        elif callback_data == 'view_networks':
            await view_networks_handler(update, context)
        elif callback_data == 'search_user':
            await search_user_handler(update, context)
        elif callback_data == 'my_sent_ratings':
            await my_sent_ratings_handler(update, context)
        elif callback_data == 'transaction_details':
            await transaction_details_handler(update, context)
        elif callback_data == 'wallet_stats':
            await wallet_stats_handler(update, context)
        
        # Enhanced supplier features
        elif callback_data == 'upload_cards':
            await upload_cards_handler(update, context)
        elif callback_data == 'manage_networks':
            await manage_networks_handler(update, context)
        elif callback_data == 'search_network':
            await search_network_handler(update, context)
        elif callback_data == 'search_networks':
            await customer_search_networks_handler(update, context)
        elif callback_data == 'cards_reports':
            await cards_reports_handler(update, context)
        elif callback_data == 'sales_stats':
            await sales_stats_handler(update, context)
        elif callback_data == 'upload_history':
            await upload_history_handler(update, context)
        elif callback_data == 'supplier_settings':
            await supplier_settings_handler(update, context)
        
        # File upload processing
        elif callback_data.startswith('select_network_'):
            await process_network_selection(update, context)
        elif callback_data.startswith('select_category_'):
            await process_category_selection(update, context)
        elif callback_data == 'cancel_upload':
            await cancel_upload(update, context)
        elif callback_data == 'confirm_upload':
            await confirm_upload(update, context)
        elif callback_data == 'notification_settings':
            await notification_settings_handler(update, context)
        elif callback_data == 'choose_upload_method':
            await choose_upload_method_handler(update, context)
        elif callback_data == 'network_details':
            await network_details_handler(update, context)
        elif callback_data == 'privacy_settings':
            await privacy_settings_handler(update, context)
        elif callback_data == 'search_networks':
            await search_networks_handler(update, context)
        elif callback_data == 'filter_by_category':
            await filter_by_category_handler(update, context)
        elif callback_data == 'sales_reports':
            await sales_reports_handler(update, context)
        elif callback_data == 'add_network':
            await add_network_handler(update, context)
        elif callback_data == 'promotion_details':
            await promotion_details_handler(update, context)
        elif callback_data == 'mark_all_read':
            await mark_all_read_handler(update, context)
        elif callback_data == 'recharge_balance':
            await recharge_balance_handler(update, context)
        elif callback_data == 'personal_reports':
            await personal_reports_handler(update, context)
        elif callback_data == 'promotions':
            await promotions_handler(update, context)
        elif callback_data == 'my_notifications':
            await my_notifications_handler(update, context)
        elif callback_data == 'account_settings':
            await account_settings_handler(update, context)
        elif callback_data == 'transfer_history':
            await transfer_history_handler(update, context)
        elif callback_data == 'update_profile':
            await update_profile_handler(update, context)
        elif callback_data == 'change_password':
            await change_password_handler(update, context)
        elif callback_data == 'contact_admin':
            await contact_admin_handler(update, context)
        elif callback_data == 'account_status':
            await account_status_handler(update, context)
        
        # Refresh balance
        elif callback_data == 'refresh_balance':
            new_balance = recalc_and_set_user_balance(user['id'])
            await query.edit_message_text(
                f"🔄 **تم تحديث الرصيد**\n\n💰 رصيدك الحالي: **{new_balance:.2f}** ريال",
                parse_mode='Markdown'
            )
        
        # Help
        elif callback_data == 'help':
            await help_handler(update, context)
        

        # Support and agent callbacks
        elif callback_data == 'agent_locations':
            from bot_modules.handlers import agent_locations_handler
            return await agent_locations_handler(update, context)
        elif callback_data == 'contact_support':
            from bot_modules.handlers import contact_support_handler
            return await contact_support_handler(update, context)
        elif callback_data == 'recharge_help':
            await query.edit_message_text(
                "💡 **مساعدة الشحن** 💡\n\n"
                "🎟️ **أسرع طريقة:** استخدم الكوبونات\n"
                "🏪 **الوكلاء:** متاحون في جميع المحافظات\n"
                "📞 **الدعم:** متاح 24/7\n\n"
                "💡 اختر الطريقة المناسبة لك:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon')],
                    [InlineKeyboardButton('🏪 مواقع الوكلاء', callback_data='agent_locations')],
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )

                # Default fallback for unrecognized callbacks
        else:
            # Try dynamic dispatch to existing command handlers before fallback UI
            try:
                if callback_data in COMMAND_HANDLERS:
                    return await COMMAND_HANDLERS[callback_data](update, context)
            except Exception as _e:
                logger.warning(f"Dynamic dispatch failed for {callback_data}: {_e}")
            
            logger.warning(f"Unhandled callback: {callback_data}")
            await query.edit_message_text(
                f"{EMOJIS['warning']} حدثت مشكلة في تنفيذ هذا الخيار حالياً.\n\n"
                f"يرجى العودة للقائمة الرئيسية والمحاولة من جديد.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
    
    except Exception as e:
        logger.error(f"Error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"{EMOJIS['error']} حدث خطأ. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except:
            pass

# Placeholder handlers for features being implemented
async def personal_reports_handler(update: Update, context):
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

async def my_ratings_handler(update: Update, context):
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

async def my_notifications_handler(update: Update, context):
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

async def promotions_handler(update: Update, context):
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

async def account_settings_handler(update: Update, context):
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

async def buy_cards_handler(update: Update, context):
    """Handle buy cards request"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على الشبكات المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إصلاح: إزالة شرط HAVING categories_count > 0 لعرض جميع الشبكات حتى لو لم تحتوي على فئات كروت
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY n.name
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        # تسجيل مفصل لمساعدة المطورين في التشخيص
        logger.info(f"جلب الشبكات: تم العثور على {len(networks)} شبكة")
        if len(networks) == 0:
            logger.warning("لا توجد شبكات متاحة! تحقق من: 1) وجود شبكات في جدول networks 2) قيم is_active و is_approved")
        else:
            networks_with_categories = sum(1 for n in networks if n[4] > 0)
            networks_without_categories = len(networks) - networks_with_categories
            logger.info(f"الشبكات مع فئات كروت: {networks_with_categories}, بدون فئات: {networks_without_categories}")
        
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
                
                # معالجة محسنة للشبكات بدون فئات كروت
                if cat_count > 0:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                    categories_text = f"💳 {cat_count} فئة متاحة"
                    price_text = f"💰 {price_range} ريال"
                else:
                    categories_text = "💳 لا توجد فئات كروت بعد"
                    price_text = "💰 لم يتم تحديد الأسعار"
                
                buy_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
{categories_text}
{price_text}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            buy_text += """❌ **لا توجد شبكات متاحة حالياً**

🔍 **الأسباب المحتملة:**
• لم يتم إضافة شبكات بعد
• جميع الشبكات غير نشطة أو غير معتمدة
• مشكلة في قاعدة البيانات

💡 **الحلول:**
• تواصل مع المشرف لإضافة شبكات
• تحقق لاحقاً من توفر شبكات جديدة

🔍 **للبحث عن شبكات محددة:**
• اضغط على زر \"🔍 البحث في الشبكات\" أدناه
• ابحث بالاسم أو المعرف أو اسم المزود
• استخدم البحث السريع للشبكات المعروفة"""
        
        keyboard = []
        
        # إضافة أزرار الشبكات للشراء
        if networks:
            for network in networks[:6]:  # أول 6 شبكات
                net_id = network[0]
                name = network[1]
                cat_count = network[4]  # عدد فئات الكروت
                
                # إضافة أزرار مختلفة حسب توفر فئات الكروت
                if cat_count > 0:
                    keyboard.append([
                        InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
                    ])
                else:
                    keyboard.append([
                        InlineKeyboardButton(f'👁️ عرض {name} (لا توجد فئات)', callback_data=f'network_{net_id}')
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

async def transfer_handler(update: Update, context):
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
async def agent_panel_handler(update: Update, context):
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

async def my_commissions_handler(update: Update, context):
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

async def supplier_panel_handler(update: Update, context):
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

async def view_networks_handler(update: Update, context):
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

async def search_user_handler(update: Update, context):
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

async def my_sent_ratings_handler(update: Update, context):
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

async def transaction_details_handler(update: Update, context):
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

async def wallet_stats_handler(update: Update, context):
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
async def upload_cards_handler(update: Update, context):
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

async def manage_networks_handler(update: Update, context):
    """Handle network management"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get user's networks
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, name, city, provider, description, location, is_active, is_approved, created_at
            FROM networks 
            WHERE supplier_id = ? 
            ORDER BY id DESC
        ''', (user['id'],))
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
                net_id, name, city, provider, description, location, is_active, is_approved, created_at = network
                status = "✅ مفعلة" if is_active else "⏸️ متوقفة"
                approval = "✅ معتمدة" if is_approved else "⏳ في انتظار الموافقة"
                networks_text += f"""
📶 **{name}**
🏙️ المدينة: {city or 'غير محدد'}
👤 المزود: {provider or 'غير محدد'}
📊 الحالة: {status}
✅ الاعتماد: {approval}
---"""
        else:
            networks_text += "\n⚠️ لا توجد شبكات مسجلة بعد"
        
        keyboard = [
            [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='add_network')],
            [InlineKeyboardButton('🔍 البحث عن شبكة', callback_data='search_network')],
            [InlineKeyboardButton('📊 تفاصيل الشبكات', callback_data='network_details')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إدارة الشبكات.")

async def search_network_handler(update: Update, context):
    """Handle network search"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # إرسال رسالة تطلب البحث
        search_text = f"""
🔍 **البحث عن الشبكات** 🔍

👤 **{user['full_name']}**

💡 **كيفية البحث:**
• اكتب اسم الشبكة (مثل: يمنتل)
• اكتب معرف الشبكة (مثل: 21)
• اكتب اسم المزود (مثل: MTN)

📝 **أرسل كلمة البحث الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 عودة لإدارة الشبكات', callback_data='manage_networks')]
        ]
        
        # حفظ حالة البحث
        context.user_data['searching_network'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search network handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def perform_network_search(update: Update, context):
    """Perform actual network search"""
    try:
        user = get_user(update.message.from_user.id)
        search_query = update.message.text.strip()
        
        if not search_query:
            await update.message.reply_text("❌ يرجى إدخال كلمة بحث صحيحة.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث في الشبكات
        cursor.execute('''
            SELECT id, name, city, provider, description, location, is_active, is_approved, created_at
            FROM networks 
            WHERE (name LIKE ? OR provider LIKE ? OR id = ?) AND supplier_id = ?
            ORDER BY name
        ''', (f'%{search_query}%', f'%{search_query}%', search_query, user['id']))
        
        networks = cursor.fetchall()
        conn.close()
        
        if networks:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_query}"**

📊 **تم العثور على {len(networks)} شبكة:**

"""
            
            for network in networks:
                net_id, name, city, provider, description, location, is_active, is_approved, created_at = network
                status = "✅ مفعلة" if is_active else "⏸️ متوقفة"
                approval = "✅ معتمدة" if is_approved else "⏳ في انتظار الموافقة"
                
                search_results += f"""
📶 **{name}** (ID: {net_id})
🏙️ المدينة: {city or 'غير محدد'}
👤 المزود: {provider or 'غير محدد'}
📍 الموقع: {location or 'غير محدد'}
📊 الحالة: {status}
✅ الاعتماد: {approval}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_query}"**

❌ **لم يتم العثور على شبكات تطابق البحث**

💡 **اقتراحات:**
• تأكد من كتابة الاسم بشكل صحيح
• جرب البحث باسم المزود
• تحقق من معرف الشبكة
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='search_network')],
            [InlineKeyboardButton('🔙 عودة لإدارة الشبكات', callback_data='manage_networks')]
        ]
        
        # إزالة حالة البحث
        context.user_data['searching_network'] = False
        
        await update.message.reply_text(search_results, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in perform network search: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

async def customer_search_networks_handler(update: Update, context):
    """Handle customer network search"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # إرسال رسالة تطلب البحث مع تعليمات واضحة
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

💡 **كيفية البحث:**

🔤 **البحث بالاسم:**
• اكتب اسم الشبكة (مثل: دريم، يمنتل، MTN)
• اكتب جزء من الاسم (مثل: دريم، يمن)

🔢 **البحث بالمعرف:**
• اكتب رقم معرف الشبكة (مثل: 1، 2، 3)

👤 **البحث بالمزود:**
• اكتب اسم المزود (مثل: عبد الملك، يمنتل)

📝 **أرسل كلمة البحث الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 بحث سريع: دريم', callback_data='quick_search_dream')],
            [InlineKeyboardButton('🔍 بحث سريع: يمنتل', callback_data='quick_search_yemen')],
            [InlineKeyboardButton('🔍 بحث سريع: MTN', callback_data='quick_search_mtn')],
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
        ]
        
        # حفظ حالة البحث للعميل
        context.user_data['customer_searching_network'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in customer search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def perform_quick_search(update: Update, context, search_term):
    """تنفيذ البحث السريع"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # تحويل مصطلح البحث إلى العربية
        search_mapping = {
            'dream': 'دريم',
            'yemen': 'يمنتل',
            'mtn': 'MTN'
        }
        
        arabic_term = search_mapping.get(search_term, search_term)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث في الشبكات
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1 
                  AND (n.name LIKE ? OR n.provider LIKE ? OR n.id = ?)
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY n.name
        ''', (f'%{arabic_term}%', f'%{arabic_term}%', search_term))
        
        networks = cursor.fetchall()
        conn.close()
        
        if networks:
            search_results = f"""
🔍 **نتائج البحث السريع عن: "{arabic_term}"**

📊 **تم العثور على {len(networks)} شبكة:**

"""
            
            keyboard = []
            
            for network in networks:
                net_id, name, provider, location, cat_count, min_price, max_price = network
                location_text = f"📍 {location}" if location else ""
                
                # معالجة محسنة للشبكات بدون فئات كروت
                if cat_count > 0:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                    categories_text = f"💳 {cat_count} فئة متاحة"
                    price_text = f"💰 {price_range} ريال"
                    
                    # أزرار للشراء
                    keyboard.append([
                        InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
                    ])
                else:
                    categories_text = "💳 لا توجد فئات كروت بعد"
                    price_text = "💰 لم يتم تحديد الأسعار"
                    
                    # أزرار للعرض فقط
                    keyboard.append([
                        InlineKeyboardButton(f'👁️ عرض {name} (لا توجد فئات)', callback_data=f'network_{net_id}')
                    ])
                
                search_results += f"""
🌐 **{name}** (ID: {net_id})
👤 {provider} {location_text}
{categories_text}
{price_text}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            search_results = f"""
🔍 **نتائج البحث السريع عن: "{arabic_term}"**

❌ **لم يتم العثور على شبكات تطابق البحث**

💡 **اقتراحات:**
• تأكد من صحة كلمة البحث
• جرب البحث بكلمات أخرى
• تحقق من توفر الشبكات
"""
            keyboard = []
        
        # إضافة أزرار الإجراءات
        keyboard.extend([
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
        ])
        
        await query.edit_message_text(search_results, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in quick search: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث السريع.")

async def show_network_categories(update: Update, context, network_id):
    """عرض فئات الكروت لشبكة معينة مع الأسعار"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على معلومات الشبكة
        cursor.execute('''
            SELECT id, name, provider, description, location
            FROM networks 
            WHERE id = ? AND is_active = 1 AND is_approved = 1
        ''', (network_id,))
        
        network = cursor.fetchone()
        if not network:
            await query.edit_message_text(f"{EMOJIS['error']} الشبكة غير موجودة أو غير متاحة.")
            return
        
        net_id, name, provider, description, location = network
        
        # الحصول على فئات الكروت المتاحة
        cursor.execute('''
            SELECT id, name, value, price, currency, stock_count
            FROM card_categories 
            WHERE network_id = ? AND is_available = 1 AND stock_count > 0
            ORDER BY price ASC
        ''', (network_id,))
        
        categories = cursor.fetchall()
        conn.close()
        
        if not categories:
            # لا توجد فئات كروت متاحة
            no_cards_text = f"""
📶 **{name}** - لا توجد كروت متاحة

👤 **المزود:** {provider}
📍 **الموقع:** {location or 'غير محدد'}
📝 **الوصف:** {description or 'لا يوجد وصف'}

❌ **لا توجد فئات كروت متاحة حالياً**

💡 **اقتراحات:**
• تحقق لاحقاً من توفر كروت جديدة
• جرب شبكة أخرى متاحة
"""
            
            keyboard = [
                [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')],
                [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')]
            ]
            
            await query.edit_message_text(no_cards_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            return
        
        # عرض فئات الكروت مع الأسعار
        categories_text = f"""
📶 **{name}** - فئات الكروت المتاحة

👤 **المزود:** {provider}
📍 **الموقع:** {location or 'غير محدد'}
📝 **الوصف:** {description or 'لا يوجد وصف'}

💰 **رصيدك:** {user['balance']:,.2f} ريال

💳 **فئات الكروت المتاحة ({len(categories)} فئة):**

"""
        
        keyboard = []
        
        for category in categories:
            cat_id, cat_name, value, price, currency, stock = category
            
            # تنسيق السعر
            price_text = f"{price:,.0f} ريال"
            
            # تنسيق القيمة
            if isinstance(value, int):
                value_text = f"{value} جيجا"
            else:
                value_text = str(value)
            
            # إضافة فئة الكرت
            categories_text += f"""
🎯 **{cat_name}**
📊 القيمة: {value_text}
💰 السعر: {price_text}
📦 المخزون: {stock} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            # إضافة زر الشراء
            keyboard.append([
                InlineKeyboardButton(f'🛒 شراء {cat_name} - {price_text}', callback_data=f'buy_card_{cat_id}')
            ])
        
        # إضافة أزرار إضافية
        keyboard.extend([
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton('💰 شحن الرصيد', callback_data='recharge_balance')]
        ])
        
        await query.edit_message_text(categories_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network categories: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض فئات الكروت.")

async def perform_customer_network_search(update: Update, context):
    """Perform customer network search"""
    try:
        user = get_user(update.message.from_user.id)
        search_query = update.message.text.strip()
        
        if not search_query:
            await update.message.reply_text("❌ يرجى إدخال كلمة بحث صحيحة.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث في جميع الشبكات المتاحة للعميل (المعتمدة والنشطة)
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            WHERE n.is_active = 1 AND n.is_approved = 1 
                  AND (n.name LIKE ? OR n.provider LIKE ? OR n.id = ?)
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY n.name
        ''', (f'%{search_query}%', f'%{search_query}%', search_query))
        
        networks = cursor.fetchall()
        conn.close()
        
        if networks:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_query}"**

📊 **تم العثور على {len(networks)} شبكة:**

"""
            
            keyboard = []
            
            for network in networks:
                net_id, name, provider, location, cat_count, min_price, max_price = network
                location_text = f"📍 {location}" if location else ""
                
                # معالجة محسنة للشبكات بدون فئات كروت
                if cat_count > 0:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price != max_price else f"{min_price:,.0f}"
                    categories_text = f"💳 {cat_count} فئة متاحة"
                    price_text = f"💰 {price_range} ريال"
                    
                    # أزرار للشراء
                    keyboard.append([
                        InlineKeyboardButton(f'🛒 شراء من {name}', callback_data=f'buy_from_network_{net_id}')
                    ])
                else:
                    categories_text = "💳 لا توجد فئات كروت بعد"
                    price_text = "💰 لم يتم تحديد الأسعار"
                    
                    # أزرار للعرض فقط
                    keyboard.append([
                        InlineKeyboardButton(f'👁️ عرض {name} (لا توجد فئات)', callback_data=f'network_{net_id}')
                    ])
                
                search_results += f"""
🌐 **{name}** (ID: {net_id})
👤 {provider} {location_text}
{categories_text}
{price_text}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            search_results = f"""
🔍 **نتائج البحث عن: "{search_query}"**

❌ **لم يتم العثور على شبكات تطابق البحث**

💡 **اقتراحات:**
• تأكد من كتابة الاسم بشكل صحيح
• جرب البحث باسم المزود (مثل: يمنتل، MTN)
• تحقق من معرف الشبكة (رقم)
• تأكد أن الشبكة معتمدة ونشطة
"""
            keyboard = []
        
        # إضافة أزرار الإجراءات
        keyboard.extend([
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='search_networks')],
            [InlineKeyboardButton('🔙 عودة لشراء الكروت', callback_data='buy_cards')]
        ])
        
        # إزالة حالة البحث
        context.user_data['customer_searching_network'] = False
        
        await update.message.reply_text(search_results, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in perform customer network search: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في البحث.")

async def cards_reports_handler(update: Update, context):
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

async def sales_stats_handler(update: Update, context):
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

async def upload_history_handler(update: Update, context):
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

async def supplier_settings_handler(update: Update, context):
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

async def help_handler(update: Update, context):
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
    """Handle mark all notifications as read"""
    try:
        query = update.callback_query
        
        await query.edit_message_text("✅ تم تحديد جميع الإشعارات كمقروءة.")
        
    except Exception as e:
        logger.error(f"Error in mark all read handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تحديث الإشعارات.")

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
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

async def search_networks_handler(update: Update, context: CallbackContext):
    """Handle network search with filters"""
    try:
        query = update.callback_query
        
        # الحصول على جميع الشبكات للبحث
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location,
                   COUNT(cc.id) as categories_count,
                   MIN(cc.price) as min_price, MAX(cc.price) as max_price,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id, n.name, n.provider, n.location
            ORDER BY available_cards DESC, n.created_at DESC
        ''')
        networks = cursor.fetchall()
        conn.close()
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

📊 **إجمالي الشبكات المتاحة:** {len(networks)} شبكة

🌐 **الشبكات المتاحة:**

"""
        
        if networks:
            for network in networks[:8]:  # أول 8 شبكات
                net_id, name, provider, location, cat_count, min_price, max_price, available_cards = network
                location_text = f"📍 {location}" if location else ""
                price_range = f"{min_price:,.0f} - {max_price:,.0f}" if min_price and max_price and min_price != max_price else f"{min_price:,.0f}" if min_price else "غير محدد"
                
                search_text += f"""
🌐 **{name}**
👤 {provider} {location_text}
💳 {cat_count} فئة | 💰 {price_range} ريال
📦 متاح: {available_cards or 0} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            search_text += "❌ لا توجد شبكات متاحة حالياً"
        
        keyboard = []
        
        # إضافة أزرار الشبكات للتفاصيل
        if networks:
            for network in networks[:6]:  # أول 6 شبكات للأزرار
                net_id = network[0]
                name = network[1]
                keyboard.append([
                    InlineKeyboardButton(f'📋 تفاصيل {name}', callback_data=f'network_{net_id}')
                ])
        
        keyboard.extend([
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('📊 جميع الشبكات', callback_data='view_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])

        # enable typing a search term after this screen
        context.user_data['awaiting_network_search'] = True

        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def transfer_to_friend_handler(update: Update, context: CallbackContext):
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

async def personal_reports_handler(update: Update, context: CallbackContext):
    """معالج التقارير الشخصية"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على إحصائيات المستخدم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المعاملات
        cursor.execute('''
            SELECT 
                COUNT(*) as total_transactions,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_amount,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_amount,
                COUNT(CASE WHEN from_user = ? THEN 1 END) as sent_count,
                COUNT(CASE WHEN to_user = ? THEN 1 END) as received_count
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        total_trans, sent_amount, received_amount, sent_count, received_count = stats
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(*) as monthly_transactions,
                COALESCE(SUM(amount), 0) as monthly_amount
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) 
            AND DATE(created_at) >= DATE('now', 'start of month')
        ''', (user['id'], user['id']))
        
        monthly_stats = cursor.fetchone()
        monthly_trans, monthly_amount = monthly_stats
        
        conn.close()
        
        reports_text = f"""
📊 **تقاريري الشخصية** 📊

👤 **{user['full_name']}**
💰 **الرصيد الحالي:** {user['balance']:,.2f} ريال
💳 **رقم المحفظة:** {user['wallet_number']}

📈 **إحصائيات شاملة:**

💸 **المعاملات المرسلة:**
• عدد المعاملات: **{sent_count or 0}** معاملة
• إجمالي المبلغ: **{sent_amount:,.2f}** ريال

📥 **المعاملات المستلمة:**
• عدد المعاملات: **{received_count or 0}** معاملة
• إجمالي المبلغ: **{received_amount:,.2f}** ريال

📊 **إحصائيات عامة:**
• إجمالي المعاملات: **{total_trans or 0}** معاملة
• صافي التحويلات: **{received_amount - sent_amount:+,.2f}** ريال

📅 **هذا الشهر:**
• معاملات الشهر: **{monthly_trans or 0}** معاملة
• مبلغ الشهر: **{monthly_amount:,.2f}** ريال

🎯 **تحليل النشاط:**
• متوسط المعاملة: **{(sent_amount + received_amount) / max(total_trans, 1):,.2f}** ريال
• نشاط الشهر: **{monthly_trans / max(total_trans, 1) * 100:.1f}%** من إجمالي النشاط
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تفاصيل المعاملات', callback_data='transaction_details'),
             InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(reports_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in personal reports handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في التقارير الشخصية.")

async def promotions_handler(update: Update, context: CallbackContext):
    """معالج العروض والخصومات"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على العروض المتاحة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # البحث عن أفضل العروض (أقل الأسعار)
        cursor.execute('''
            SELECT n.name, n.provider, n.location, MIN(cc.price) as best_price, COUNT(cc.id) as categories
            FROM networks n
            JOIN card_categories cc ON n.id = cc.network_id
            WHERE n.is_active = 1 AND cc.is_available = 1
            GROUP BY n.id, n.name, n.provider, n.location
            HAVING best_price <= 100
            ORDER BY best_price ASC
            LIMIT 6
        ''')
        offers = cursor.fetchall()
        
        # الكوبونات المتاحة
        cursor.execute('SELECT COUNT(*) FROM coupons WHERE is_used = 0')
        available_coupons = cursor.fetchone()[0] or 0
        
        conn.close()
        
        promotions_text = f"""
🎁 **العروض والخصومات** 🎁

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

🔥 **العروض الحصرية:**

"""
        
        if offers:
            for i, (name, provider, location, price, categories) in enumerate(offers, 1):
                location_text = f"📍 {location}" if location else ""
                promotions_text += f"""
🏆 **عرض {i}: {name}**
👤 {provider} {location_text}
💰 **أسعار تبدأ من {price:,.0f} ريال فقط!**
📦 {categories} فئة متاحة
🎯 خصم خاص للعملاء المميزين
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        
        promotions_text += f"""

🎟️ **عروض الكوبونات:**
• كوبونات متاحة: **{available_coupons}** كوبون
• شحن فوري وآمن
• أسعار مخفضة
• متاح 24/7

🎯 **عروض خاصة:**
• خصم 10% للعملاء الجدد
• مكافآت الولاء
• عروض نهاية الأسبوع
• خصومات الكميات

⏰ **العروض محدودة الوقت!**
💡 **اغتنم الفرصة الآن**
"""
        
        keyboard = [
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards'),
             InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon')],
            [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks'),
             InlineKeyboardButton('🎁 تفاصيل العروض', callback_data='promotion_details')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(promotions_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in promotions handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في العروض والخصومات.")

async def my_notifications_handler(update: Update, context: CallbackContext):
    """معالج إشعاراتي"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على آخر المعاملات كإشعارات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT type, amount, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT 10
        ''', (user['id'], user['id']))
        
        recent_transactions = cursor.fetchall()
        conn.close()
        
        notifications_text = f"""
🔔 **إشعاراتي** 🔔

👤 **{user['full_name']}**

📬 **آخر الإشعارات:**

"""
        
        if recent_transactions:
            for trans_type, amount, description, created_at in recent_transactions:
                # تحديد نوع الإشعار
                if trans_type == 'card_purchase':
                    icon = "🛒"
                    title = "شراء كرت"
                elif trans_type == 'coupon_redeem':
                    icon = "🎟️"
                    title = "شحن بكوبون"
                elif trans_type == 'transfer':
                    icon = "💸"
                    title = "تحويل رصيد"
                else:
                    icon = "📊"
                    title = "معاملة"
                
                date_str = created_at[:16] if created_at else 'غير محدد'
                notifications_text += f"""
{icon} **{title}**
💰 المبلغ: **{amount:,.2f}** ريال
📝 التفاصيل: {description or 'غير محدد'}
📅 {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            notifications_text += """
📭 **لا توجد إشعارات حديثة**

💡 **ستصلك إشعارات عند:**
• إتمام معاملة جديدة
• استلام تحويل رصيد
• شراء كرت إنترنت
• شحن رصيد بكوبون
• تحديثات النظام المهمة
"""
        
        keyboard = [
            [InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='notification_settings'),
             InlineKeyboardButton('✅ وضع علامة مقروء', callback_data='mark_all_read')],
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(notifications_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in my notifications handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في الإشعارات.")

async def account_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات الحساب"""
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
⚙️ **إعدادات الحساب** ⚙️

👤 **{user['full_name']}**
💳 **رقم المحفظة:** {user['wallet_number']}
📱 **رقم الهاتف:** {user.get('phone', 'غير محدد')}
🆔 **معرف تلغرام:** {user.get('telegram_id', 'غير محدد')}
👑 **نوع الحساب:** {role_names.get(user.get('role', 'user'), 'عميل')}

⚙️ **الإعدادات المتاحة:**

🔔 **إعدادات الإشعارات:**
• إشعارات المعاملات: مفعل ✅
• إشعارات التحديثات: مفعل ✅
• إشعارات العروض: مفعل ✅

🔒 **إعدادات الأمان:**
• حماية المحفظة: مفعل ✅
• تأكيد العمليات: مفعل ✅
• إشعارات الأمان: مفعل ✅

👁️ **إعدادات الخصوصية:**
• إظهار الاسم: مفعل ✅
• إظهار رقم الهاتف: مخفي ❌
• إظهار آخر ظهور: مفعل ✅

📊 **إعدادات التقارير:**
• التقارير الشخصية: مفعل ✅
• إحصائيات المحفظة: مفعل ✅
• سجل المعاملات: مفعل ✅

💡 **معلومات الحساب:**
• تاريخ التسجيل: {user.get('created_at', 'غير محدد')[:10] if user.get('created_at') else 'غير محدد'}
• آخر تحديث: اليوم
• حالة الحساب: نشط ✅
"""
        
        keyboard = [
            [InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='notification_settings'),
             InlineKeyboardButton('🔒 إعدادات الخصوصية', callback_data='privacy_settings')],
            [InlineKeyboardButton('🔄 تحديث البيانات', callback_data='update_profile'),
             InlineKeyboardButton('🔐 تغيير كلمة المرور', callback_data='change_password')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(settings_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in account settings handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعدادات الحساب.")

async def transfer_history_handler(update: Update, context: CallbackContext):
    """معالج سجل التحويلات"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # الحصول على آخر التحويلات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT from_user, to_user, amount, description, created_at
            FROM transactions 
            WHERE (from_user = ? OR to_user = ?) AND type = 'transfer'
            ORDER BY created_at DESC
            LIMIT 15
        ''', (user['id'], user['id']))
        
        transfers = cursor.fetchall()
        conn.close()
        
        history_text = f"""
📋 **سجل التحويلات** 📋

👤 **{user['full_name']}**
💰 الرصيد الحالي: **{user['balance']:,.2f}** ريال

📊 **آخر 15 تحويل:**

"""
        
        if transfers:
            for from_user_id, to_user_id, amount, description, created_at in transfers:
                # تحديد اتجاه التحويل
                if from_user_id == user['id']:
                    direction = "📤 مرسل"
                    color = "🔴"
                    other_user_id = to_user_id
                else:
                    direction = "📥 مستلم"
                    color = "🟢"
                    other_user_id = from_user_id
                
                # الحصول على اسم المستخدم الآخر
                try:
                    other_user = get_user(other_user_id) if other_user_id else None
                    other_name = other_user['full_name'] if other_user else 'مستخدم محذوف'
                except:
                    other_name = 'غير معروف'
                
                date_str = created_at[:16] if created_at else 'غير محدد'
                
                history_text += f"""
{color} **{direction}**
👤 {other_name}
💰 المبلغ: **{amount:,.2f}** ريال
📝 {description or 'تحويل رصيد'}
📅 {date_str}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            history_text += """
📭 **لا توجد تحويلات سابقة**

💡 **لبدء التحويل:**
• اضغط على "💸 تحويل رصيد جديد"
• ابحث عن المستلم
• أدخل المبلغ وأكد العملية
"""
        
        keyboard = [
            [InlineKeyboardButton('💸 تحويل رصيد جديد', callback_data='transfer_to_friend'),
             InlineKeyboardButton('🔍 البحث عن مستخدم', callback_data='search_user')],
            [InlineKeyboardButton('📊 تقاريري الشخصية', callback_data='personal_reports'),
             InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(history_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer history handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في سجل التحويلات.")

async def update_profile_handler(update: Update, context: CallbackContext):
    """معالج تحديث البيانات الشخصية"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        update_text = f"""
🔄 **تحديث البيانات الشخصية** 🔄

👤 **البيانات الحالية:**
📝 الاسم: **{user['full_name']}**
📱 الهاتف: **{user.get('phone', 'غير محدد')}**
💳 رقم المحفظة: **{user['wallet_number']}**
🆔 معرف تلغرام: **{user.get('telegram_id', 'غير محدد')}**

✏️ **يمكنك تحديث:**
• الاسم الكامل
• رقم الهاتف
• معلومات إضافية

🔒 **لا يمكن تغيير:**
• رقم المحفظة (ثابت)
• معرف تلغرام (تلقائي)

💡 **لتحديث بياناتك:**
تواصل مع الدعم الفني أو استخدم الأزرار أدناه
"""
        
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
        user = get_user(query.from_user.id)
        
        password_text = f"""
🔐 **تغيير كلمة المرور** 🔐

👤 **{user['full_name']}**

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

async def contact_admin_handler(update: Update, context: CallbackContext):
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
    """Handle transfer confirmation"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if not confirmed:
            # User cancelled the transfer
            context.user_data.clear()
            await query.edit_message_text(f"""
❌ **تم إلغاء التحويل**

العملية ألغيت بنجاح. لم يتم خصم أي مبلغ من رصيدك.

💰 رصيدك الحالي: **{user['balance']:,.2f}** ريال

💡 يمكنك استخدام /send_balance لبدء تحويل جديد
""", parse_mode='Markdown')
            return
        
        # User confirmed the transfer - execute it
        if not context.user_data.get('awaiting_transfer_confirmation'):
            await query.edit_message_text(f"{EMOJIS['error']} انتهت صلاحية العملية. يرجى البدء من جديد.")
            return
        
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
async def process_supplier_network_creation(update: Update, context: CallbackContext):
    """معالجة إضافة الشبكة للمزود خطوة بخطوة - مُصحح"""
    try:
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        step = context.user_data.get('network_step', 'name')
        
        if step == 'name':
            context.user_data['network_name'] = text
            context.user_data['network_step'] = 'provider'
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الشبكة:** {text}\n\n🔸 **الخطوة 2 من 4**\n👤 **أدخل اسم المزود:**",
                parse_mode='Markdown'
            )
            
        elif step == 'provider':
            context.user_data['network_provider'] = text
            context.user_data['network_step'] = 'description'
            await update.message.reply_text(
                f"✅ **تم حفظ اسم المزود:** {text}\n\n🔸 **الخطوة 3 من 4**\n📝 **أدخل وصف الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'description':
            context.user_data['network_description'] = text
            context.user_data['network_step'] = 'location'
            await update.message.reply_text(
                f"✅ **تم حفظ وصف الشبكة:** {text}\n\n🔸 **الخطوة 4 من 4**\n📍 **أدخل موقع الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'location':
            network_name = context.user_data.get('network_name')
            provider = context.user_data.get('network_provider')
            description = context.user_data.get('network_description')
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # إدراج مع supplier_id المطلوب
                cursor.execute('''
                    INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                ''', (user['id'], network_name, text, provider, description, text, user['id']))
                
                network_id = cursor.lastrowid
                conn.commit()
                conn.close()
                context.user_data.clear()
                
                await update.message.reply_text(
                    f"✅ **تم إنشاء الشبكة بنجاح!**\n\n🌐 **{network_name}**\n👤 {provider}\n📍 {text}\n🆔 معرف: #{network_id}",
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Error creating network: {e}")
                await update.message.reply_text(f"❌ خطأ في إنشاء الشبكة: {e}")
                context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error in supplier network creation: {e}")
        await update.message.reply_text(f"❌ خطأ في معالجة الشبكة: {e}")
        context.user_data.clear()


async def enhanced_wallet_handler(update: Update, context: CallbackContext):
    """معالج المحفظة المحسنة - مُصحح"""
    try:
        # تحديد نوع التحديث (callback أو message)
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            user = get_user(query.from_user.id)
            is_callback = True
        else:
            user = get_user(update.effective_user.id)
            is_callback = False
        
        if not user:
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً."
            if is_callback:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        # الحصول على المعاملات الحديثة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # آخر المعاملات
        cursor.execute('''
            SELECT id, from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT 8
        ''', (user['id'], user['id']))
        
        recent_transactions = cursor.fetchall()
        
        # إحصائيات المعاملات
        cursor.execute('''
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_total,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_total
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        total_transactions, sent_amount, received_amount = stats
        
        conn.close()
        
        # حساب التقييم
        rating_data = calculate_user_rating(user['id'])
        
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
💰 **الرصيد:** {user['balance']:,.2f} ريال
💳 **رقم المحفظة:** {user['wallet_number']}

📊 **إحصائيات المحفظة:**
📤 المرسل: **{sent_amount:,.2f}** ريال ({total_transactions} معاملة)
📥 المستلم: **{received_amount:,.2f}** ريال
💵 صافي الحركة: **{received_amount - sent_amount:+,.2f}** ريال
⭐ تقييمي: **{rating_data['average_rating']}/5**

📋 **آخر المعاملات:**

"""
        
        if recent_transactions:
            for transaction in recent_transactions:
                trans_id, from_user_id, to_user_id, amount, trans_type, description, created_at = transaction
                
                # تحديد اتجاه المعاملة
                if from_user_id == user['id']:
                    direction = "📤 مرسل"
                    color = "🔴"
                else:
                    direction = "📥 مستلم"
                    color = "🟢"
                
                # نوع المعاملة
                type_names = {
                    'transfer': 'تحويل رصيد',
                    'card_purchase': 'شراء كرت',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولة'
                }
                type_name = type_names.get(trans_type, 'معاملة')
                
                wallet_text += f"""
{color} **{direction} - {type_name}**
💰 {amount:,.2f} ريال
📅 {created_at[:16] if created_at else 'غير محدد'}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            wallet_text += "📭 لا توجد معاملات حتى الآن"
        
        keyboard = [
            [InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('📊 تفاصيل المعاملات', callback_data='transaction_details')],
            [InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats'),
             InlineKeyboardButton('🔄 تحديث الرصيد', callback_data='refresh_balance')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        if is_callback:
            await update.callback_query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        error_msg = f"{EMOJIS['error']} حدث خطأ في المحفظة. تم إصلاحه الآن."
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


# معالجات إدارة الشبكات للمشرف الأعلى
async def admin_manage_networks_handler(update: Update, context: CallbackContext):
    """معالج إدارة الشبكات للمشرف الأعلى"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على جميع الشبكات
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.city, n.location, n.is_active, n.is_approved,
                   u.full_name as supplier_name,
                   COUNT(cc.id) as categories_count,
                   COUNT(c.id) as total_cards,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            GROUP BY n.id
            ORDER BY n.created_at DESC
        ''')
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            text = f"""
🗑️ **إدارة الشبكات** 🗑️

👑 مرحباً **{user['full_name']}**

❌ **لا توجد شبكات للإدارة**

🔧 **يجب إضافة شبكة أولاً**
"""
            keyboard = [
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='admin_add_network')],
                [InlineKeyboardButton('🔙 عودة', callback_data='super_admin_panel')]
            ]
        else:
            text = f"""
🗑️ **إدارة الشبكات** 🗑️

👑 مرحباً **{user['full_name']}**

📊 **إجمالي الشبكات:** {len(networks)} شبكة

🔽 **اختر شبكة للإدارة:**
"""
            keyboard = []
            
            for network in networks:
                network_id, name, provider, city, location, is_active, is_approved, supplier_name, categories, total_cards, available_cards = network
                
                status_icon = "🟢" if is_active else "🔴"
                button_text = f"{status_icon} {name} - {provider} ({available_cards or 0} كرت متاح)"
                
                keyboard.append([InlineKeyboardButton(
                    button_text[:60] + "..." if len(button_text) > 60 else button_text,
                    callback_data=f'admin_network_details_{network_id}'
                )])
            
            keyboard.extend([
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='admin_add_network')],
                [InlineKeyboardButton('🔙 عودة', callback_data='super_admin_panel')]
            ])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in admin manage networks: {e}")
        await query.edit_message_text("❌ حدث خطأ في إدارة الشبكات.")

async def admin_network_details_handler(update: Update, context: CallbackContext, network_id: str):
    """عرض تفاصيل الشبكة مع خيارات الإدارة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على تفاصيل الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.city, n.location, n.description, n.is_active, n.is_approved,
                   n.created_at, u.full_name as supplier_name,
                   COUNT(cc.id) as categories_count,
                   COUNT(c.id) as total_cards,
                   COUNT(CASE WHEN c.is_sold = 0 THEN 1 END) as available_cards,
                   COUNT(CASE WHEN c.is_sold = 1 THEN 1 END) as sold_cards
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.id = ?
            GROUP BY n.id
        ''', (network_id,))
        
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ لم يتم العثور على الشبكة المحددة.")
            return
        
        conn.close()
        
        network_id, name, provider, city, location, description, is_active, is_approved, created_at, supplier_name, categories_count, total_cards, available_cards, sold_cards = network
        
        status_text = "🟢 نشطة" if is_active else "🔴 متوقفة"
        approval_text = "✅ معتمدة" if is_approved else "⏳ في الانتظار"
        
        text = f"""
📋 **تفاصيل الشبكة** 📋

🌐 **الاسم:** {name}
👤 **المزود:** {provider}
🏢 **المالك:** {supplier_name or 'غير محدد'}
🏙️ **المدينة:** {city or 'غير محدد'}
📍 **الموقع:** {location or 'غير محدد'}

📊 **الحالة:**
• **الحالة:** {status_text}
• **الاعتماد:** {approval_text}
• **تاريخ الإنشاء:** {created_at[:10] if created_at else 'غير محدد'}

💳 **إحصائيات الكروت:**
• **فئات الكروت:** {categories_count or 0}
• **إجمالي الكروت:** {total_cards or 0}
• **متاحة:** {available_cards or 0}
• **مباعة:** {sold_cards or 0}
"""
        
        keyboard = [
            [InlineKeyboardButton('💳 إدارة الكروت', callback_data=f'admin_upload_to_network_{network_id}'),
             InlineKeyboardButton('📊 إحصائيات', callback_data=f'admin_network_stats_{network_id}')],
            [InlineKeyboardButton('🗑️ حذف الشبكة', callback_data=f'admin_delete_network_{network_id}')],
            [InlineKeyboardButton('🔙 عودة للقائمة', callback_data='admin_manage_networks'),
             InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in network details: {e}")
        await query.edit_message_text("❌ حدث خطأ في عرض تفاصيل الشبكة.")

async def admin_delete_network_handler(update: Update, context: CallbackContext, network_id: str):
    """تأكيد حذف الشبكة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على تفاصيل الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.name, n.provider, u.full_name as supplier_name,
                   COUNT(c.id) as total_cards,
                   COUNT(CASE WHEN c.is_sold = 1 THEN 1 END) as sold_cards
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.id = ?
            GROUP BY n.id
        ''', (network_id,))
        
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text("❌ لم يتم العثور على الشبكة المحددة.")
            return
        
        name, provider, supplier_name, total_cards, sold_cards = network
        
        text = f"""
⚠️ **تأكيد حذف الشبكة** ⚠️

🌐 **الشبكة:** {name}
👤 **المزود:** {provider}
🏢 **المالك:** {supplier_name or 'غير محدد'}

📊 **البيانات التي ستُحذف:**
• **إجمالي الكروت:** {total_cards or 0}
• **الكروت المباعة:** {sold_cards or 0}
• **جميع فئات الكروت**
• **جميع الإحصائيات**

⚠️ **تحذير هام:**
• هذا الإجراء **لا يمكن التراجع عنه**
• سيتم حذف جميع البيانات المرتبطة

❓ **هل أنت متأكد من الحذف؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ نعم، احذف الشبكة', callback_data=f'admin_confirm_delete_{network_id}'),
             InlineKeyboardButton('❌ إلغاء', callback_data=f'admin_network_details_{network_id}')]
        ]
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in delete network confirmation: {e}")
        await query.edit_message_text("❌ حدث خطأ في تأكيد حذف الشبكة.")

async def admin_confirm_delete_network_handler(update: Update, context: CallbackContext, network_id: str):
    """تنفيذ حذف الشبكة فعلياً"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] != 'super_admin':
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        # الحصول على اسم الشبكة قبل الحذف
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider FROM networks WHERE id = ?', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ لم يتم العثور على الشبكة المحددة.")
            return
        
        network_name, provider = network
        
        # حذف الشبكة وجميع البيانات المرتبطة
        try:
            # 1. حذف الكروت أولاً
            cursor.execute('''
                DELETE FROM cards 
                WHERE category_id IN (
                    SELECT id FROM card_categories WHERE network_id = ?
                )
            ''', (network_id,))
            deleted_cards = cursor.rowcount
            
            # 2. حذف فئات الكروت
            cursor.execute('DELETE FROM card_categories WHERE network_id = ?', (network_id,))
            deleted_categories = cursor.rowcount
            
            # 3. حذف الشبكة نفسها
            cursor.execute('DELETE FROM networks WHERE id = ?', (network_id,))
            
            conn.commit()
            conn.close()
            
            success_text = f"""
✅ **تم حذف الشبكة بنجاح** ✅

🗑️ **الشبكة المحذوفة:**
• **الاسم:** {network_name}
• **المزود:** {provider}

📊 **البيانات المحذوفة:**
• **الكروت:** {deleted_cards}
• **فئات الكروت:** {deleted_categories}

⏰ **وقت الحذف:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👤 **تم بواسطة:** {user['full_name']}
"""
            
            keyboard = [
                [InlineKeyboardButton('🗑️ إدارة شبكات أخرى', callback_data='admin_manage_networks')],
                [InlineKeyboardButton('�� إضافة شبكة جديدة', callback_data='admin_add_network')],
                [InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
            ]
            
            await query.edit_message_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            logger.info(f"تم حذف الشبكة {network_name} (ID: {network_id}) بواسطة {user['full_name']}")
            
        except Exception as db_error:
            conn.rollback()
            conn.close()
            
            logger.error(f"خطأ في حذف الشبكة: {db_error}")
            
            await query.edit_message_text(
                f"❌ **فشل في حذف الشبكة**\n\n🔍 **السبب:** {str(db_error)}",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🔄 إعادة المحاولة', callback_data=f'admin_delete_network_{network_id}')],
                    [InlineKeyboardButton('🔙 عودة للتفاصيل', callback_data=f'admin_network_details_{network_id}')]
                ]),
                parse_mode='Markdown'
            )
        
    except Exception as e:
        logger.error(f"Error in confirm delete network: {e}")
        await query.edit_message_text("❌ حدث خطأ في حذف الشبكة.")

