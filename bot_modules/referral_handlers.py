#!/usr/bin/env python3
"""
Referral and Commission Handlers Module
معالجات الإحالات والعمولات
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

# Import utilities
from bot_modules.utils import get_user, get_referral_stats
from bot_modules.database import get_db_connection
from bot_modules.config import EMOJIS
from bot_modules.enhanced_error_messages import ErrorMessages

logger = logging.getLogger(__name__)

async def referral_stats_handler(update: Update, context: CallbackContext):
    """معالج إحصائيات الإحالات والعمولات"""
    try:
        query = update.callback_query
        user = get_user(query.from_user.id)
        
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # الحصول على إحصائيات الإحالات
        stats = get_referral_stats(user['id'])
        
        # إنشاء رابط الإحالة
        invite_code = user['invite_code'] if user['invite_code'] else 'غير متوفر'
        bot_username = context.bot.username or "YemenNetBot"
        referral_link = f"https://t.me/{bot_username}?start=ref_{invite_code}" if invite_code != 'غير متوفر' else "غير متوفر"
        
        referral_text = f"""
👥 **إحالاتي وعمولاتي** 👥

👤 **{user['full_name']}**
💳 محفظتك: **{user['wallet_number']}**

🎯 **إحصائيات الإحالات:**
👥 عدد الإحالات: **{stats['total_referrals']:,}** شخص
💰 إجمالي العمولات: **{stats['total_commissions']:,.2f}** ريال
🛒 إجمالي مشتريات المُحالين: **{stats['total_referred_purchases']:,.2f}** ريال
📊 عدد العمولات: **{stats['commission_count']:,}** عمولة

📅 **هذا الشهر:**
💰 العمولات المكتسبة: **{stats['monthly_commission_amount']:,.2f}** ريال
📈 عدد العمولات: **{stats['monthly_commissions']:,}** عمولة

🎫 **رابط الإحالة الخاص بك:**
`{referral_link}`

💡 **كيف تعمل العمولات:**
• احصل على **5%** من كل مشترى يقوم به أصدقاؤك
• العمولة تُضاف فوراً لرصيدك عند كل عملية شراء
• لا يوجد حد أقصى للعمولات
• شارك رابطك واكسب المزيد!

📱 **نصائح لزيادة الإحالات:**
• شارك الرابط مع الأصدقاء والعائلة
• انشر الرابط في مجموعات التواصل
• اشرح فوائد المنصة للآخرين
"""
        
        keyboard = [
            [InlineKeyboardButton('📋 نسخ رابط الإحالة', callback_data=f'copy_referral_{invite_code}')],
            [InlineKeyboardButton('💳 محفظتي', callback_data='enhanced_wallet'),
             InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(referral_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in referral stats handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض إحصائيات الإحالات.")

async def copy_referral_link_handler(update: Update, context: CallbackContext):
    """معالج نسخ رابط الإحالة"""
    try:
        query = update.callback_query
        await query.answer("📋 تم نسخ رابط الإحالة! شاركه مع أصدقائك لتحصل على عمولة 5%", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in copy referral link handler: {e}")
        await query.answer("❌ حدث خطأ في نسخ الرابط")

async def copy_share_link_handler(update: Update, context: CallbackContext):
    """معالج نسخ رابط مشاركة الشبكة"""
    try:
        query = update.callback_query
        await query.answer("📋 تم نسخ الرابط! يمكنك مشاركته الآن", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error in copy share link handler: {e}")
        await query.answer("❌ حدث خطأ في نسخ الرابط")