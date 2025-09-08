#!/usr/bin/env python3
"""
Callback Query Dispatcher for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext

from src.handlers import user_handlers, admin_handlers, supplier_handlers, menu_handler

logger = logging.getLogger(__name__)

# Mapping from callback_data to handler functions
CALLBACK_MAP = {
    # Menu
    'main_menu': menu_handler.show_main_menu,

    # User Handlers
    'buy_cards': user_handlers.buy_cards_handler,
    'transfer_to_friend': user_handlers.transfer_handler,
    'redeem_coupon': user_handlers.redeem_coupon_handler,
    'cancel_coupon': user_handlers.cancel_coupon_handler,
    'personal_reports': user_handlers.personal_reports_handler,
    'my_ratings': user_handlers.my_ratings_handler,
    'my_notifications': user_handlers.my_notifications_handler,
    'promotions': user_handlers.promotions_handler,
    'account_settings': user_handlers.account_settings_handler,

    # Admin Handlers
    'admin_panel': admin_handlers.admin_panel_handler,
    'customer_dashboard': admin_handlers.customer_dashboard_handler,
    'admin_dashboard': admin_handlers.admin_dashboard_handler,
    'admin_add_offers': admin_handlers.admin_add_offers_handler,
    'super_activate_suppliers': admin_handlers.activate_suppliers_handler,
    'super_create_coupons': admin_handlers.create_coupons_handler,

    # Supplier Handlers
    'supplier_panel': supplier_handlers.supplier_panel_handler,
    'manage_networks': supplier_handlers.manage_networks_handler,
    'upload_cards': supplier_handlers.upload_cards_handler,
    'cards_reports': supplier_handlers.cards_reports_handler,
}

async def dispatch_callback_query(update: Update, context: CallbackContext):
    """The main callback query dispatcher."""
    query = update.callback_query
    await query.answer()

    callback_data = query.data

    # Simple direct mapping
    if callback_data in CALLBACK_MAP:
        handler = CALLBACK_MAP[callback_data]
        await handler(update, context)
        return

    # For more complex patterns (e.g., with IDs)
    # This part will be expanded as we refactor more handlers.
    if callback_data.startswith('buy_from_network_'):
        # Example: await user_handlers.show_network_categories(update, context)
        await query.edit_message_text(f"Handler for {callback_data} is not implemented yet.")
    elif callback_data.startswith('select_category_'):
        await query.edit_message_text(f"Handler for {callback_data} is not implemented yet.")
    else:
        logger.warning(f"Unhandled callback query: {callback_data}")
        await query.edit_message_text("This feature is not yet implemented.")
