#!/usr/bin/env python3
"""
Callback Handlers Module
Handles all callback query interactions
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CallbackQueryHandler
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.handlers import show_main_menu
from bot_modules.wallet_handlers import enhanced_wallet_handler
from bot_modules.network_handlers import (
    search_networks_handler, show_network_details, 
    view_networks_handler, buy_from_network_handler
)
from bot_modules.transfer_handlers import (
    transfer_to_friend_handler, search_user_handler,
    confirm_transfer_handler
)
from bot_modules.supplier_handlers import (
    supplier_panel_handler, manage_networks_handler,
    upload_cards_handler, manual_card_input_handler
)
from bot_modules.admin_handlers import (
    super_admin_panel_handler, admin_manage_users_handler,
    admin_manage_networks_handler, admin_upload_cards_handler
)

logger = logging.getLogger(__name__)

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
        result = await route_callback(update, context, callback_data, user)
        
        if result is False:
            # Handle unknown callback
            await query.edit_message_text(
                f"{EMOJIS['error']} خيار غير معروف. يرجى المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')
                ]])
            )
            
    except Exception as e:
        logger.error(f"Error in button click handler: {e}", exc_info=True)
        try:
            await update.callback_query.edit_message_text(
                f"{EMOJIS['error']} حدث خطأ في معالجة الطلب. يرجى المحاولة مرة أخرى.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')
                ]])
            )
        except:
            pass

async def route_callback(update: Update, context: CallbackContext, callback_data: str, user: dict):
    """Route callback to appropriate handler"""
    
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
    elif callback_data.startswith('buy_from_network_'):
        network_id = callback_data.split('_')[-1]
        return await buy_from_network_handler(update, context, network_id)
    
    # Transfer handlers
    elif callback_data == 'transfer_to_friend':
        return await transfer_to_friend_handler(update, context)
    elif callback_data == 'advanced_search_transfer':
        return await search_user_handler(update, context)
    elif callback_data.startswith('confirm_transfer_'):
        transfer_data = callback_data.split('_', 2)[2]
        return await confirm_transfer_handler(update, context, transfer_data)
    
    # Supplier handlers
    elif callback_data == 'supplier_panel':
        return await supplier_panel_handler(update, context)
    elif callback_data == 'manage_networks':
        return await manage_networks_handler(update, context)
    elif callback_data == 'upload_cards':
        return await upload_cards_handler(update, context)
    elif callback_data == 'manual_card_input':
        return await manual_card_input_handler(update, context)
    elif callback_data.startswith('manual_network_'):
        network_id = callback_data.split('_')[-1]
        return await manual_network_selection_handler(update, context, network_id)
    elif callback_data.startswith('price_'):
        parts = callback_data.split('_')
        price = parts[1]
        network_id = parts[2]
        return await price_selection_handler(update, context, price, network_id)
    elif callback_data.startswith('custom_price_'):
        network_id = callback_data.split('_')[-1]
        return await custom_price_handler(update, context, network_id)
    
    # Admin handlers
    elif callback_data == 'super_admin_panel':
        return await super_admin_panel_handler(update, context)
    elif callback_data == 'admin_manage_users':
        return await admin_manage_users_handler(update, context)
    elif callback_data == 'admin_manage_networks':
        return await admin_manage_networks_handler(update, context)
    elif callback_data == 'admin_upload_cards':
        return await admin_upload_cards_handler(update, context)
    
    # Buy cards
    elif callback_data == 'buy_cards':
        return await buy_cards_handler(update, context)
    elif callback_data == 'customer_search_networks':
        return await customer_search_networks_handler(update, context)
    elif callback_data.startswith('quick_search_'):
        search_term = callback_data.split('_', 1)[1]
        return await perform_quick_search(update, context, search_term)
    
    # Unknown callback
    return False

def setup_callback_handlers(application):
    """Setup callback handlers"""
    application.add_handler(CallbackQueryHandler(button_click_handler))