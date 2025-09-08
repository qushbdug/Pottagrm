#!/usr/bin/env python3
"""
Text Message Handler for Pottagrm Enhanced Bot
"""

import logging
from telegram import Update
from telegram.ext import CallbackContext

from src.utils.user_utils import get_user

logger = logging.getLogger(__name__)

async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages that are not commands."""
    user = get_user(update.message.from_user.id)
    if not user:
        # This can happen if a user who is not registered tries to send a message.
        # The start handler should be the only entry point for new users.
        await update.message.reply_text("أرسل /start للبدء.")
        return

    # For now, just a simple response. This can be expanded later to handle
    # more complex text-based interactions (e.g., searching by text).
    await update.message.reply_text("لم أفهم طلبك. الرجاء استخدام الأزرار أو الأوامر.")
