#!/usr/bin/env python3
"""
Main Router Module
الموزع الرئيسي للأزرار والأوامر
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import get_user
from bot_modules.config import EMOJIS

# Import all handler modules
from bot_modules.wallet_handlers import (
    transfer_handler, wallet_stats_handler, transfer_to_friend_handler,
    transfer_history_handler, recharge_balance_handler, confirm_transfer_handler,
    enhanced_wallet_handler, show_wallet_page, wallet_page_handler, confirm_user_transfer
)

from bot_modules.purchase_handlers import (
    buy_cards_handler, show_network_categories, confirm_card_purchase, process_card_purchase
)

from bot_modules.supplier_handlers import (
    supplier_panel_handler, view_networks_handler, manage_networks_handler,
    share_network_handler, upload_cards_handler, cards_reports_handler,
    sales_stats_handler, upload_history_handler, supplier_settings_handler,
    search_networks_handler, show_network_details, add_network_handler
)

from bot_modules.withdrawal_handlers import (
    request_withdrawal_handler, submit_withdrawal_request_handler,
    view_my_withdrawals_handler, process_withdrawal_step,
    confirm_withdrawal_request_handler, approve_withdrawal_handler,
    reject_withdrawal_handler
)

from bot_modules.referral_handlers import (
    referral_stats_handler, copy_referral_link_handler, copy_share_link_handler
)

from bot_modules.notification_handlers import (
    my_notifications_handler, personal_reports_handler, 
    transaction_details_handler, promotions_handler, help_handler
)

# Import admin functions
from bot_modules.admin_functions import ADMIN_CALLBACKS

logger = logging.getLogger(__name__)

async def button_click_handler(update: Update, context):
    """Main router for all button clicks"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        callback_data = query.data
        
        # ===== Wallet and Transfer Handlers =====
        if callback_data == 'transfer':
            return await transfer_handler(update, context)
        elif callback_data == 'wallet_stats':
            return await wallet_stats_handler(update, context)
        elif callback_data == 'transfer_to_friend':
            return await transfer_to_friend_handler(update, context)
        elif callback_data == 'transfer_history':
            return await transfer_history_handler(update, context)
        elif callback_data == 'recharge_balance':
            return await recharge_balance_handler(update, context)
        elif callback_data == 'confirm_transfer_yes':
            return await confirm_transfer_handler(update, context, True)
        elif callback_data == 'confirm_transfer_no':
            return await confirm_transfer_handler(update, context, False)
        elif callback_data == 'enhanced_wallet':
            return await enhanced_wallet_handler(update, context)
        elif callback_data.startswith('wallet_page_'):
            return await wallet_page_handler(update, context)
        elif callback_data.startswith('confirm_transfer_'):
            parts = callback_data.split('_')
            user_id = parts[2]
            amount = parts[3]
            return await confirm_user_transfer(update, context, user_id, amount)
        
        # ===== Purchase and Card Handlers =====
        elif callback_data == 'buy_cards':
            return await buy_cards_handler(update, context)
        elif callback_data.startswith('buy_from_network_'):
            network_id = callback_data.split('_')[3]
            return await show_network_categories(update, context, network_id)
        elif callback_data.startswith('confirm_purchase_'):
            parts = callback_data.split('_')
            network_id = parts[2]
            price = parts[3]
            return await confirm_card_purchase(update, context, network_id, price)
        elif callback_data.startswith('process_purchase_'):
            parts = callback_data.split('_')
            network_id = parts[2]
            price = parts[3]
            return await process_card_purchase(update, context, network_id, price)
        
        # ===== Supplier and Network Handlers =====
        elif callback_data == 'supplier_panel':
            return await supplier_panel_handler(update, context)
        elif callback_data == 'view_networks':
            return await view_networks_handler(update, context)
        elif callback_data == 'manage_networks':
            return await manage_networks_handler(update, context)
        elif callback_data.startswith('share_network_'):
            network_id = callback_data.split('_')[2]
            return await share_network_handler(update, context, network_id)
        elif callback_data == 'upload_cards':
            return await upload_cards_handler(update, context)
        elif callback_data == 'cards_reports':
            return await cards_reports_handler(update, context)
        elif callback_data == 'sales_stats':
            return await sales_stats_handler(update, context)
        elif callback_data == 'upload_history':
            return await upload_history_handler(update, context)
        elif callback_data == 'supplier_settings':
            return await supplier_settings_handler(update, context)
        elif callback_data == 'search_networks':
            return await search_networks_handler(update, context)
        elif callback_data.startswith('network_'):
            network_id = callback_data.split('_')[1]
            return await show_network_details(update, context, network_id)
        elif callback_data == 'add_network':
            return await add_network_handler(update, context)
        
        # ===== Withdrawal Handlers =====
        elif callback_data == 'request_withdrawal':
            return await request_withdrawal_handler(update, context)
        elif callback_data == 'submit_withdrawal_request':
            return await submit_withdrawal_request_handler(update, context)
        elif callback_data == 'view_my_withdrawals':
            return await view_my_withdrawals_handler(update, context)
        elif callback_data.startswith('withdrawal_method_'):
            method = callback_data.split('_', 2)[2]
            return await confirm_withdrawal_request_handler(update, context, method)
        elif callback_data.startswith('approve_withdrawal_'):
            withdrawal_id = callback_data.split('_', 2)[2]
            return await approve_withdrawal_handler(update, context, withdrawal_id)
        elif callback_data.startswith('reject_withdrawal_'):
            withdrawal_id = callback_data.split('_', 2)[2]
            return await reject_withdrawal_handler(update, context, withdrawal_id)
        
        # ===== Referral Handlers =====
        elif callback_data == 'referral_stats':
            return await referral_stats_handler(update, context)
        elif callback_data.startswith('copy_referral_'):
            return await copy_referral_link_handler(update, context)
        elif callback_data.startswith('copy_share_link_'):
            return await copy_share_link_handler(update, context)
        
        # ===== Notification and Report Handlers =====
        elif callback_data == 'my_notifications':
            return await my_notifications_handler(update, context)
        elif callback_data == 'personal_reports':
            return await personal_reports_handler(update, context)
        elif callback_data == 'transaction_details':
            return await transaction_details_handler(update, context)
        elif callback_data == 'promotions':
            return await promotions_handler(update, context)
        elif callback_data == 'help':
            return await help_handler(update, context)
        
        # ===== Admin Handlers =====
        elif callback_data in ADMIN_CALLBACKS:
            if user['role'] in ['admin', 'super_admin']:
                return await ADMIN_CALLBACKS[callback_data](update, context)
            else:
                await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية لهذه العملية.")
                return
        
        # ===== Refresh Balance =====
        elif callback_data == 'refresh_balance':
            new_balance = recalc_and_set_user_balance(user['id'])
            # إعادة تحميل بيانات المستخدم بعد تحديث الرصيد
            user = get_user(user['id'])
            # العودة للمحفظة المطورة مع الرصيد المحدث
            return await enhanced_wallet_handler(update, context)
        
        # ===== Unhandled Callbacks =====
        else:
            logger.warning(f"Unhandled callback: {callback_data}")
            await query.edit_message_text(
                f"⚠️ **عذراً، هذه الميزة قيد التطوير**\n\nالزر: `{callback_data}`",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ]),
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Error in button click handler: {e}")
        try:
            await query.edit_message_text(
                f"{EMOJIS['error']} حدث خطأ في معالجة الطلب. يرجى المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
        except:
            pass