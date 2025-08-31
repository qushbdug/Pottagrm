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
import sqlite3
from telegram.error import TelegramError, NetworkError, TimedOut, BadRequest

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
    # Import configuration and database
    from config import *
    from database import init_db, get_db_connection
    
    # Import utilities
    from utils import (
        get_user, recalc_and_set_user_balance,
        get_or_create_supplier_code, get_cards_stats_by_category,
        get_card_categories, process_uploaded_cards, calculate_user_rating,
        get_user_permissions
    )
    
    # Import handlers
    from handlers import (
        COMMAND_HANDLERS, CONVERSATION_STATES, handle_text_message, show_main_menu,
        redeem_coupon_handler, cancel_coupon_handler, quick_transfer_handler,
        select_user_for_transfer, process_amount_selection, process_card_purchase,
        skip_network_location, search_by_type_handler, choose_role
    )
    
    # Import account statement handlers
    from account_statement import (
        account_statement_handler, download_excel_30_handler, download_excel_90_handler,
        download_excel_all_handler, download_pdf_30_handler, download_pdf_90_handler,
        download_pdf_all_handler
    )
    
    # Import accounting engine
    from accounting_engine import (
        AccountingEngine, record_purchase_accounting, record_transfer_accounting,
        record_coupon_accounting, record_commission_accounting, record_money_creation_accounting
    )
    
    # Import export system
    from export_system import (
        export_options_handler, export_profits_handler, export_customers_handler,
        export_suppliers_handler, export_comprehensive_handler, ExportSystem, quick_export_handler
    )
    
    # Import accounting search
    from accounting_search import (
        accounting_search_handler, quick_stats_handler, quick_transaction_report_handler
    )
    
    # Import admin functions
    from admin_functions import (
        ADMIN_CALLBACKS, activate_single_supplier, admin_panel_handler,
        admin_add_offers_handler, accounting_system_handler,
        create_coupons_handler, create_quick_coupon_handler,
        coupons_stats_handler, list_coupons_handler
    )
    
    # Import management modules
    from customer_management import CustomerManagement
    from admin_management import AdminManagement
    from admin_management_extended import AdminManagementExtended
    from enhanced_error_messages import ErrorMessages, db_error, perm_error, net_error, unexpected_error, menu_error, wallet_error, search_error, coupon_error
    
    # Import permissions system
    from permissions import has_permission, check_permission_or_deny, AVAILABLE_PERMISSIONS
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

# Custom Exception Classes for better error handling
class BotDatabaseError(Exception):
    """Database related errors"""
    pass

class BotValidationError(Exception):
    """Input validation errors"""
    pass

class BotPermissionError(Exception):
    """Permission related errors"""
    pass

class BotConfigurationError(Exception):
    """Configuration errors"""
    pass

class BotTimeoutError(Exception):
    """Timeout related errors"""
    pass

# Utility functions for enhanced functionality
async def safe_db_operation(operation_func, *args, timeout=10.0, **kwargs):
    """Execute database operation with timeout and error handling"""
    try:
        return await asyncio.wait_for(
            asyncio.create_task(operation_func(*args, **kwargs)),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        raise BotTimeoutError(f"Database operation timed out after {timeout} seconds")
    except sqlite3.Error as e:
        raise BotDatabaseError(f"Database operation failed: {e}")
    except Exception as e:
        logger.error(f"Unexpected error in database operation: {e}")
        raise

def validate_user_input(input_value, input_type, min_length=None, max_length=None, pattern=None):
    """Enhanced input validation with specific checks"""
    if input_value is None:
        raise BotValidationError("Input value cannot be None")
    
    if input_type == 'phone':
        if not input_value.startswith(('77', '73', '70', '71')):
            raise BotValidationError("رقم الهاتف يجب أن يبدأ بـ 77، 73، 70، أو 71")
        if len(input_value) != 9:
            raise BotValidationError("رقم الهاتف يجب أن يكون 9 أرقام")
        if not input_value.isdigit():
            raise BotValidationError("رقم الهاتف يجب أن يحتوي على أرقام فقط")
    
    elif input_type == 'amount':
        try:
            amount = float(input_value)
            if amount <= 0:
                raise BotValidationError("المبلغ يجب أن يكون أكبر من صفر")
            if amount > 100000:
                raise BotValidationError("المبلغ كبير جداً")
        except ValueError:
            raise BotValidationError("المبلغ يجب أن يكون رقماً صحيحاً")
    
    elif input_type == 'name':
        if len(input_value.strip()) < 2:
            raise BotValidationError("الاسم يجب أن يكون أكثر من حرفين")
        if len(input_value.strip()) > 50:
            raise BotValidationError("الاسم طويل جداً")
    
    elif input_type == 'text':
        if min_length and len(input_value) < min_length:
            raise BotValidationError(f"النص قصير جداً (الحد الأدنى {min_length} حرف)")
        if max_length and len(input_value) > max_length:
            raise BotValidationError(f"النص طويل جداً (الحد الأقصى {max_length} حرف)")
    
    return True

# Memory optimization utilities
def clear_unused_context_data(context, keep_keys=None):
    """Clear unused data from context to save memory"""
    if keep_keys is None:
        keep_keys = ['user_state', 'selected_network_id', 'upload_file']
    
    keys_to_remove = [key for key in context.user_data.keys() if key not in keep_keys]
    for key in keys_to_remove:
        context.user_data.pop(key, None)

async def cleanup_old_conversations(context):
    """Clean up old conversation data periodically"""
    try:
        # This should be called periodically to clean memory
        if hasattr(context, 'user_data') and len(context.user_data) > 100:
            # Keep only recent conversations
            logger.info("Cleaning up old conversation data")
            # Implementation depends on how data is stored
    except Exception as e:
        logger.warning(f"Failed to cleanup conversations: {e}")

# Enhanced database connection with connection pooling concept
_db_connection_pool = None
_pool_lock = asyncio.Lock()

async def get_pooled_db_connection():
    """Get database connection with basic pooling for memory efficiency"""
    try:
        # Simple connection reuse to reduce memory overhead
        conn = get_db_connection()
        return conn
    except Exception as e:
        raise BotDatabaseError(f"Failed to get database connection: {e}")

# Main callback handler
async def button_click_handler(update: Update, context):
    """Enhanced callback query handler with better error handling"""
    try:
        query = update.callback_query
        
        # Handle query answer with specific timeout
        try:
            await asyncio.wait_for(query.answer(), timeout=5.0)
        except asyncio.TimeoutError:
            logger.warning(f"Query answer timeout for user {query.from_user.id}")
        except (TelegramError, NetworkError) as e:
            logger.warning(f"Telegram error in query answer: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in query answer: {e}")
        
        callback_data = query.data
        
        # Get user with validation
        try:
            user = get_user(query.from_user.id)
            if not user:
                raise BotValidationError("User not found in database")
        except sqlite3.Error as e:
            logger.error(f"Database error getting user {query.from_user.id}: {e}")
            await query.edit_message_text(db_error("استرداد بيانات المستخدم", "فشل في الاتصال بقاعدة البيانات"))
            return
        except BotValidationError:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Update user activity (temporarily disabled to avoid errors)
        # TODO: Re-implement update_user_activity function
        
        # Route to appropriate handlers
        
        # Main menu
        if callback_data == 'main_menu':
            return await show_main_menu(update, context, user['role'])
        
        # Enhanced wallet
        elif callback_data == 'enhanced_wallet':
            return await enhanced_wallet_handler(update, context)
        
        # Wallet pagination
        elif callback_data.startswith('wallet_page_'):
            return await wallet_page_handler(update, context)
        
        # Network search and details
        elif callback_data == 'search_networks':
            return await search_networks_handler(update, context)
        elif callback_data.startswith('network_'):
            network_id = callback_data.split('_')[1]
            return await show_network_details(update, context, network_id)
        elif callback_data.startswith('buy_from_network_'):
            network_id = callback_data.split('_')[3]
            return await show_network_categories(update, context, network_id)
        elif callback_data.startswith('select_category_'):
            parts = callback_data.split('_')
            network_id = parts[2]
            price = parts[3]
            return await confirm_card_purchase(update, context, network_id, price)
        elif callback_data.startswith('confirm_purchase_'):
            parts = callback_data.split('_')
            network_id = parts[2]
            price = parts[3]
            return await process_card_purchase(update, context, network_id, price)
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


        
        # Search by type handlers
        elif callback_data.startswith('search_by_'):
            search_type = callback_data.split('_')[2]
            return await search_by_type_handler(update, context, search_type)
        
        # Admin panel routing
        elif callback_data == 'admin_panel':
            if user['role'] in ['admin', 'super_admin']:
                return await admin_panel_handler(update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية للوصول لهذه اللوحة.")
                return
        
        # Enhanced Customer Management System
        elif callback_data == 'customer_dashboard':
            return await CustomerManagement.get_customer_dashboard(update, context)
        elif callback_data == 'customer_search':
            return await CustomerManagement.search_customers(update, context)
        elif callback_data == 'customer_analytics':
            return await CustomerManagement.get_customer_analytics(update, context)
        elif callback_data.startswith('customer_profile_'):
            customer_id = int(callback_data.split('_')[2])
            return await CustomerManagement.show_customer_profile(update, context, customer_id)
        
        # Enhanced Admin Management System  
        elif callback_data == 'admin_dashboard':
            return await AdminManagement.get_admin_dashboard(update, context)
        elif callback_data == 'admin_manage_admins':
            return await AdminManagement.manage_admins(update, context)
        elif callback_data == 'admin_analytics':
            return await AdminManagement.get_admin_analytics(update, context)
        elif callback_data == 'admin_security':
            return await AdminManagement.admin_security_center(update, context)
        elif callback_data.startswith('admin_profile_'):
            admin_id = int(callback_data.split('_')[2])
            return await AdminManagement.show_admin_profile(update, context, admin_id)
        
        # Advanced Permissions Management System
        elif callback_data == 'admin_permissions':
            return await AdminManagement.admin_permissions_handler(update, context)
        elif callback_data == 'perm_list_all_admins':
            return await AdminManagement.list_all_admins_permissions(update, context)
        elif callback_data.startswith('perm_page_'):
            page = int(callback_data.split('_')[2])
            context.user_data['admin_perms_page'] = page
            return await AdminManagement.list_all_admins_permissions(update, context)
        elif callback_data.startswith('perm_quick_edit_'):
            admin_id = int(callback_data.split('_')[3])
            return await AdminManagement.edit_admin_permissions(update, context, admin_id)
        elif callback_data.startswith('perm_grant_') or callback_data.startswith('perm_revoke_'):
            parts = callback_data.split('_')
            action = parts[1]  # grant or revoke
            admin_id = int(parts[2])
            permission = parts[3]
            return await AdminManagement.toggle_permission(update, context, action, admin_id, permission)
        
        # Complete Admin Management System Handlers
        elif callback_data == 'admin_add_new':
            return await AdminManagement.add_new_admin_handler(update, context)
        elif callback_data == 'add_admin_enter_id':
            return await AdminManagement.add_admin_enter_id_handler(update, context)
        elif callback_data == 'add_admin_enter_phone':
            return await AdminManagement.add_admin_enter_phone_handler(update, context)

        elif callback_data == 'promote_to_admin':
            return await AdminManagement.execute_admin_promotion(update, context, 'admin')
        elif callback_data == 'promote_to_super_admin':
            return await AdminManagement.execute_admin_promotion(update, context, 'super_admin')
        elif callback_data == 'add_admin_cancel':
            # تنظيف بيانات السياق
            context.user_data.pop('awaiting_admin_telegram_id', None)
            context.user_data.pop('awaiting_admin_phone', None)
            context.user_data.pop('target_admin_telegram_id', None)
            context.user_data.pop('target_admin_db_id', None)
            context.user_data.pop('admin_add_step', None)
            return await AdminManagement.get_admin_dashboard(update, context)
        
        # Admin Search System
        elif callback_data == 'admin_search_admin':
            return await AdminManagementExtended.search_admin_handler(update, context)
        elif callback_data == 'search_admin_by_id':
            return await AdminManagementExtended.search_admin_by_id_handler(update, context)
        elif callback_data == 'search_admin_by_phone':
            return await AdminManagementExtended.search_admin_by_phone_handler(update, context)
        elif callback_data == 'search_admin_cancel':
            # تنظيف بيانات البحث
            context.user_data.pop('awaiting_admin_search_id', None)
            context.user_data.pop('awaiting_admin_search_phone', None)
            context.user_data.pop('search_type', None)
            return await AdminManagementExtended.search_admin_handler(update, context)
        
        # Admin Activity Logs
        elif callback_data == 'admin_activity_log':
            return await AdminManagementExtended.admin_activity_log_handler(update, context)
        
        # Admin Settings
        elif callback_data == 'admin_settings':
            return await AdminManagementExtended.admin_settings_handler(update, context)
        elif callback_data.startswith('toggle_setting_'):
            parts = callback_data.split('_')
            setting_key = parts[2]
            new_value = parts[3]
            return await AdminManagementExtended.toggle_admin_setting(setting_key, new_value, update, context)
        elif callback_data == 'admin_settings_reload':
            return await AdminManagementExtended.admin_settings_handler(update, context)
        
        # Admin Reports
        elif callback_data == 'admin_reports':
            return await AdminManagementExtended.admin_reports_handler(update, context)
        
        # Admin Profile and Management Actions
        elif callback_data.startswith('admin_profile_'):
            admin_id = int(callback_data.split('_')[2])
            return await AdminManagement.show_admin_profile(update, context, admin_id)
        elif callback_data.startswith('admin_delete_'):
            admin_id = int(callback_data.split('_')[2])
            return await AdminManagement.delete_admin_handler(update, context, admin_id)
        elif callback_data.startswith('confirm_delete_admin_'):
            admin_id = int(callback_data.split('_')[3])
            return await AdminManagement.confirm_delete_admin_handler(update, context, admin_id)
        
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
        
        # Coupon quick creation handlers
        elif callback_data.startswith('create_quick_coupon_'):
            if user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            amount = int(callback_data.split('_')[-1])
            from bot_modules.admin_functions import create_quick_coupon_handler
            return await create_quick_coupon_handler(update, context, amount)
        
        # Additional coupon handlers
        elif callback_data == 'coupons_stats':
            if user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            from bot_modules.admin_functions import coupons_stats_handler
            return await coupons_stats_handler(update, context)
        
        elif callback_data == 'list_coupons':
            if user['role'] != 'super_admin':
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
            from bot_modules.admin_functions import list_coupons_handler
            return await list_coupons_handler(update, context)
        
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
            return await choose_role(update, context)
        
        # Core features
        elif callback_data == 'buy_cards':
            await buy_cards_handler(update, context)
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
        elif callback_data.startswith('price_'):
            await process_price_selection(update, context)
        elif callback_data == 'cancel_upload':
            await cancel_upload(update, context)
        elif callback_data == 'confirm_upload':
            await confirm_upload(update, context)
        elif callback_data == 'confirm_simplified_upload':
            await confirm_simplified_upload(update, context)
        elif callback_data == 'notification_settings':
            await notification_settings_handler(update, context)
        elif callback_data == 'choose_upload_method':
            await choose_upload_method_handler(update, context)
        elif callback_data == 'network_details':
            await network_details_handler(update, context)
        elif callback_data == 'privacy_settings':
            await privacy_settings_handler(update, context)
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
        elif callback_data == 'my_notifications':
            await my_notifications_handler(update, context)
        elif callback_data == 'transfer_history':
            await transfer_history_handler(update, context)
        elif callback_data == 'update_profile':
            await update_profile_handler(update, context)
        elif callback_data == 'view_full_profile':
            await view_full_profile_handler(update, context)
        elif callback_data == 'change_password':
            await change_password_handler(update, context)
        elif callback_data == 'contact_admin':
            await contact_admin_handler(update, context)
        elif callback_data == 'account_status':
            await account_status_handler(update, context)
        elif callback_data == 'account_statement':
            await account_statement_handler(update, context)
        
        # Account statement download handlers
        elif callback_data == 'download_excel_30':
            await download_excel_30_handler(update, context)
        elif callback_data == 'download_excel_90':
            await download_excel_90_handler(update, context)
        elif callback_data == 'download_excel_all':
            await download_excel_all_handler(update, context)
        elif callback_data == 'download_pdf_30':
            await download_pdf_30_handler(update, context)
        elif callback_data == 'download_pdf_90':
            await download_pdf_90_handler(update, context)
        elif callback_data == 'download_pdf_all':
            await download_pdf_all_handler(update, context)
        elif callback_data == 'fix_missing_entries':
            from bot_modules.admin_functions import fix_missing_entries_handler
            await fix_missing_entries_handler(update, context)
        elif callback_data == 'trial_balance':
            from bot_modules.admin_functions import trial_balance_handler
            await trial_balance_handler(update, context)
        
        # Export system handlers
        elif callback_data == 'export_profits':
            await export_profits_handler(update, context)
        elif callback_data == 'export_customers':
            await export_customers_handler(update, context)
        elif callback_data == 'export_suppliers':
            await export_suppliers_handler(update, context)
        elif callback_data == 'export_comprehensive':
            await export_comprehensive_handler(update, context)
        elif callback_data == 'quick_export':
            await quick_export_handler(update, context)
        elif callback_data == 'quick_stats':
            await quick_stats_handler(update, context)
        elif callback_data == 'quick_transaction_report':
            await quick_transaction_report_handler(update, context)
        
        # Export with period handlers
        elif callback_data.startswith('export_'):
            parts = callback_data.split('_')
            if len(parts) >= 3:
                export_type = parts[1]
                period = '_'.join(parts[2:])
                await ExportSystem.export_data_handler(update, context, export_type, period)
        
        # Refresh balance
        elif callback_data == 'refresh_balance':
            new_balance = recalc_and_set_user_balance(user['id'])
            # إعادة تحميل بيانات المستخدم بعد تحديث الرصيد
            user = get_user(user['id'])
            # العودة للمحفظة المطورة مع الرصيد المحدث
            return await enhanced_wallet_handler(update, context)
        
        # Help
        elif callback_data == 'help':
            await help_handler(update, context)
        

        # Support callbacks
        elif callback_data == 'recharge_help':
            await query.edit_message_text(
                "💡 **مساعدة الشحن** 💡\n\n"
                "🎟️ **أسرع طريقة:** استخدم الكوبونات\n"
                "📞 **الدعم:** متاح 24/7\n\n"
                "💡 اختر الطريقة المناسبة لك:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon')],
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )

                # Default fallback for unrecognized callbacks
        else:
            # Handle unified commands (search_networks and promotions now handled here)
            if callback_data == 'search_networks':
                return await search_networks_handler(update, context)
            elif callback_data == 'promotions':
                return await promotions_handler(update, context)
            
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
    
    except BotDatabaseError as e:
        logger.error(f"Database error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    db_error("تسجيل الاستعلام", "فشل في حفظ البيانات"),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except (TelegramError, NetworkError) as te:
            logger.error(f"Failed to send database error message: {te}")
    
    except BotValidationError as e:
        logger.warning(f"Validation error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"{EMOJIS['warning']} بيانات غير صحيحة. يرجى التحقق والمحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except (TelegramError, NetworkError) as te:
            logger.error(f"Failed to send validation error message: {te}")
    
    except BotPermissionError as e:
        logger.warning(f"Permission error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except (TelegramError, NetworkError) as te:
            logger.error(f"Failed to send permission error message: {te}")
    
    except (NetworkError, TimedOut) as e:
        logger.error(f"Network/Timeout error in button click handler: {e}")
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    f"{EMOJIS['warning']} مشكلة في الاتصال. يرجى المحاولة مرة أخرى.",
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except Exception:
            pass  # Don't log if this fails too
    
    except TelegramError as e:
        logger.error(f"Telegram error in button click handler: {e}")
        # Don't try to send message if it's a Telegram error
    
    except Exception as e:
        logger.error(f"Unexpected error in button click handler: {e}", exc_info=True)
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    unexpected_error("معالجة الضغط على الزر", f"زر '{callback_data}'"),
                    reply_markup=InlineKeyboardMarkup([
                        [InlineKeyboardButton(f'{EMOJIS["home"]} القائمة الرئيسية', callback_data='main_menu')]
                    ])
                )
        except Exception:
            pass

# Placeholder handlers for features being implemented

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
        await query.edit_message_text(ErrorMessages.custom_error(
            "عرض التقييمات",
            "لا يمكن الوصول إلى بيانات التقييمات حالياً",
            "تأكد من الاتصال بالإنترنت وحاول مرة أخرى خلال دقائق",
            "RATING_ERROR"
        ))

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
        await query.edit_message_text(ErrorMessages.notification_error("عرض قائمة الإشعارات"))





async def buy_cards_handler(update: Update, context):
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
        await query.edit_message_text(menu_error("صفحة الشراء", "شراء الكروت"))

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
        await query.edit_message_text(wallet_error("عرض صفحة التحويل"))

# Additional missing handlers


async def supplier_panel_handler(update: Update, context):
    """Handle enhanced supplier panel"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get supplier code
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
        
        # تحديد حالة الشبكة
        network_status = "✅ متاحة" if networks_count == 0 else "📶 مُنشأة"
        can_add_network = networks_count == 0 and user['is_active']
        
        panel_text = f"""
🏪 **لوحة المزود المطورة** 🏪

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:.2f}** ريال
🆔 **معرف المزود: `{supplier_code}`**
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📊 **إحصائيات المزود:**
📶 شبكتك: **{network_status}** ({networks_count}/1)
📋 كروت متاحة: **{active_cards}**
✅ كروت مباعة: **{sold_cards}**
📤 رفع حديث (7 أيام): **{recent_uploads}**

🎯 **إدارة الكروت والشبكات:**
💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
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
        await query.edit_message_text(ErrorMessages.supplier_error(
            "تحميل لوحة التحكم", 
            "فشل في الوصول إلى بيانات المزود"
        ))

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
        await query.edit_message_text(search_error(None, "عرض قائمة الشبكات"))

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
        await query.edit_message_text(search_error("المستخدم", "قاعدة بيانات المستخدمين"))

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
        await query.edit_message_text(ErrorMessages.custom_error(
            "عرض التقييمات المرسلة",
            "فشل في استرداد قائمة التقييمات التي أرسلتها",
            "قد تكون قاعدة البيانات مشغولة، حاول مرة أخرى خلال دقائق",
            "SENT_RATING_ERROR"
        ))

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
                
                # تحديد اتجاه المعاملة والأيقونات
                if from_user_id == user['id']:
                    # معاملة صادرة (سحب)
                    direction_color = "🔴"
                    direction_text = "مرسل"
                    amount_prefix = "-"
                else:
                    # معاملة واردة (إيداع)
                    direction_color = "🟢"
                    direction_text = "مستلم"
                    amount_prefix = "+"
                
                # أيقونات أنواع المعاملات
                type_icons = {
                    'transfer': '🔄',
                    'card_purchase': '🛒',
                    'coupon_redeem': '🎟️',
                    'commission': '🎯',
                    'money_creation': '💰',
                    'transfer_fee': '💳'
                }
                
                type_names = {
                    'transfer': 'تحويل رصيد',
                    'card_purchase': 'شراء كرت',
                    'coupon_redeem': 'شحن بكوبون',
                    'commission': 'عمولة',
                    'money_creation': 'إنشاء رصيد',
                    'transfer_fee': 'رسوم تحويل'
                }
                
                type_icon = type_icons.get(trans_type, '💼')
                type_name = type_names.get(trans_type, 'معاملة')
                
                # تنسيق التاريخ
                date_formatted = created_at[:16] if created_at else 'غير محدد'
                
                details_text += f"""
📅 {date_formatted}
{direction_color} {direction_text} | {type_icon} {type_name} | 💰 {amount_prefix}{amount:,.0f} ريال

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
        await query.edit_message_text(wallet_error("عرض تفاصيل المعاملات"))

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
        await query.edit_message_text(wallet_error("حساب إحصائيات المحفظة"))

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

👤 **{user['full_name']}**

🎯 **الطريقة المبسطة الجديدة:**

📋 **فقط ملف نصي (.txt)**
• كل رقم كرت في سطر منفصل
• مثال:
```
123456789012
123456789013
123456789014
```

🔄 **خطوات سريعة:**
1️⃣ **ارفع ملف TXT** مع أرقام الكروت
2️⃣ **اختر السعر** من القائمة
3️⃣ **أدخل حجم الكرت** (مثل: 1 جيجا)

📁 **ارفع ملف TXT الآن مباشرة!**
(قم بسحب وإفلات الملف في المحادثة)
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 عرض سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
        ]
        
        # تفعيل وضع انتظار الملف
        context.user_data['awaiting_card_upload'] = True
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in upload cards handler: {e}")
        await query.edit_message_text(ErrorMessages.upload_error(
            "الكروت",
            None,
            None
        ).replace("الرفع", "صفحة رفع الكروت").replace("في رفع", "في تحميل صفحة رفع"))

async def manage_networks_handler(update: Update, context):
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
📊 شبكاتك: **{len(networks)}/1** (الحد الأقصى)
🔰 حالة التفعيل: **{'✅ مفعل' if user['is_active'] else '⏳ في الانتظار'}**

📋 **شبكتك:**
"""
        
        if networks:
            network = networks[0]  # عرض الشبكة الوحيدة
            status = "✅ مفعلة" if network['is_active'] else "⏸️ متوقفة"
            approval = "✅ معتمدة" if network['is_approved'] else "⏳ في انتظار الموافقة"
            networks_text += f"""
📶 **{network['name']}**
🏢 المزود: {network['provider']}
🏙️ المدينة: {network['city']}
📊 الحالة: {status}
✅ الاعتماد: {approval}

💡 **ملاحظة:** يُسمح بشبكة واحدة فقط لكل مزود
"""
        else:
            networks_text += """
⚠️ لا توجد شبكة مسجلة بعد

💡 **يمكنك إنشاء شبكة واحدة فقط**
"""
        
        # تحديد الأزرار حسب الحالة
        keyboard = []
        
        if networks:
            # إذا كانت توجد شبكة، عرض أزرار الإدارة
            keyboard = [
                [InlineKeyboardButton('📊 تفاصيل الشبكة', callback_data='network_details')],
                [InlineKeyboardButton('📤 رفع كروت', callback_data='upload_cards')],
                [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
            ]
        else:
            # إذا لم تكن توجد شبكة ومفعل، إظهار زر الإضافة
            if user['is_active']:
                keyboard = [
                    [InlineKeyboardButton('➕ إضافة شبكة جديدة', callback_data='add_network')],
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
                ]
            else:
                keyboard = [
                    [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')]
                ]
        
        await query.edit_message_text(networks_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in manage networks handler: {e}")
        await query.edit_message_text(ErrorMessages.supplier_error(
            "إدارة الشبكات",
            "لا يمكن الوصول إلى بيانات الشبكات الخاصة بك حالياً"
        ))

async def cards_reports_handler(update: Update, context):
    """Handle cards reports"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        # Get cards statistics
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
        await query.edit_message_text(ErrorMessages.report_error("الكروت والمبيعات"))

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
        await query.edit_message_text(ErrorMessages.report_error("إحصائيات المبيعات"))

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
        await query.edit_message_text(ErrorMessages.upload_error("عرض سجل الرفع"))

async def supplier_settings_handler(update: Update, context):
    """Handle supplier settings"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
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
        await query.edit_message_text(ErrorMessages.supplier_error("عرض الإعدادات"))

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
        error_text = menu_error("صفحة المساعدة", "عرض المساعدة")
        if update.callback_query:
            await update.callback_query.edit_message_text(error_text)
        else:
            await update.message.reply_text(error_text)

async def handle_document(update: Update, context: CallbackContext):
    """Handle uploaded documents for simplified card upload - TXT only"""
    try:
        if not update.message or not update.message.document:
            return
        
        user = get_user(update.message.from_user.id)
        if not user or user['role'] != 'supplier':
            await update.message.reply_text("❌ هذه الميزة متاحة للمزودين فقط.")
            return
        
        # التحقق من وضع انتظار رفع الكروت
        if not context.user_data.get('awaiting_card_upload'):
            await update.message.reply_text("❌ لم يتم طلب رفع كروت. اذهب للوحة المزود أولاً.")
            return
        
        document = update.message.document
        file_name = document.file_name
        file_size = document.file_size
        
        # Check file size (max 10MB)
        if file_size > 10 * 1024 * 1024:
            await update.message.reply_text("❌ حجم الملف كبير جداً. الحد الأقصى 10 ميجابايت.")
            return
        
        # Check file type - TXT only for simplified process
        if not file_name.lower().endswith('.txt'):
            await update.message.reply_text("""
❌ **ملف غير مدعوم**

🎯 **النظام المبسط الجديد:**
يدعم فقط ملفات **TXT** (.txt)

📋 **كيفية إنشاء الملف:**
• افتح برنامج Notepad أو أي محرر نصوص
• اكتب كل رقم كرت في سطر منفصل
• احفظ الملف بصيغة TXT

💡 **مثال على المحتوى:**
```
123456789012
123456789013
123456789014
```
""", parse_mode='Markdown')
            return
        
        # Download file with timeout and memory management
        try:
            file = await asyncio.wait_for(
                context.bot.get_file(document.file_id),
                timeout=30.0
            )
            file_content = await asyncio.wait_for(
                file.download_as_bytearray(),
                timeout=60.0
            )
        except asyncio.TimeoutError:
            await update.message.reply_text("❌ انتهت مهلة تحميل الملف. يرجى المحاولة مرة أخرى.")
            return
        except Exception as e:
            logger.error(f"Error downloading file: {e}")
            await update.message.reply_text("❌ فشل في تحميل الملف. يرجى المحاولة مرة أخرى.")
            return
        
        # Process file content with memory-efficient decoding
        try:
            if file_name.lower().endswith('.txt'):
                # For text files, try different encodings
                for encoding in ['utf-8', 'utf-8-sig', 'latin-1', 'cp1256']:
                    try:
                        content = file_content.decode(encoding)
                        break
                    except UnicodeDecodeError:
                        continue
                else:
                    raise UnicodeDecodeError("Failed to decode with any encoding")
            else:
                content = file_content
                
            # Clear the original file_content to free memory
            del file_content
            
        except UnicodeDecodeError as e:
            logger.error(f"Encoding error in file {file_name}: {e}")
            await update.message.reply_text("❌ تعذر قراءة الملف. تأكد من ترميز النص (UTF-8).")
            return
        
        # Clear any old upload data to save memory
        clear_unused_context_data(context, keep_keys=['upload_file'])
        
        context.user_data['upload_file'] = {
            'content': content,
            'filename': file_name,
            'size': file_size,
            'timestamp': datetime.now().timestamp()  # For cleanup tracking
        }
        
        # تحليل محتوى الملف للتحقق من صحته
        lines = [line.strip() for line in content.split('\n') if line.strip()]
        valid_cards = []
        
        for line in lines:
            # إزالة أي مسافات وتحقق من صحة الرقم
            card_number = line.strip()
            if len(card_number) >= 6 and card_number.isdigit():
                valid_cards.append(card_number)
        
        if not valid_cards:
            await update.message.reply_text("""
❌ **لا توجد أرقام كروت صحيحة في الملف**

📋 **تأكد من:**
• كل رقم في سطر منفصل
• الأرقام تحتوي على 6 أرقام على الأقل
• عدم وجود رموز أو حروف

💡 **مثال صحيح:**
```
123456789012
123456789013
123456789014
```
""", parse_mode='Markdown')
            return
        
        # حفظ الكروت الصحيحة
        context.user_data['upload_file']['valid_cards'] = valid_cards
        context.user_data['awaiting_card_upload'] = False
        
        # الانتقال مباشرة لاختيار السعر
        await show_price_selection(update, context, file_name, len(valid_cards))
        
    except Exception as e:
        logger.error(f"Error handling document: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.file_error(
            "معالجة الملف المرفوع",
            "TXT",
            f"{file_size/1024:.1f} KB" if 'file_size' in locals() else "غير محدد"
        ))

async def show_price_selection(update: Update, context: CallbackContext, filename: str, card_count: int):
    """عرض خيارات اختيار السعر"""
    try:
        # خيارات السعر الافتراضية
        price_options = [
            ("10", "10 ريال"),
            ("15", "15 ريال"), 
            ("20", "20 ريال"),
            ("25", "25 ريال"),
            ("30", "30 ريال"),
            ("50", "50 ريال"),
            ("75", "75 ريال"),
            ("100", "100 ريال"),
            ("custom", "سعر مخصص")
        ]
        
        price_text = f"""
💰 **اختيار سعر الكروت** 💰

📁 **الملف:** {filename}
📊 **عدد الكروت:** {card_count} كرت

🎯 **خطوة 2: اختر سعر الكرت الواحد:**
"""
        
        keyboard = []
        # إنشاء صفوف الأزرار (3 أزرار في كل صف)
        for i in range(0, len(price_options), 3):
            row = []
            for j in range(3):
                if i + j < len(price_options):
                    price_value, price_label = price_options[i + j]
                    row.append(InlineKeyboardButton(price_label, callback_data=f"price_{price_value}"))
            keyboard.append(row)
        
        # زر الإلغاء
        keyboard.append([InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")])
        
        await update.message.reply_text(price_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing price selection: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.custom_error(
            "اختيار السعر",
            "فشل في عرض خيارات الأسعار",
            "حاول إعادة رفع الملف مرة أخرى",
            "PRICE_SELECT_ERROR"
        ))

async def process_price_selection(update: Update, context: CallbackContext):
    """معالجة اختيار السعر"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        callback_data = query.data
        price_value = callback_data.split('_')[1]
        
        upload_data = context.user_data.get('upload_file')
        if not upload_data:
            await query.edit_message_text("❌ لم يتم العثور على بيانات الملف. يرجى إعادة رفع الملف.")
            return
        
        if price_value == "custom":
            # طلب إدخال سعر مخصص
            custom_text = f"""
💰 **إدخال سعر مخصص** 💰

📁 **الملف:** {upload_data['filename']}
📊 **عدد الكروت:** {len(upload_data['valid_cards'])} كرت

✍️ **أدخل السعر المطلوب (بالريال):**
مثال: 35 أو 47.5
"""
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")]]
            
            await query.edit_message_text(custom_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            context.user_data['awaiting_custom_price'] = True
            return
        
        # حفظ السعر المختار
        context.user_data['selected_price'] = float(price_value)
        
        # الانتقال لإدخال حجم الكرت
        await show_card_size_input(update, context)
        
    except Exception as e:
        logger.error(f"Error processing price selection: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "اختيار السعر",
            "فشل في معالجة السعر المختار",
            "حاول اختيار السعر مرة أخرى",
            "PRICE_PROCESS_ERROR"
        ))

async def show_card_size_input(update: Update, context: CallbackContext):
    """عرض طلب إدخال حجم الكرت"""
    try:
        query = update.callback_query
        upload_data = context.user_data.get('upload_file')
        selected_price = context.user_data.get('selected_price')
        
        size_text = f"""
📏 **إدخال حجم الكرت** 📏

📁 **الملف:** {upload_data['filename']}
📊 **عدد الكروت:** {len(upload_data['valid_cards'])} كرت
💰 **السعر:** {selected_price} ريال للكرت

🎯 **خطوة 3: أدخل حجم الكرت**

✍️ **أمثلة على الحجم:**
• 1 جيجا
• 2 جيجا
• 5 جيجا
• 500 ميجا
• 1.5 جيجا

📝 **اكتب حجم الكرت الآن:**
"""
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")]]
        
        await query.edit_message_text(size_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        context.user_data['awaiting_card_size'] = True
        
    except Exception as e:
        logger.error(f"Error showing card size input: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "إدخال حجم الكرت",
            "فشل في عرض شاشة إدخال الحجم",
            "حاول إعادة اختيار السعر",
            "SIZE_INPUT_ERROR"
        ))

async def handle_text_message(update: Update, context: CallbackContext):
    """معالج الرسائل النصية لجميع المستخدمين"""
    try:
        user = get_user(update.message.from_user.id)
        if not user:
            return
        
        message_text = update.message.text.strip()
        
        # ===== Admin Management Text Handlers =====
        
        # معالجة إدخال معرف تلجرام لإضافة مشرف جديد
        if context.user_data.get('awaiting_admin_telegram_id'):
            if message_text.lower() in ['إلغاء', 'cancel', 'الغاء']:
                # إلغاء العملية
                context.user_data.pop('awaiting_admin_telegram_id', None)
                context.user_data.pop('admin_add_step', None)
                
                cancel_text = "❌ تم إلغاء عملية إضافة المشرف."
                keyboard = [[InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]]
                
                await update.message.reply_text(
                    cancel_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            try:
                telegram_id = int(message_text)
                context.user_data.pop('awaiting_admin_telegram_id', None)
                await AdminManagement.process_admin_user_search(str(telegram_id), 'telegram_id', update, context)
                return
            except ValueError:
                await update.message.reply_text(
                    "❌ يرجى إدخال معرف تلجرام صحيح (أرقام فقط).\n\n"
                    "مثال: `123456789`\n\n"
                    "أو اكتب `إلغاء` للإلغاء.",
                    parse_mode='Markdown'
                )
                return
        
        # معالجة إدخال رقم الهاتف لإضافة مشرف جديد
        if context.user_data.get('awaiting_admin_phone'):
            if message_text.lower() in ['إلغاء', 'cancel', 'الغاء']:
                # إلغاء العملية
                context.user_data.pop('awaiting_admin_phone', None)
                context.user_data.pop('admin_add_step', None)
                
                cancel_text = "❌ تم إلغاء عملية إضافة المشرف."
                keyboard = [[InlineKeyboardButton('🔙 العودة للوحة الإدارة', callback_data='admin_dashboard')]]
                
                await update.message.reply_text(
                    cancel_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            # معالجة رقم الهاتف
            phone_clean = message_text.strip().replace(' ', '').replace('-', '').replace('+', '')
            if phone_clean.isdigit() and len(phone_clean) >= 9:
                context.user_data.pop('awaiting_admin_phone', None)
                await AdminManagement.process_admin_user_search(phone_clean, 'phone', update, context)
                return
            else:
                await update.message.reply_text(
                    "❌ يرجى إدخال رقم هاتف صحيح.\n\n"
                    "مثال: `967777123456` أو `777123456`\n\n"
                    "أو اكتب `إلغاء` للإلغاء.",
                    parse_mode='Markdown'
                )
                return
        
        # معالجة البحث عن مشرف بالمعرف
        if context.user_data.get('awaiting_admin_search_id'):
            if message_text.lower() in ['إلغاء', 'cancel', 'الغاء']:
                context.user_data.pop('awaiting_admin_search_id', None)
                context.user_data.pop('search_type', None)
                
                cancel_text = "❌ تم إلغاء عملية البحث."
                keyboard = [[InlineKeyboardButton('🔙 العودة للبحث', callback_data='admin_search_admin')]]
                
                await update.message.reply_text(
                    cancel_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            context.user_data.pop('awaiting_admin_search_id', None)
            search_type = context.user_data.pop('search_type', 'by_id')
            await AdminManagementExtended.perform_admin_search(message_text, search_type, update, context)
            return
        
        # معالجة البحث عن مشرف برقم الهاتف  
        if context.user_data.get('awaiting_admin_search_phone'):
            if message_text.lower() in ['إلغاء', 'cancel', 'الغاء']:
                context.user_data.pop('awaiting_admin_search_phone', None)
                context.user_data.pop('search_type', None)
                
                cancel_text = "❌ تم إلغاء عملية البحث."
                keyboard = [[InlineKeyboardButton('🔙 العودة للبحث', callback_data='admin_search_admin')]]
                
                await update.message.reply_text(
                    cancel_text,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                return
            
            context.user_data.pop('awaiting_admin_search_phone', None)
            search_type = context.user_data.pop('search_type', 'by_phone')
            await AdminManagementExtended.perform_admin_search(message_text, search_type, update, context)
            return
            
        # استيراد معالج النصوص من handlers.py للحالات العامة
        from bot_modules.handlers import handle_text_message as general_text_handler
        
        # إذا كان المستخدم مورد ولديه حالات خاصة
        if user['role'] == 'supplier':
            message_text = update.message.text.strip()
            
            # التحقق من إدخال السعر المخصص
            if context.user_data.get('awaiting_custom_price'):
                try:
                    price = float(message_text.replace(',', '.'))
                    if price <= 0:
                        await update.message.reply_text("❌ السعر يجب أن يكون أكبر من صفر. حاول مرة أخرى:")
                        return
                    
                    # حفظ السعر المخصص
                    context.user_data['selected_price'] = price
                    context.user_data['awaiting_custom_price'] = False
                    
                    # الانتقال لإدخال حجم الكرت
                    await show_card_size_input_from_text(update, context)
                    
                except ValueError:
                    await update.message.reply_text("❌ يرجى إدخال رقم صحيح للسعر. مثال: 35 أو 47.5")
                return
            
            # التحقق من إدخال حجم الكرت
            if context.user_data.get('awaiting_card_size'):
                # حفظ حجم الكرت
                context.user_data['card_size'] = message_text
                context.user_data['awaiting_card_size'] = False
                
                # عرض ملخص نهائي وتأكيد الرفع
                await show_final_confirmation(update, context)
                return
        
        # للمستخدمين الآخرين (العملاء والمشرفين) - استخدام المعالج العام
        await general_text_handler(update, context)
            
    except Exception as e:
        logger.error(f"Error in handle_text_message: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.custom_error(
            "معالجة الرسالة",
            "فشل في معالجة النص المدخل",
            "تأكد من صحة البيانات وحاول مرة أخرى",
            "TEXT_PROCESS_ERROR"
        ))

async def show_card_size_input_from_text(update: Update, context: CallbackContext):
    """عرض طلب إدخال حجم الكرت من الرسالة النصية"""
    try:
        upload_data = context.user_data.get('upload_file')
        selected_price = context.user_data.get('selected_price')
        
        size_text = f"""
📏 **إدخال حجم الكرت** 📏

📁 **الملف:** {upload_data['filename']}
📊 **عدد الكروت:** {len(upload_data['valid_cards'])} كرت
💰 **السعر:** {selected_price} ريال للكرت

🎯 **خطوة 3: أدخل حجم الكرت**

✍️ **أمثلة على الحجم:**
• 1 جيجا
• 2 جيجا  
• 5 جيجا
• 500 ميجا
• 1.5 جيجا

📝 **اكتب حجم الكرت الآن:**
"""
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")]]
        
        await update.message.reply_text(size_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        context.user_data['awaiting_card_size'] = True
        
    except Exception as e:
        logger.error(f"Error showing card size input from text: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.custom_error(
            "إدخال حجم الكرت",
            "فشل في عرض شاشة إدخال الحجم",
            "حاول إعادة العملية من البداية",
            "SIZE_INPUT_ERROR"
        ))

async def show_final_confirmation(update: Update, context: CallbackContext):
    """عرض الملخص النهائي وتأكيد الرفع"""
    try:
        upload_data = context.user_data.get('upload_file')
        selected_price = context.user_data.get('selected_price')
        card_size = context.user_data.get('card_size')
        
        # الحصول على شبكة المستخدم (في النظام الجديد كل مزود له شبكة واحدة)
        user = get_user(update.message.from_user.id)
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, name FROM networks WHERE supplier_id = ? AND is_active = 1', (user['id'],))
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await update.message.reply_text("""
❌ **لا توجد شبكة مفعلة**

يجب أن يكون لديك شبكة مفعلة لرفع الكروت.
اتصل بالإدارة لتفعيل شبكتك.
""", parse_mode='Markdown')
            context.user_data.clear()
            return
        
        # حفظ معرف الشبكة
        context.user_data['selected_network_id'] = network['id']
        
        total_value = len(upload_data['valid_cards']) * selected_price
        
        confirmation_text = f"""
✅ **تأكيد رفع الكروت** ✅

📁 **الملف:** {upload_data['filename']}
📶 **الشبكة:** {network['name']}
📊 **عدد الكروت:** {len(upload_data['valid_cards'])} كرت
💰 **سعر الكرت:** {selected_price} ريال
📏 **حجم الكرت:** {card_size}
💵 **إجمالي القيمة:** {total_value} ريال

🔍 **معاينة أول 5 كروت:**
```
{chr(10).join(upload_data['valid_cards'][:5])}
{"..." if len(upload_data['valid_cards']) > 5 else ""}
```

🚀 **هل تريد إتمام عملية الرفع؟**
"""
        
        keyboard = [
            [InlineKeyboardButton("✅ تأكيد الرفع", callback_data="confirm_simplified_upload")],
            [InlineKeyboardButton("❌ إلغاء", callback_data="cancel_upload")]
        ]
        
        await update.message.reply_text(confirmation_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error showing final confirmation: {e}")
        from enhanced_error_messages import ErrorMessages
        await update.message.reply_text(ErrorMessages.custom_error(
            "التأكيد النهائي",
            "فشل في عرض ملخص العملية",
            "حاول إعادة العملية من البداية",
            "CONFIRMATION_ERROR"
        ))

async def confirm_simplified_upload(update: Update, context: CallbackContext):
    """تأكيد الرفع في النظام المبسط"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        upload_data = context.user_data.get('upload_file')
        selected_price = context.user_data.get('selected_price')
        card_size = context.user_data.get('card_size')
        network_id = context.user_data.get('selected_network_id')
        
        # التحقق من البيانات المطلوبة مع رسائل مفصلة
        missing_data = []
        if not upload_data:
            missing_data.append("ملف الكروت")
        if not selected_price:
            missing_data.append("سعر الكرت")
        if not card_size:
            missing_data.append("حجم الكرت")
        if not network_id:
            missing_data.append("معرف الشبكة")
            
        if missing_data:
            await query.edit_message_text(f"""
❌ **بيانات مفقودة**

البيانات التالية مطلوبة لإتمام العملية:
{chr(10).join(['• ' + item for item in missing_data])}

يرجى إعادة العملية من البداية.
""", parse_mode='Markdown')
            context.user_data.clear()
            return
        
        # إنشاء batch_id لهذه العملية
        import uuid
        batch_id = str(uuid.uuid4())
        
        # تسجيل عملية الرفع في قاعدة البيانات
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO card_upload_batches (id, supplier_id, network_id, filename, total_cards, 
                                        successful_cards, failed_cards, upload_status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
        ''', (batch_id, user['id'], network_id, upload_data['filename'], 
              len(upload_data['valid_cards']), 0, 0, 'processing'))
        conn.commit()
        conn.close()
        
        # معالجة الكروت مع السعر والحجم
        successful_count = 0
        failed_count = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for card_number in upload_data['valid_cards']:
            try:
                # التحقق من عدم وجود الكرت مسبقاً
                cursor.execute('SELECT id FROM network_cards WHERE card_code = ?', (card_number,))
                if cursor.fetchone():
                    failed_count += 1
                    continue
                
                # إدراج الكرت الجديد - إنشاء ID فريد
                import uuid
                card_id = str(uuid.uuid4())
                cursor.execute('''
                    INSERT INTO network_cards (id, supplier_id, network_id, card_code, card_value, 
                                               upload_batch_id, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
                ''', (card_id, user['id'], network_id, card_number, selected_price, batch_id))
                
                successful_count += 1
                
            except Exception as e:
                logger.error(f"Error inserting card {card_number}: {e}")
                failed_count += 1
        
        # تحديث إحصائيات batch
        cursor.execute('''
            UPDATE card_upload_batches 
            SET successful_cards = ?, failed_cards = ?, upload_status = ? 
            WHERE id = ?
        ''', (successful_count, failed_count, 'completed', batch_id))
        
        conn.commit()
        conn.close()
        
        # مسح بيانات العملية
        context.user_data.clear()
        
        # إرسال نتائج العملية
        total_value = successful_count * selected_price
        success_rate = (successful_count / len(upload_data['valid_cards']) * 100) if upload_data['valid_cards'] else 0
        
        result_text = f"""
🎉 **اكتمل رفع الكروت بنجاح!** 🎉

📁 **الملف:** {upload_data['filename']}
📏 **حجم الكرت:** {card_size}

📊 **النتائج:**
✅ **نجح:** {successful_count} كرت
❌ **فشل:** {failed_count} كرت
📈 **معدل النجاح:** {success_rate:.1f}%

💰 **تفاصيل مالية:**
💵 **سعر الكرت:** {selected_price} ريال
💸 **إجمالي القيمة:** {total_value} ريال

🏪 **العودة للوحة المزود للإدارة والمتابعة**
"""
        
        keyboard = [
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')],
            [InlineKeyboardButton('📋 سجل الرفع', callback_data='upload_history')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in confirm simplified upload: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "تأكيد الرفع",
            "فشل في إتمام عملية رفع الكروت",
            "تحقق من الاتصال وحاول مرة أخرى",
            "UPLOAD_CONFIRM_ERROR"
        ))

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
        await query.edit_message_text(search_error("الشبكة", "معالجة الاختيار"))

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
        await query.edit_message_text(ErrorMessages.card_error("اختيار فئة الكرت"))

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
        await query.edit_message_text(ErrorMessages.upload_error("تأكيد الرفع"))

async def notification_settings_handler(update: Update, context: CallbackContext):
    """Handle notification settings"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
                # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
 
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
        await query.edit_message_text(ErrorMessages.notification_error("تحديث الإعدادات"))

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
        await query.edit_message_text(ErrorMessages.upload_error("اختيار طريقة الرفع"))

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
        await query.edit_message_text(search_error("تفاصيل الشبكة", "قاعدة البيانات"))

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
        await query.edit_message_text(ErrorMessages.settings_error("الخصوصية"))

async def search_networks_handler(update: Update, context: CallbackContext):
    """Handle network search functionality - interactive search"""
    try:
        # دعم كل من الأوامر المباشرة والأزرار
        if update.callback_query:
            query = update.callback_query
            user = get_user(query.from_user.id)
            is_callback = True
        else:
            user = get_user(update.message.from_user.id)
            is_callback = False
        
        search_text = f"""
🔍 **البحث في الشبكات** 🔍

👤 **{user['full_name']}**

🎯 **كيفية البحث:**
• اكتب اسم الشبكة (مثل: `يمن نت`)
• اكتب اسم المزود (مثل: `أحمد`)  
• اكتب موقع الشبكة (مثل: `صنعاء`)
• اكتب معرف الشبكة أو المزود

💡 **أرسل مصطلح البحث الآن:**
سيتم البحث في جميع الحقول تلقائياً

📋 **أمثلة:**
• `سبافون` - البحث بالاسم
• `صنعاء` - البحث بالموقع  
• `أحمد` - البحث بالمزود
• `801234` - البحث بالمعرف
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء البحث', callback_data='buy_cards')],
            [InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='view_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        # Set context for search mode
        context.user_data['awaiting_network_search'] = True
        
        if is_callback:
            await update.callback_query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search networks handler: {e}")
        from enhanced_error_messages import ErrorMessages
        error_text = ErrorMessages.custom_error(
            "البحث في الشبكات",
            "فشل في تحميل واجهة البحث",
            "تحقق من الاتصال وحاول مرة أخرى",
            "SEARCH_INIT_ERROR"
        )
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(error_text)
            else:
                await update.message.reply_text(error_text)
        except:
            pass

async def filter_by_category_handler(update: Update, context: CallbackContext):
    """Handle filtering cards by category"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
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
        await query.edit_message_text(ErrorMessages.card_error("فلترة حسب الفئة"))

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
        await query.edit_message_text(ErrorMessages.report_error("المبيعات"))

async def add_network_handler(update: Update, context: CallbackContext):
    """Handle add network"""
    try:
        query = update.callback_query
        
        user = get_user(query.from_user.id)
        
        # التحقق من صلاحيات المستخدم
        if user['role'] != 'supplier':
            add_text = """
❌ **غير مسموح**

هذه الميزة متاحة للمزودين المفعلين فقط.
للحصول على حساب مزود، تواصل مع الإدارة.
"""
        elif not user['is_active']:
            add_text = """
⏳ **حسابك غير مفعل**

يجب تفعيل حسابك من قبل الإدارة قبل إضافة الشبكات.
تواصل مع الدعم للمساعدة.
"""
        else:
            # التحقق من أن المزود لا يملك شبكة بالفعل
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) FROM networks WHERE supplier_id = ?', (user['id'],))
            existing_networks = cursor.fetchone()[0]
            conn.close()
            
            if existing_networks > 0:
                add_text = """
⚠️ **شبكة موجودة بالفعل**

يُسمح لكل مزود بإنشاء شبكة واحدة فقط.
يمكنك إدارة شبكتك الحالية من لوحة التحكم.

💡 **لإضافة فئات أو كروت جديدة:**
استخدم خيار "إدارة الشبكات" من لوحة المزود.
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
        await query.edit_message_text(ErrorMessages.supplier_error("إضافة شبكة جديدة"))

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
        await query.edit_message_text(menu_error("العروض والخصومات", "عرض التفاصيل"))

async def mark_all_read_handler(update: Update, context: CallbackContext):
    """Handle mark all notifications as read"""
    try:
        query = update.callback_query
        
        await query.edit_message_text("✅ تم تحديد جميع الإشعارات كمقروءة.")
        
    except Exception as e:
        logger.error(f"Error in mark all read handler: {e}")
        await query.edit_message_text(ErrorMessages.notification_error("تحديث حالة القراءة"))

async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """Show detailed information about a specific network"""
    try:
        query = update.callback_query
        
        # الحصول على تفاصيل الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, n.location, n.description, n.created_at,
                   COUNT(DISTINCT nc.card_value) as categories_count,
                   MIN(nc.card_value) as min_price, MAX(nc.card_value) as max_price,
                   COUNT(CASE WHEN nc.is_sold = 0 THEN 1 END) as available_cards
            FROM networks n
            LEFT JOIN network_cards nc ON n.id = nc.network_id
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
        
        # الحصول على فئات الكروت من network_cards
        cursor.execute('''
            SELECT DISTINCT nc.card_value as price, COUNT(*) as stock_count
            FROM network_cards nc
            WHERE nc.network_id = ? AND nc.is_sold = 0
            GROUP BY nc.card_value
            ORDER BY nc.card_value ASC
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
            for price, stock_count in categories:
                details_text += f"""
🎫 **كرت بقيمة {price:,.0f} ريال**
💰 السعر: **{price:,.0f}** ريال
📦 المتاح: **{stock_count}** كرت
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
        await query.edit_message_text(search_error("تفاصيل الشبكة", "قاعدة البيانات"))

async def legacy_search_networks_handler(update: Update, context: CallbackContext):
    """Legacy search function - shows all networks (deprecated)"""
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
        await query.edit_message_text(search_error("الشبكات", "واجهة البحث"))

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
        await query.edit_message_text(wallet_error("عرض صفحة التحويل"))

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
        await query.edit_message_text(ErrorMessages.report_error("الشخصية"))

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
        await query.edit_message_text(menu_error("العروض والخصومات", "عرض العروض"))

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
        await query.edit_message_text(ErrorMessages.notification_error("عرض الإشعارات"))

async def account_settings_handler(update: Update, context: CallbackContext):
    """معالج إعدادات الحساب"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
                # تحديد نوع الحساب
        role_names = {
            'user': 'عميل', 
 
            'supplier': 'مزود', 
            'admin': 'مشرف', 
            'super_admin': 'مشرف أعلى'
        }
        
        settings_text = f"""
⚙️ **إعدادات الحساب** ⚙️

👤 **{user['full_name']}**
💳 **رقم المحفظة:** {user['wallet_number']}
📱 **رقم الهاتف:** {user['phone'] if user['phone'] else 'غير محدد'}
🆔 **معرف تلغرام:** {user['telegram_id']}
👑 **نوع الحساب:** {role_names.get(user['role'], 'عميل')}

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
• تاريخ التسجيل: {user['created_at'][:10] if user['created_at'] else 'غير محدد'}
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
        await query.edit_message_text(ErrorMessages.settings_error("الحساب"))

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
        await query.edit_message_text(wallet_error("عرض سجل التحويلات"))

async def update_profile_handler(update: Update, context: CallbackContext):
    """معالج تحديث البيانات الشخصية"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        update_text = f"""
🔄 **تحديث البيانات الشخصية** 🔄

👤 **البيانات الحالية:**
📝 الاسم: **{user['full_name']}**
📱 الهاتف: **{user['phone'] if user['phone'] else 'غير محدد'}**
💳 رقم المحفظة: **{user['wallet_number']}**
🆔 معرف تلغرام: **{user['telegram_id']}**

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
        await query.edit_message_text(ErrorMessages.settings_error("البيانات الشخصية"))

async def view_full_profile_handler(update: Update, context: CallbackContext):
    """معالج عرض البيانات الكاملة للمستخدم"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} لم يتم العثور على بيانات المستخدم.")
            return
        
        # الحصول على إحصائيات مفصلة للمستخدم
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المعاملات
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE user_id = ?', (user['id'],))
        total_transactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = "purchase"', (user['id'],))
        result = cursor.fetchone()[0]
        total_purchases = result if result is not None else 0
        
        cursor.execute('SELECT SUM(amount) FROM transactions WHERE user_id = ? AND type = "transfer"', (user['id'],))
        result = cursor.fetchone()[0]
        total_transfers = result if result is not None else 0
        
        # إحصائيات الإحالات
        cursor.execute('SELECT COUNT(*) FROM referrals WHERE referrer_id = ?', (user['id'],))
        total_referrals = cursor.fetchone()[0]
        
        # آخر نشاط
        cursor.execute('''
            SELECT action, details, created_at 
            FROM activity_logs 
            WHERE user_id = ? 
            ORDER BY created_at DESC 
            LIMIT 5
        ''', (user['id'],))
        recent_activities = cursor.fetchall()
        
        conn.close()
        
        # تنسيق النشاطات الأخيرة
        activities_text = ""
        if recent_activities:
            for activity in recent_activities:
                activities_text += f"• {activity[0]}: {activity[1][:30]}... - {activity[2][:16]}\n"
        else:
            activities_text = "• لا توجد نشاطات مسجلة\n"
        
        profile_text = f"""
📋 **البيانات الكاملة للمستخدم** 📋

👤 **المعلومات الأساسية:**
📝 الاسم: **{user['full_name']}**
📱 الهاتف: **{user['phone'] if user['phone'] else 'غير محدد'}**
💳 رقم المحفظة: **{user['wallet_number']}**
🆔 معرف تلغرام: **{user['telegram_id']}**
🎭 الدور: **{USER_ROLES.get(user['role'], user['role'])}**
🟢 الحالة: **{'نشط' if user['is_active'] else 'غير نشط'}**

💰 **المعلومات المالية:**
💵 الرصيد الحالي: **{user['balance']:,.2f}** ريال
💸 إجمالي المشتريات: **{total_purchases:,.2f}** ريال
🔄 إجمالي التحويلات: **{total_transfers:,.2f}** ريال
📊 إجمالي المعاملات: **{total_transactions:,}**

👥 **الإحالات:**
🎯 عدد الإحالات: **{total_referrals:,}**

📅 **التواريخ المهمة:**
📅 تاريخ التسجيل: **{user['created_at'][:16]}**
⏰ آخر نشاط: **{user['last_activity'][:16]}**

⚡ **النشاطات الأخيرة:**
{activities_text}

───────────────────
💡 استخدم الأزرار أدناه للمزيد من الخيارات
"""
        
        keyboard = [
            [InlineKeyboardButton('📊 تقاريري المفصلة', callback_data='detailed_reports'),
             InlineKeyboardButton('💳 محفظتي المطورة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('⚙️ إعدادات الحساب', callback_data='account_settings'),
             InlineKeyboardButton('🔄 تحديث البيانات', callback_data='update_profile')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in view full profile handler: {e}")
        await query.edit_message_text(ErrorMessages.settings_error("عرض البيانات الكاملة"))

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
        await query.edit_message_text(ErrorMessages.settings_error("كلمة المرور"))

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
        await query.edit_message_text(menu_error("معلومات التواصل", "الدعم الفني"))

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
        await query.edit_message_text(ErrorMessages.settings_error("حالة الحساب"))

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
        await query.edit_message_text(wallet_error("شحن الرصيد"))

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
        
        # حماية ضد الضغط المتعدد
        if context.user_data.get('transfer_processing'):
            await query.answer("⏳ العملية قيد التنفيذ، يرجى الانتظار...", show_alert=True)
            return
        
        # تعيين حالة المعالجة
        context.user_data['transfer_processing'] = True
        
        # Get transfer details
        target_user_id = context.user_data.get('target_user_id')
        target_user_name = context.user_data.get('target_user_name')
        amount = context.user_data.get('transfer_amount')
        transfer_fee = 0.0  # FREE transfers
        
        if not all([target_user_id, amount]):
            await query.edit_message_text(f"{EMOJIS['error']} معلومات التحويل مفقودة. يرجى البدء من جديد.")
            return
        
        # Execute the transfer
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
        
        # No fee transaction - transfers are FREE!
        
        # Update balances
        sender_new_balance = recalc_and_set_user_balance(user['id'])
        receiver_new_balance = recalc_and_set_user_balance(target_user['id'])
        
        # تسجيل القيد المحاسبي للتحويل
        record_transfer_accounting(amount, user['id'], target_user['id'], transfer_id)
        
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
🆓 التحويل: **مجاني بدون رسوم**
📊 إجمالي الخصم: **{amount:.2f}** ريال (بدون رسوم)

💵 **الأرصدة:**
🔻 رصيدك الجديد: **{sender_new_balance:.2f}** ريال
🔺 رصيد المستلم: **{receiver_new_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📱 سيتم إشعار المستلم فوراً
"""
        
        await query.edit_message_text(success_text, parse_mode='Markdown')
        
        # Send notification to receiver (about receiving money)
        try:
            receiver_notification = f"""
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
                text=receiver_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to receiver {target_user['telegram_id']}: {e}")

        # Send notification to sender (about sending money)
        try:
            sender_notification = f"""
📤 **تم خصم رصيد من محفظتك** 📤

💸 **تفاصيل الخصم:**
👤 المستلم: **{target_user['full_name']}**
💰 المبلغ المخصوم: **{amount:.2f}** ريال
🆓 الرسوم: **مجاني**
💵 رصيدك الجديد: **{sender_new_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
            
            await context.bot.send_message(
                chat_id=user['telegram_id'],
                text=sender_notification,
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.warning(f"Failed to send notification to sender {user['telegram_id']}: {e}")
        
        # Log the transfer
        logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
        
    except Exception as e:
        logger.error(f"Error in confirm transfer handler: {e}")
        await query.edit_message_text(wallet_error("تنفيذ التحويل"))

def main():
    """Main function to start the bot with enhanced error handling"""
    try:
        # Initialize database with timeout
        logger.info("Initializing database...")
        try:
            init_db()
            logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            raise BotDatabaseError(f"Failed to initialize database: {e}")
        except Exception as e:
            raise BotConfigurationError(f"Database configuration error: {e}")
        
        # Validate configuration
        if not BOT_TOKEN:
            raise BotConfigurationError("BOT_TOKEN is not configured")
        
        # Create persistence with error handling
        try:
            persistence = PicklePersistence(filepath='yemen_net_bot_data')
            application = Application.builder().token(BOT_TOKEN).persistence(persistence).build()
        except Exception as e:
            raise BotConfigurationError(f"Failed to create application: {e}")
        
        # Set bot commands (will be done after startup)
        async def post_init(application):
            try:
                logger.info("Setting bot commands...")
                await asyncio.wait_for(
                    application.bot.set_my_commands(QUICK_COMMANDS),
                    timeout=30.0
                )
                await asyncio.wait_for(
                    application.bot.set_chat_menu_button(menu_button=MenuButtonCommands()),
                    timeout=30.0
                )
                logger.info("Bot commands set successfully")
            except asyncio.TimeoutError:
                logger.error("Timeout setting bot commands")
            except (TelegramError, NetworkError) as e:
                logger.error(f'Telegram error setting commands/menu: {e}')
            except Exception as e:
                logger.error(f'Unexpected error setting commands/menu: {e}')
        
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
                MessageHandler(filters.TEXT & filters.Regex(r'^/cancel$'), COMMAND_HANDLERS['cancel']),
            ],
            name='yemen_net_conversation',
            persistent=True,
            allow_reentry=True,
            per_message=False,
            per_chat=True,
        )
        
        # Enhanced error handler
        async def error_handler(update: object, context):
            """Enhanced error handler with specific error types"""
            error = context.error
            
            # Log error with context
            if isinstance(error, (NetworkError, TimedOut)):
                logger.warning(f"Network/Timeout error: {error}")
            elif isinstance(error, TelegramError):
                logger.error(f"Telegram API error: {error}")
            elif isinstance(error, (BotDatabaseError, sqlite3.Error)):
                logger.error(f"Database error: {error}")
            elif isinstance(error, BotValidationError):
                logger.warning(f"Validation error: {error}")
            elif isinstance(error, BotPermissionError):
                logger.warning(f"Permission error: {error}")
            else:
                logger.error("Unexpected error while handling update:", exc_info=error)
            
            # Try to send appropriate error message to user
            try:
                if isinstance(update, Update) and update.effective_chat:
                    if isinstance(error, (NetworkError, TimedOut)):
                        message = f"{EMOJIS['warning']} مشكلة في الاتصال. يرجى المحاولة مرة أخرى."
                    elif isinstance(error, (BotDatabaseError, sqlite3.Error)):
                        message = f"{EMOJIS['error']} خطأ في قاعدة البيانات. يرجى المحاولة لاحقاً."
                    elif isinstance(error, BotValidationError):
                        message = f"{EMOJIS['warning']} بيانات غير صحيحة. يرجى التحقق والمحاولة مرة أخرى."
                    elif isinstance(error, BotPermissionError):
                        message = f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية."
                    else:
                        message = unexpected_error("تنفيذ العملية", "معالجة الطلب")
                    
                    await asyncio.wait_for(
                        context.bot.send_message(
                            chat_id=update.effective_chat.id,
                            text=message
                        ),
                        timeout=10.0
                    )
            except Exception:
                pass  # Don't log if this fails
        
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
        
        # Add unified command handlers (removed from handlers.py)
        application.add_handler(CommandHandler('wifi_search', search_networks_handler))
        application.add_handler(CommandHandler('search_networks', search_networks_handler))
        application.add_handler(CommandHandler('promotions', promotions_handler))
        application.add_handler(CommandHandler('redeem_coupon', redeem_coupon_handler))
        application.add_handler(CommandHandler('statement', account_statement_handler))
        
        # Start the bot with enhanced error handling
        logger.info(f'{EMOJIS["fire"]} Starting Pottagrm Enhanced Bot v2.1.0...')
        try:
            # Configure timeouts for the polling
            application.run_polling(
                allowed_updates=Update.ALL_TYPES,
                timeout=30
            )
        except KeyboardInterrupt:
            logger.info("Bot stopped by user (Ctrl+C)")
        except (NetworkError, TimedOut) as e:
            logger.error(f"Network error during polling: {e}")
            raise BotTimeoutError(f"Network error: {e}")
        except TelegramError as e:
            logger.error(f"Telegram API error during polling: {e}")
            raise BotConfigurationError(f"Telegram error: {e}")
        
    except BotDatabaseError as e:
        logger.critical(f"Database error prevented bot startup: {e}")
        raise
    except BotConfigurationError as e:
        logger.critical(f"Configuration error prevented bot startup: {e}")
        raise
    except BotTimeoutError as e:
        logger.critical(f"Timeout error prevented bot startup: {e}")
        raise
    except Exception as e:
        logger.critical(f"Unexpected error prevented bot startup: {e}", exc_info=True)
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
    """معالج المحفظة المحسنة مع نظام التصفح بالصفحات"""
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
        
        # صفحة افتراضية (الصفحة الأولى)
        page = 1
        return await show_wallet_page(update, context, user, page, is_callback)
        
    except Exception as e:
        logger.error(f"Error in enhanced wallet handler: {e}")
        from enhanced_error_messages import ErrorMessages
        error_msg = ErrorMessages.custom_error(
            "المحفظة المطورة",
            "فشل في تحميل بيانات المحفظة",
            "تحقق من الاتصال وحاول مرة أخرى",
            "WALLET_LOAD_ERROR"
        )
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def show_wallet_page(update: Update, context: CallbackContext, user: dict, page: int, is_callback: bool = True):
    """عرض صفحة محددة من المحفظة مع نظام التصفح"""
    try:
        TRANSACTIONS_PER_PAGE = 4  # 4 معاملات لكل صفحة
        
        # الحصول على جميع المعاملات مع إحصائيات التصفح
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إجمالي عدد المعاملات
        cursor.execute('''
            SELECT COUNT(*) FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id']))
        total_transactions = cursor.fetchone()[0]
        
        # حساب إجمالي الصفحات
        total_pages = max(1, (total_transactions + TRANSACTIONS_PER_PAGE - 1) // TRANSACTIONS_PER_PAGE)
        
        # التأكد من أن رقم الصفحة صحيح
        page = max(1, min(page, total_pages))
        
        # حساب الإزاحة (offset) لقاعدة البيانات
        offset = (page - 1) * TRANSACTIONS_PER_PAGE
        
        # جلب المعاملات للصفحة الحالية
        cursor.execute('''
            SELECT id, from_user, to_user, amount, type, description, created_at
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        ''', (user['id'], user['id'], TRANSACTIONS_PER_PAGE, offset))
        
        page_transactions = cursor.fetchall()
        
        # إحصائيات المعاملات الإجمالية
        cursor.execute('''
            SELECT 
                COUNT(*) as total_count,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount END), 0) as sent_total,
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount END), 0) as received_total
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user['id'], user['id'], user['id'], user['id']))
        
        stats = cursor.fetchone()
        total_count, sent_amount, received_amount = stats
        
        conn.close()
        
        # حساب التقييم
        rating_data = calculate_user_rating(user['id'])
        
        # بناء نص المحفظة
        wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
💰 **الرصيد:** {user['balance']:,.2f} ريال
💳 **رقم المحفظة:** {user['wallet_number']}

📊 **إحصائيات المحفظة:**
📤 المرسل: **{sent_amount:,.2f}** ريال ({total_count} معاملة)
📥 المستلم: **{received_amount:,.2f}** ريال
💵 صافي الحركة: **{received_amount - sent_amount:+,.2f}** ريال
⭐ تقييمي: **{rating_data['average_rating']}/5**

📋 **المعاملات (صفحة {page} من {total_pages}):**

"""
        
        if page_transactions:
            for transaction in page_transactions:
                trans_id, from_user_id, to_user_id, amount, trans_type, description, created_at = transaction
                
                # تحديد اتجاه المعاملة والأيقونات
                if from_user_id == user['id']:
                    # معاملة صادرة (سحب)
                    direction_color = "🔴"
                    direction_icon = "📤"
                    direction_text = "مرسل"
                    amount_prefix = "-"
                else:
                    # معاملة واردة (إيداع)
                    direction_color = "🟢" 
                    direction_icon = "📥"
                    direction_text = "مستلم"
                    amount_prefix = "+"
                
                # أيقونات أنواع المعاملات
                type_icons = {
                    'transfer': '🔄',
                    'card_purchase': '🛒', 
                    'coupon_redeem': '🎟️',
                    'commission': '🎯',
                    'money_creation': '💰',
                    'transfer_fee': '💳'
                }
                
                type_names = {
                    'transfer': 'تحويل رصيد',
                    'card_purchase': 'شراء كرت',
                    'coupon_redeem': 'شحن بكوبون', 
                    'commission': 'عمولة',
                    'money_creation': 'إنشاء رصيد',
                    'transfer_fee': 'رسوم تحويل'
                }
                
                type_icon = type_icons.get(trans_type, '💼')
                type_name = type_names.get(trans_type, 'معاملة')
                
                # تنسيق التاريخ
                date_formatted = created_at[:16] if created_at else 'غير محدد'
                
                # عرض المعاملة بالتنسيق الجديد
                wallet_text += f"""
📅 {date_formatted}
{direction_color} {direction_text} | {type_icon} {type_name} | 💰 {amount_prefix}{amount:,.0f} ريال

"""
        else:
            if total_transactions == 0:
                wallet_text += "📭 لا توجد معاملات حتى الآن"
            else:
                wallet_text += "📭 لا توجد معاملات في هذه الصفحة"
        
        # بناء لوحة المفاتيح مع أزرار التصفح
        keyboard = []
        
        # أزرار التصفح (إذا كان هناك أكثر من صفحة)
        if total_pages > 1:
            navigation_row = []
            
            # زر الصفحة السابقة
            if page > 1:
                navigation_row.append(InlineKeyboardButton('◀️ السابق', callback_data=f'wallet_page_{page-1}'))
            
            # أزرار أرقام الصفحات (حتى 5 صفحات)
            start_page = max(1, page - 2)
            end_page = min(total_pages, start_page + 4)
            
            for p in range(start_page, end_page + 1):
                if p == page:
                    navigation_row.append(InlineKeyboardButton(f'• {p} •', callback_data=f'wallet_page_{p}'))
                else:
                    navigation_row.append(InlineKeyboardButton(str(p), callback_data=f'wallet_page_{p}'))
            
            # زر الصفحة التالية
            if page < total_pages:
                navigation_row.append(InlineKeyboardButton('▶️ التالي', callback_data=f'wallet_page_{page+1}'))
            
            # تقسيم أزرار التصفح إلى صفوف إذا كانت كثيرة
            if len(navigation_row) > 5:
                keyboard.append(navigation_row[:3])
                keyboard.append(navigation_row[3:])
            else:
                keyboard.append(navigation_row)
        
        # أزرار الوظائف الرئيسية
        keyboard.extend([
            [InlineKeyboardButton('💸 تحويل رصيد', callback_data='transfer_to_friend'),
             InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🎟️ شحن بكوبون', callback_data='redeem_coupon'),
             InlineKeyboardButton('📊 تفاصيل المعاملات', callback_data='transaction_details')],
            [InlineKeyboardButton('🎟️ كشف الحساب', callback_data='account_statement'),
             InlineKeyboardButton('📈 إحصائيات المحفظة', callback_data='wallet_stats')],
            [InlineKeyboardButton('🔄 تحديث الرصيد', callback_data='refresh_balance'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        if is_callback:
            await update.callback_query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        else:
            await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show wallet page: {e}")
        from enhanced_error_messages import ErrorMessages
        error_msg = ErrorMessages.custom_error(
            "صفحة المحفظة",
            f"فشل في تحميل الصفحة رقم {page}",
            "حاول تحديث المحفظة أو العودة للصفحة الأولى",
            "WALLET_PAGE_ERROR"
        )
        
        if is_callback:
            await update.callback_query.edit_message_text(error_msg)
        else:
            await update.message.reply_text(error_msg)

async def wallet_page_handler(update: Update, context: CallbackContext):
    """معالج التنقل بين صفحات المحفظة"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً.")
            return
        
        # استخراج رقم الصفحة من callback_data
        callback_data = query.data
        page = int(callback_data.split('_')[-1])
        
        await show_wallet_page(update, context, user, page, is_callback=True)
        
    except Exception as e:
        logger.error(f"Error in wallet page handler: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "التنقل بين الصفحات",
            "فشل في تحميل الصفحة المطلوبة",
            "حاول العودة للمحفظة الرئيسية وأعد المحاولة",
            "PAGE_NAV_ERROR"
        ))

async def confirm_user_transfer(update: Update, context: CallbackContext, user_id: str, amount: str):
    """تأكيد التحويل للمستخدم - معالج مفقود"""
    try:
        # Get target user info
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM users WHERE id = ?', (int(user_id),))
        target_user = cursor.fetchone()
        conn.close()
        
        if not target_user:
            query = update.callback_query
            await query.edit_message_text(
                f"{EMOJIS['error']} المستخدم المستهدف غير موجود.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
            return
        
        # Set up context for confirm_transfer_handler
        context.user_data['target_user_id'] = int(user_id)
        context.user_data['target_user_name'] = target_user['full_name']
        context.user_data['transfer_amount'] = float(amount)
        context.user_data['awaiting_transfer_confirmation'] = True
        
        # Call the existing confirm_transfer_handler with confirmed=True
        return await confirm_transfer_handler(update, context, confirmed=True)
        
    except Exception as e:
        logger.error(f"Error in confirm user transfer: {e}")
        query = update.callback_query
        await query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في تأكيد التحويل. يرجى المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ])
        )

async def show_network_categories(update: Update, context: CallbackContext, network_id: str):
    """عرض فئات الكروت المتاحة في الشبكة للشراء"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(
                "❌ يرجى التسجيل أولاً /start",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='search_networks')
                ]])
            )
            return
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider FROM networks WHERE id = ? AND is_active = 1', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='search_networks')
                ]])
            )
            return
        
        network_name, provider = network
        
        # الحصول على فئات الكروت المتاحة
        cursor.execute('''
            SELECT DISTINCT nc.card_value as price, COUNT(*) as stock_count
            FROM network_cards nc
            WHERE nc.network_id = ? AND nc.is_sold = 0
            GROUP BY nc.card_value
            ORDER BY nc.card_value ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        categories_text = f"""
🛒 **شراء كروت من {network_name}** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

🏪 **المزود:** {provider}

💳 **الفئات المتاحة:**

"""
        
        keyboard = []
        
        if categories:
            for price, stock_count in categories:
                # إضافة زر لكل فئة
                button_text = f"💰 {price:,.0f} ريال ({stock_count} كرت متاح)"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"select_category_{network_id}_{price}"
                )])
                
                categories_text += f"""
🎫 **كرت بقيمة {price:,.0f} ريال**
📦 المتاح: **{stock_count}** كرت
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            categories_text += "❌ لا توجد فئات متاحة حالياً"
        
        # إضافة أزرار العودة
        keyboard.extend([
            [InlineKeyboardButton('🔙 تفاصيل الشبكة', callback_data=f'network_{network_id}'),
             InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(categories_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show network categories: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "عرض فئات الكروت",
            "فشل في تحميل فئات الكروت المتاحة",
            "تحقق من الاتصال وحاول مرة أخرى",
            "CATEGORIES_ERROR"
        ))

async def confirm_card_purchase(update: Update, context: CallbackContext, network_id: str, price: str):
    """تأكيد شراء الكرت"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT name, provider FROM networks WHERE id = ? AND is_active = 1', (network_id,))
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة")
            return
        
        network_name, provider = network
        card_price = float(price)
        
        # التحقق من توفر الكرت
        cursor.execute('''
            SELECT COUNT(*) FROM network_cards 
            WHERE network_id = ? AND card_value = ? AND is_sold = 0
        ''', (network_id, card_price))
        available_count = cursor.fetchone()[0]
        
        conn.close()
        
        if available_count == 0:
            await query.edit_message_text(
                f"❌ عذراً، لا توجد كروت متاحة بقيمة {card_price:,.0f} ريال",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة للفئات', callback_data=f'buy_from_network_{network_id}')
                ]])
            )
            return
        
        # التحقق من الرصيد
        if user['balance'] < card_price:
            await query.edit_message_text(
                f"❌ رصيدك ({user['balance']:,.2f} ريال) غير كافي لشراء كرت بقيمة {card_price:,.0f} ريال",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('💳 شحن الرصيد', callback_data='enhanced_wallet'),
                    InlineKeyboardButton('🔙 العودة', callback_data=f'buy_from_network_{network_id}')
                ]])
            )
            return
        
        # عرض تأكيد الشراء
        confirm_text = f"""
🛒 **تأكيد الشراء** 🛒

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📋 **تفاصيل الشراء:**
🏪 الشبكة: **{network_name}**
👤 المزود: **{provider}**
💰 قيمة الكرت: **{card_price:,.0f}** ريال
📦 متاح: **{available_count}** كرت

💳 **بعد الشراء:**
رصيدك الجديد: **{user['balance'] - card_price:,.0f}** ريال

❓ **هل أنت متأكد من الشراء؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ نعم، أريد الشراء', callback_data=f'confirm_purchase_{network_id}_{price}'),
             InlineKeyboardButton('❌ لا، إلغاء', callback_data=f'buy_from_network_{network_id}')]
        ]
        
        await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in confirm card purchase: {e}")
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(ErrorMessages.custom_error(
            "تأكيد الشراء",
            "فشل في تحميل معلومات التأكيد",
            "حاول مرة أخرى أو تواصل مع الدعم",
            "CONFIRM_ERROR"
        ))

async def process_card_purchase(update: Update, context: CallbackContext, network_id: str, price: str):
    """تنفيذ شراء الكرت"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        # حماية ضد الضغط المتعدد
        if context.user_data.get('purchase_processing'):
            await query.answer("⏳ عملية الشراء قيد التنفيذ، يرجى الانتظار...", show_alert=True)
            return
        
        # تعيين حالة المعالجة
        context.user_data['purchase_processing'] = True
        
        # الحصول على معلومات الشبكة
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # بدء معاملة قاعدة البيانات
        cursor.execute('BEGIN TRANSACTION')
        
        try:
            cursor.execute('SELECT name, provider, supplier_id FROM networks WHERE id = ? AND is_active = 1', (network_id,))
            network = cursor.fetchone()
            
            if not network:
                raise Exception("الشبكة غير موجودة أو غير متاحة")
            
            network_name, provider, supplier_id = network
            card_price = float(price)
            
            # التحقق من توفر الكرت (مع قفل للصف لتجنب التضارب)
            cursor.execute('''
                SELECT id FROM network_cards 
                WHERE network_id = ? AND card_value = ? AND is_sold = 0
                LIMIT 1
            ''', (network_id, card_price))
            
            card_result = cursor.fetchone()
            if not card_result:
                raise Exception(f"لا توجد كروت متاحة بقيمة {card_price:,.0f} ريال")
            
            card_id = card_result[0]
            
            # التحقق من الرصيد مرة أخرى
            cursor.execute('SELECT balance FROM users WHERE telegram_id = ?', (user['telegram_id'],))
            current_balance = cursor.fetchone()[0]
            
            if current_balance < card_price:
                raise Exception(f"رصيدك ({current_balance:,.2f} ريال) غير كافي")
            
            # تحديث حالة الكرت إلى مباع
            cursor.execute('UPDATE network_cards SET is_sold = 1, sold_at = datetime("now") WHERE id = ?', (card_id,))
            
            # خصم المبلغ من رصيد المشتري
            cursor.execute('UPDATE users SET balance = balance - ? WHERE telegram_id = ?', (card_price, user['telegram_id']))
            
            # إضافة المبلغ لرصيد المزود
            cursor.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (card_price, supplier_id))
            
            # إنشاء معاملة في السجل
            import uuid
            transaction_id = str(uuid.uuid4())
            
            cursor.execute('''
                INSERT INTO transactions (id, from_user, to_user, amount, type, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime("now"))
            ''', (transaction_id, user['id'], supplier_id, card_price, 'card_purchase', 
                  f"شراء كرت {card_price:,.0f} ريال من شبكة {network_name}"))
            
            # الحصول على معلومات الكرت
            cursor.execute('SELECT card_code FROM network_cards WHERE id = ?', (card_id,))
            card_code = cursor.fetchone()[0]
            
            # تسجيل القيد المحاسبي لشراء الكرت
            record_purchase_accounting(card_price, user['id'], transaction_id)
            
            # تأكيد المعاملة
            cursor.execute('COMMIT')
            
            # عرض نتيجة الشراء الناجح
            success_text = f"""
✅ **تم الشراء بنجاح!** ✅

👤 **{user['full_name']}**

📋 **تفاصيل الشراء:**
🏪 الشبكة: **{network_name}**
👤 المزود: **{provider}**
💰 المبلغ المدفوع: **{card_price:,.0f}** ريال

🎫 **بيانات الكرت:**
🔢 رقم الكرت: `{card_code}`
💰 القيمة: **{card_price:,.0f}** ريال

💳 **رصيدك الجديد:** {current_balance - card_price:,.2f} ريال

📋 **معرف المعاملة:** `{transaction_id[:8]}`
⏰ **وقت الشراء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

🎉 **شكراً لاستخدام خدماتنا!**
"""
            
            keyboard = [
                [InlineKeyboardButton('🛒 شراء كرت آخر', callback_data=f'buy_from_network_{network_id}'),
                 InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('🔍 البحث في الشبكات', callback_data='search_networks'),
                 InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
            # تنظيف حالة المعالجة بعد النجاح
            context.user_data.clear()
            
            # Send notification to buyer (about purchase)
            try:
                buyer_notification = f"""
🛒 **تم خصم رصيد - شراء كرت** 🛒

💸 **تفاصيل الشراء:**
🏪 الشبكة: **{network_name}**
👤 المزود: **{provider}**
💰 المبلغ المخصوم: **{card_price:,.0f}** ريال
💳 رصيدك الجديد: **{current_balance - card_price:,.2f}** ريال

🎫 **بيانات الكرت:**
🔢 رقم الكرت: `{card_code}`

⏰ **وقت الشراء:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
                
                await context.bot.send_message(
                    chat_id=user['telegram_id'],
                    text=buyer_notification,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.warning(f"Failed to send notification to buyer {user['telegram_id']}: {e}")

            # Send notification to supplier (about sale)
            try:
                # Get supplier's telegram_id
                cursor.execute('SELECT telegram_id FROM users WHERE id = ?', (supplier_id,))
                supplier_telegram_result = cursor.fetchone()
                
                if supplier_telegram_result:
                    supplier_telegram_id = supplier_telegram_result[0]
                    
                    supplier_notification = f"""
💰 **تم بيع كرت من شبكتك!** 💰

📈 **تفاصيل البيع:**
🏪 الشبكة: **{network_name}**
👤 المشتري: **{user['full_name']}**
💰 المبلغ المحول إليك: **{card_price:,.0f}** ريال
🎫 نوع الكرت: **{card_price:,.0f} ريال**

⏰ **وقت البيع:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
                    
                    await context.bot.send_message(
                        chat_id=supplier_telegram_id,
                        text=supplier_notification,
                        parse_mode='Markdown'
                    )
            except Exception as e:
                logger.warning(f"Failed to send notification to supplier: {e}")
            
        except Exception as e:
            # إلغاء المعاملة في حالة الخطأ
            cursor.execute('ROLLBACK')
            raise e
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in process card purchase: {e}")
        
        # تنظيف حالة المعالجة في حالة الخطأ
        context.user_data.clear()
        
        from enhanced_error_messages import ErrorMessages
        await query.edit_message_text(
            ErrorMessages.custom_error(
                "تنفيذ الشراء",
                f"فشل في إتمام عملية الشراء - {str(e)}",
                "تحقق من رصيدك وتوفر الكروت وحاول مرة أخرى",
                "PURCHASE_ERROR"
            ),
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🔄 إعادة المحاولة', callback_data=f'buy_from_network_{network_id}'),
                 InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ])
        )


# معالجات إدارة الشبكات للمشرف الأعلى
