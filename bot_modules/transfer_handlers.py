#!/usr/bin/env python3
"""
Transfer Handlers Module
Handles money transfer functionality
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.database import get_db_connection, update_user_balance, log_transaction

logger = logging.getLogger(__name__)

async def transfer_to_friend_handler(update: Update, context: CallbackContext):
    """Handle transfer to friend"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        if user['balance'] <= 0:
            await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي للتحويل.")
            return
        
        transfer_text = f"""
💰 **إرسال رصيد لصديق** 💰

👤 **{user['full_name']}**
💰 **رصيدك الحالي:** {user['balance']:,.2f} ريال

📝 **أدخل رقم المحفظة أو رقم الهاتف:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 عودة للمحفظة', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        # Set transfer state
        context.user_data['awaiting_transfer_step1'] = True
        
        await query.edit_message_text(transfer_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in transfer to friend handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعداد التحويل.")

async def search_user_handler(update: Update, context: CallbackContext):
    """Handle user search for transfer"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        search_text = """
🔍 **البحث عن مستخدم للتحويل** 🔍

💡 **كيفية البحث:**
• اكتب رقم الهاتف (مثال: 777123456)
• اكتب اسم المستخدم
• اكتب رقم المحفظة

🔍 **ابدأ البحث الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔙 عودة للتحويل', callback_data='transfer_to_friend')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        # Set search state
        context.user_data['awaiting_user_search'] = True
        
        await query.edit_message_text(search_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in search user handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن المستخدم.")

async def confirm_transfer_handler(update: Update, context: CallbackContext, transfer_data: str):
    """Handle transfer confirmation"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Parse transfer data
        try:
            target_user_id, amount = transfer_data.split('|')
            target_user_id = int(target_user_id)
            amount = float(amount)
        except:
            await query.edit_message_text(f"{EMOJIS['error']} بيانات التحويل غير صحيحة.")
            return
        
        # Get target user
        target_user = get_user(target_user_id)
        if not target_user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم المستهدف غير موجود.")
            return
        
        # Check balance
        if user['balance'] < amount:
            await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي للتحويل.")
            return
        
        # Calculate transfer fee (1%)
        transfer_fee = amount * 0.01
        total_cost = amount + transfer_fee
        
        if user['balance'] < total_cost:
            await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي (يشمل رسوم التحويل).")
            return
        
        # Confirm transfer
        confirm_text = f"""
💰 **تأكيد التحويل** 💰

📤 **من:** {user['full_name']}
📥 **إلى:** {target_user['full_name']}
💰 **المبلغ:** {amount:,.2f} ريال
💸 **رسوم التحويل:** {transfer_fee:,.2f} ريال
💵 **إجمالي التكلفة:** {total_cost:,.2f} ريال

✅ **هل تريد تأكيد التحويل؟**
"""
        
        keyboard = [
            [InlineKeyboardButton('✅ تأكيد التحويل', callback_data=f'execute_transfer_{target_user_id}_{amount}')],
            [InlineKeyboardButton('❌ إلغاء', callback_data='transfer_to_friend')]
        ]
        
        await query.edit_message_text(confirm_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in confirm transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تأكيد التحويل.")

async def execute_transfer_handler(update: Update, context: CallbackContext, target_user_id: int, amount: float):
    """Execute the transfer"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get target user
        target_user = get_user(target_user_id)
        if not target_user:
            await query.edit_message_text(f"{EMOJIS['error']} المستخدم المستهدف غير موجود.")
            return
        
        # Check balance again
        if user['balance'] < amount:
            await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي للتحويل.")
            return
        
        # Calculate transfer fee
        transfer_fee = amount * 0.01
        total_cost = amount + transfer_fee
        
        if user['balance'] < total_cost:
            await query.edit_message_text(f"{EMOJIS['error']} رصيدك غير كافي (يشمل رسوم التحويل).")
            return
        
        # Execute transfer
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Update sender balance
            new_sender_balance = user['balance'] - total_cost
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_sender_balance, user['id']))
            
            # Update receiver balance
            new_receiver_balance = target_user['balance'] + amount
            cursor.execute('UPDATE users SET balance = ? WHERE id = ?', (new_receiver_balance, target_user_id))
            
            # Log transaction
            cursor.execute('''
                INSERT INTO transactions (from_user, to_user, amount, type, description, created_at)
                VALUES (?, ?, ?, 'transfer', ?, CURRENT_TIMESTAMP)
            ''', (user['id'], target_user_id, amount, f"تحويل إلى {target_user['full_name']}"))
            
            conn.commit()
            conn.close()
            
            # Success message
            success_text = f"""
✅ **تم التحويل بنجاح!** ✅

📤 **من:** {user['full_name']}
📥 **إلى:** {target_user['full_name']}
💰 **المبلغ:** {amount:,.2f} ريال
💸 **رسوم التحويل:** {transfer_fee:,.2f} ريال
💵 **إجمالي التكلفة:** {total_cost:,.2f} ريال
💳 **رصيدك الجديد:** {new_sender_balance:,.2f} ريال

⏰ **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
            
            keyboard = [
                [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('🔄 تحويل آخر', callback_data='transfer_to_friend')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await query.edit_message_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            
            # Send notification to receiver
            try:
                notification_text = f"""
💰 **تم استلام رصيد جديد!** 💰

📥 **تفاصيل الاستلام:**
👤 المرسل: **{user['full_name']}**
💰 المبلغ المستلم: **{amount:.2f}** ريال
💵 رصيدك الجديد: **{new_receiver_balance:.2f}** ريال

🕐 **وقت التحويل:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

───────────────────
💡 استخدم /wallet لعرض محفظتك
"""
                
                # Note: In a real implementation, you would send this to the target user
                logger.info(f"Notification sent to {target_user['full_name']}: {notification_text}")
                
            except Exception as e:
                logger.warning(f"Failed to send notification to receiver {target_user_id}: {e}")
            
            # Log the transfer
            logger.info(f"User {user['full_name']} sent {amount} YER to {target_user['full_name']} (fee: {transfer_fee})")
            
        except Exception as db_error:
            logger.error(f"Database error in transfer: {db_error}")
            await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في قاعدة البيانات أثناء التحويل.")
            
    except Exception as e:
        logger.error(f"Error in execute transfer handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في تنفيذ التحويل.")