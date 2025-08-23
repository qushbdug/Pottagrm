#!/usr/bin/env python3
"""
Wallet Handlers Module
Handles wallet-related functionality
"""

import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.database import get_db_connection

logger = logging.getLogger(__name__)

async def enhanced_wallet_handler(update: Update, context: CallbackContext):
    """Enhanced wallet handler with comprehensive error handling"""
    try:
        logger.info("بدء معالجة طلب المحفظة المطورة")
        
        # Determine update type (callback or message)
        if hasattr(update, 'callback_query') and update.callback_query:
            query = update.callback_query
            user = get_user(query.from_user.id)
            is_callback = True
            logger.info(f"طلب callback من المستخدم {query.from_user.id}")
        else:
            user = get_user(update.effective_user.id)
            is_callback = False
            logger.info(f"طلب message من المستخدم {update.effective_user.id}")
        
        if not user:
            logger.warning(f"مستخدم غير مسجل يحاول الوصول للمحفظة")
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً."
            if is_callback:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        logger.info(f"معالجة محفظة المستخدم: {user['full_name']} (ID: {user['id']})")
        
        # Get recent transactions
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            logger.info("تم الاتصال بقاعدة البيانات")
            
            # Recent transactions
            cursor.execute('''
                SELECT id, from_user, to_user, amount, type, description, created_at
                FROM transactions 
                WHERE from_user = ? OR to_user = ?
                ORDER BY created_at DESC
                LIMIT 8
            ''', (user['id'], user['id']))
            
            recent_transactions = cursor.fetchall()
            logger.info(f"تم جلب {len(recent_transactions)} معاملة حديثة")
            
            # Transaction statistics
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
            logger.info(f"إحصائيات المعاملات: إجمالي {total_transactions}, مرسل {sent_amount}, مستلم {received_amount}")
            
            conn.close()
            
        except Exception as db_error:
            logger.error(f"خطأ في قاعدة البيانات: {db_error}", exc_info=True)
            # Use default values in case of database error
            recent_transactions = []
            total_transactions = 0
            sent_amount = 0.0
            received_amount = 0.0
        
        # Calculate rating with error handling
        try:
            logger.info("بدء حساب تقييم المستخدم")
            rating_data = calculate_user_rating(user['id'])
            logger.info(f"تم حساب التقييم: {rating_data}")
        except Exception as rating_error:
            logger.error(f"خطأ في حساب التقييم: {rating_error}", exc_info=True)
            # Use default values in case of rating error
            rating_data = {'total_ratings': 0, 'average_rating': 0.0, 'rating_distribution': {}}
        
        # Build wallet text
        try:
            wallet_text = build_wallet_text(user, recent_transactions, total_transactions, 
                                          sent_amount, received_amount, rating_data)
            logger.info("تم بناء نص المحفظة بنجاح")
            
            # Build keyboard
            keyboard = [
                [InlineKeyboardButton('💰 تحويل رصيد', callback_data='transfer_to_friend')],
                [InlineKeyboardButton('📊 تقارير المعاملات', callback_data='transaction_reports')],
                [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            # Send response
            if is_callback:
                await query.edit_message_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await update.message.reply_text(wallet_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
                
            logger.info("تم إرسال المحفظة بنجاح")
            
        except Exception as text_error:
            logger.error(f"خطأ في بناء نص المحفظة: {text_error}", exc_info=True)
            wallet_text = build_simple_wallet_text(user)
        
        # Create keyboard
        try:
            reply_markup = create_wallet_keyboard()
            logger.info("تم إنشاء لوحة المفاتيح بنجاح")
            
        except Exception as keyboard_error:
            logger.error(f"خطأ في إنشاء لوحة المفاتيح: {keyboard_error}", exc_info=True)
            reply_markup = create_simple_keyboard()
        
        # Send message
        try:
            if is_callback:
                await query.edit_message_text(wallet_text, reply_markup=reply_markup, parse_mode='Markdown')
                logger.info("تم تحديث رسالة المحفظة بنجاح")
            else:
                await update.message.reply_text(wallet_text, reply_markup=reply_markup, parse_mode='Markdown')
                logger.info("تم إرسال رسالة المحفظة بنجاح")
            
        except Exception as send_error:
            logger.error(f"خطأ في إرسال رسالة المحفظة: {send_error}", exc_info=True)
            await send_error_message(update, is_callback)
        
    except Exception as e:
        logger.error(f"خطأ عام في معالج المحفظة: {e}", exc_info=True)
        await send_error_message(update, is_callback)

def build_wallet_text(user, recent_transactions, total_transactions, sent_amount, received_amount, rating_data):
    """Build comprehensive wallet text"""
    wallet_text = f"""
💳 **محفظتي المطورة** 💳

👤 **{user['full_name']}**
💰 **الرصيد:** {user['balance']:,.2f} ريال
💳 **رقم المحفظة:** {user.get('wallet_number', 'غير محدد')}

📊 **إحصائيات المحفظة:**
📤 المرسل: **{sent_amount:,.2f}** ريال ({total_transactions} معاملة)
📥 المستلم: **{received_amount:,.2f}** ريال
💵 صافي الحركة: **{received_amount - sent_amount:+,.2f}** ريال
⭐ تقييمي: **{rating_data.get('average_rating', 0.0)}/5** ({rating_data.get('total_ratings', 0)} تقييم)

📋 **آخر المعاملات:**

"""
    
    if recent_transactions:
        for i, trans in enumerate(recent_transactions[:8], 1):
            trans_id, from_user, to_user, amount, trans_type, description, created_at = trans
            
            # Determine transaction type
            if from_user == user['id']:
                trans_icon = "📤"
                trans_text = f"أرسلت {amount:,.2f} ريال"
                if to_user:
                    try:
                        recipient = get_user(to_user)
                        if recipient:
                            trans_text += f" إلى {recipient['full_name']}"
                    except:
                        trans_text += " إلى مستخدم آخر"
            else:
                trans_icon = "📥"
                trans_text = f"استلمت {amount:,.2f} ريال"
                if from_user:
                    try:
                        sender = get_user(from_user)
                        if sender:
                            trans_text += f" من {sender['full_name']}"
                    except:
                        trans_text += " من مستخدم آخر"
            
            # Format date
            try:
                if created_at:
                    if isinstance(created_at, str):
                        date_obj = datetime.strptime(created_at, '%Y-%m-%d %H:%M:%S')
                    else:
                        date_obj = created_at
                    formatted_date = date_obj.strftime('%Y-%m-%d %H:%M')
                else:
                    formatted_date = "غير محدد"
            except:
                formatted_date = "غير محدد"
            
            wallet_text += f"{i}. {trans_icon} **{trans_text}**\n"
            wallet_text += f"   📝 {description or 'معاملة عادية'}\n"
            wallet_text += f"   🕐 {formatted_date}\n\n"
    else:
        wallet_text += "📭 لا توجد معاملات حديثة\n\n"
    
    # Add action buttons
    wallet_text += "🔧 **الإجراءات المتاحة:**\n"
    wallet_text += "• 💰 إرسال رصيد\n"
    wallet_text += "• 📊 تقارير مفصلة\n"
    wallet_text += "• ⭐ تقييماتي\n"
    wallet_text += "• 🔙 القائمة الرئيسية"
    
    return wallet_text

def build_simple_wallet_text(user):
    """Build simple wallet text in case of error"""
    return f"""
💳 **محفظتي** 💳

👤 **{user['full_name']}**
💰 **الرصيد:** {user['balance']:,.2f} ريال

❌ حدث خطأ في عرض التفاصيل الكاملة
💡 يمكنك استخدام الأزرار أدناه للوصول للميزات
"""

def create_wallet_keyboard():
    """Create wallet keyboard"""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('💰 إرسال رصيد', callback_data='send_balance')],
        [InlineKeyboardButton('📊 تقارير مفصلة', callback_data='detailed_reports')],
        [InlineKeyboardButton('⭐ تقييماتي', callback_data='my_ratings')],
        [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
    ])

def create_simple_keyboard():
    """Create simple keyboard in case of error"""
    return InlineKeyboardMarkup([[
        InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')
    ]])

async def send_error_message(update, is_callback):
    """Send error message to user"""
    error_msg = f"{EMOJIS['error']} حدث خطأ في عرض المحفظة. يرجى المحاولة مرة أخرى."
    
    try:
        if is_callback:
            await update.callback_query.edit_message_text(error_msg, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='wallet'),
                InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')
            ]]))
        else:
            await update.message.reply_text(error_msg, reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='wallet'),
                InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')
            ]]))
    except:
        pass

def setup_wallet_handlers(application):
    """Setup wallet handlers"""
    # Wallet handlers are called via callback handlers
    pass