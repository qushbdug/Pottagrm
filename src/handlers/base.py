#!/usr/bin/env python3
"""
Base Handler Classes for Yemen Net Bot
Professional handler architecture with error handling and logging.
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Union
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes, ConversationHandler
from telegram.constants import ParseMode

# Import from core modules
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.utils import error_handler, rate_limiter, get_user
from core.config import EMOJIS

logger = logging.getLogger(__name__)


class BaseHandler(ABC):
    """Base class for all handlers with common functionality."""
    
    def __init__(self):
        self.name = self.__class__.__name__
    
    async def handle(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Main handler method with error handling and logging."""
        try:
            # Rate limiting check
            user_id = update.effective_user.id
            if not rate_limiter.can_perform_action(user_id, self.name):
                await self._send_rate_limit_message(update, context)
                return ConversationHandler.END
            
            # Log the action
            logger.info(f"Handler {self.name} called by user {user_id}")
            
            # Execute the actual handler
            result = await self._handle_impl(update, context)
            
            # Log success
            logger.info(f"Handler {self.name} completed successfully for user {user_id}")
            return result
            
        except Exception as e:
            # Log and handle errors
            logger.error(f"Error in handler {self.name}: {e}", exc_info=True)
            await self._handle_error(update, context, e)
            return ConversationHandler.END
    
    @abstractmethod
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Implementation of the handler logic."""
        pass
    
    async def _handle_error(self, update: Update, context: ContextTypes.DEFAULT_TYPE, error: Exception) -> None:
        """Handle errors gracefully."""
        error_message = error_handler.handle_general_error(error, self.name)
        await self._send_message(update, context, error_message)
    
    async def _send_rate_limit_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Send rate limit exceeded message."""
        message = f"{EMOJIS['warning']} لقد تجاوزت الحد المسموح من الطلبات. يرجى الانتظار قليلاً."
        await self._send_message(update, context, message)
    
    async def _send_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        text: str,
        reply_markup: Optional[InlineKeyboardMarkup] = None,
        parse_mode: str = ParseMode.MARKDOWN
    ) -> None:
        """Send message with error handling."""
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
            else:
                await update.message.reply_text(
                    text=text,
                    reply_markup=reply_markup,
                    parse_mode=parse_mode
                )
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            # Fallback to simple text message
            try:
                if update.callback_query:
                    await update.callback_query.answer(text, show_alert=True)
                else:
                    await update.message.reply_text(text)
            except Exception as fallback_error:
                logger.error(f"Fallback message also failed: {fallback_error}")


class CommandHandler(BaseHandler):
    """Base class for command handlers."""
    
    def __init__(self, command: str):
        super().__init__()
        self.command = command
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle command with user validation."""
        user = get_user(update.effective_user.id)
        if not user:
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            )
            return ConversationHandler.END
        
        return await self._handle_command(update, context, user)
    
    @abstractmethod
    async def _handle_command(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Handle the specific command logic."""
        pass


class CallbackHandler(BaseHandler):
    """Base class for callback query handlers."""
    
    def __init__(self, callback_data: str):
        super().__init__()
        self.callback_data = callback_data
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle callback with user validation."""
        # Answer callback query to remove loading state
        try:
            await update.callback_query.answer()
        except Exception:
            pass  # Ignore callback answer errors
        
        user = get_user(update.effective_user.id)
        if not user:
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            )
            return ConversationHandler.END
        
        return await self._handle_callback(update, context, user)
    
    @abstractmethod
    async def _handle_callback(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Handle the specific callback logic."""
        pass


class MessageHandler(BaseHandler):
    """Base class for message handlers."""
    
    def __init__(self, filters=None):
        super().__init__()
        self.filters = filters
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle message with user validation."""
        user = get_user(update.effective_user.id)
        if not user:
            await self._send_message(
                update, 
                context, 
                f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            )
            return ConversationHandler.END
        
        return await self._handle_message(update, context, user)
    
    @abstractmethod
    async def _handle_message(
        self, 
        update: Update, 
        context: ContextTypes.DEFAULT_TYPE, 
        user: Any
    ) -> Any:
        """Handle the specific message logic."""
        pass


class ConversationHandler(BaseHandler):
    """Base class for conversation handlers."""
    
    def __init__(self, states: Dict[str, int]):
        super().__init__()
        self.states = states
        self.current_state = None
    
    async def _handle_impl(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> Any:
        """Handle conversation with state management."""
        # Get current state from context
        self.current_state = context.user_data.get('conversation_state', 0)
        
        # Handle based on current state
        if self.current_state == 0:
            return await self._start_conversation(update, context)
        else:
            return await self._continue_conversation(update, context)
    
    async def _start_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Start the conversation."""
        context.user_data['conversation_state'] = 0
        return await self._handle_conversation_start(update, context)
    
    async def _continue_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Continue the conversation based on current state."""
        return await self._handle_conversation_continue(update, context)
    
    @abstractmethod
    async def _handle_conversation_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle conversation start."""
        pass
    
    @abstractmethod
    async def _handle_conversation_continue(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Handle conversation continuation."""
        pass
    
    def _set_state(self, context: ContextTypes.DEFAULT_TYPE, state: int) -> None:
        """Set conversation state."""
        context.user_data['conversation_state'] = state
        self.current_state = state
    
    def _get_state(self, context: ContextTypes.DEFAULT_TYPE) -> int:
        """Get current conversation state."""
        return context.user_data.get('conversation_state', 0)