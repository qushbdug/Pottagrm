#!/usr/bin/env python3
"""
معالجات نظام الكوبونات للمشرف الأعلى والعملاء
Coupon System Handlers for Super Admin and Customers
"""

import logging
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, filters
from bot_modules.coupon_system import coupon_system
from bot_modules.config import *
from bot_modules.utils import get_user
from bot_modules.permissions import has_permission

logger = logging.getLogger(__name__)

# حالات المحادثة للكوبونات
COUPON_CREATE_SINGLE_VALUE = 100
COUPON_CREATE_BATCH_COUNT = 101
COUPON_CREATE_BATCH_VALUE = 102
COUPON_CREATE_BATCH_NAME = 103
COUPON_DELETE_CODE = 104
COUPON_REDEEM_CODE = 105

class CouponHandlers:
    """معالجات نظام الكوبونات"""
    
    @staticmethod
    async def coupon_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """القائمة الرئيسية لنظام الكوبونات"""
        user = get_user(update.effective_user.id)
        
        if not user or not has_permission(user['telegram_id'], 'super_admin'):
            await update.callback_query.answer("⛔ غير مصرح لك بالوصول لهذا القسم")
            return
        
        keyboard = [
            [
                InlineKeyboardButton("🎫 إنشاء كوبون فردي", callback_data="coupon_create_single"),
                InlineKeyboardButton("🎫🎫 إنشاء مجموعة كوبونات", callback_data="coupon_create_batch")
            ],
            [
                InlineKeyboardButton("📋 عرض الكوبونات النشطة", callback_data="coupon_list_active"),
                InlineKeyboardButton("📊 إحصائيات الكوبونات", callback_data="coupon_stats")
            ],
            [
                InlineKeyboardButton("🗑️ حذف/إلغاء كوبون", callback_data="coupon_delete"),
                InlineKeyboardButton("📄 سجل العمليات", callback_data="coupon_logs")
            ],
            [
                InlineKeyboardButton("🔙 العودة للقائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        text = """
🎫 **نظام إدارة الكوبونات المتقدم**

🔧 **الميزات المتاحة:**
• إنشاء كوبونات فردية أو مجموعات
• تصدير الكوبونات لملفات CSV/TXT
• حذف وإلغاء الكوبونات
• مراقبة شاملة للعمليات
• حماية متقدمة ضد التخمين

🛡️ **الأمان:**
• كوبونات بصيغة A123456789
• حد أقصى 20 محاولة خاطئة في الساعة
• تسجيل كامل لجميع العمليات
• منع التكرار والتخمين العشوائي

اختر العملية المطلوبة:
"""
        
        if update.callback_query:
            await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')
        else:
            await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')
    
    @staticmethod
    async def create_single_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بداية إنشاء كوبون فردي"""
        await update.callback_query.answer()
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="coupon_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "💰 **إنشاء كوبون فردي**\n\n"
            "أدخل قيمة الكوبون بالريال:\n"
            "مثال: 100\n\n"
            "⚠️ يجب أن تكون القيمة أكبر من 0",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return COUPON_CREATE_SINGLE_VALUE
    
    @staticmethod
    async def create_single_coupon_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة قيمة الكوبون الفردي"""
        try:
            value = float(update.message.text.strip())
            
            if value <= 0:
                await update.message.reply_text("❌ يجب أن تكون القيمة أكبر من 0")
                return COUPON_CREATE_SINGLE_VALUE
            
            # إنشاء الكوبون
            success, code, message = coupon_system.create_single_coupon(
                update.effective_user.id, value, f"كوبون فردي بقيمة {value} ريال"
            )
            
            if success:
                keyboard = [
                    [InlineKeyboardButton("🎫 إنشاء كوبون آخر", callback_data="coupon_create_single")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="coupon_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إنشاء الكوبون بنجاح!**\n\n"
                    f"🎫 **كود الكوبون:** `{code}`\n"
                    f"💰 **القيمة:** {value} ريال\n"
                    f"📅 **تاريخ الإنشاء:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"📋 **نسخ الكود:** `{code}`",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                await update.message.reply_text(f"❌ {message}")
                return COUPON_CREATE_SINGLE_VALUE
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
            return COUPON_CREATE_SINGLE_VALUE
        except Exception as e:
            logger.error(f"خطأ في إنشاء الكوبون الفردي: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام")
        
        return ConversationHandler.END
    
    @staticmethod
    async def create_batch_coupons_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بداية إنشاء مجموعة كوبونات"""
        await update.callback_query.answer()
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="coupon_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🎫🎫 **إنشاء مجموعة كوبونات**\n\n"
            "أدخل عدد الكوبونات المطلوب إنشاؤها:\n"
            "مثال: 100\n\n"
            "⚠️ الحد الأقصى: 1000 كوبون في المرة الواحدة\n"
            "⚠️ الحد الأدنى: 2 كوبون",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return COUPON_CREATE_BATCH_COUNT
    
    @staticmethod
    async def create_batch_coupons_count(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة عدد الكوبونات في المجموعة"""
        try:
            count = int(update.message.text.strip())
            
            if count < 2:
                await update.message.reply_text("❌ يجب أن يكون العدد أكبر من 1")
                return COUPON_CREATE_BATCH_COUNT
            
            if count > 1000:
                await update.message.reply_text("❌ لا يمكن إنشاء أكثر من 1000 كوبون في المرة الواحدة")
                return COUPON_CREATE_BATCH_COUNT
            
            context.user_data['batch_count'] = count
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="coupon_main")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"💰 **قيمة الكوبونات**\n\n"
                f"عدد الكوبونات: {count}\n\n"
                f"أدخل قيمة كل كوبون بالريال:\n"
                f"مثال: 200\n\n"
                f"⚠️ يجب أن تكون القيمة أكبر من 0",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return COUPON_CREATE_BATCH_VALUE
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
            return COUPON_CREATE_BATCH_COUNT
        except Exception as e:
            logger.error(f"خطأ في معالجة عدد الكوبونات: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام")
            return ConversationHandler.END
    
    @staticmethod
    async def create_batch_coupons_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة قيمة الكوبونات في المجموعة"""
        try:
            value = float(update.message.text.strip())
            
            if value <= 0:
                await update.message.reply_text("❌ يجب أن تكون القيمة أكبر من 0")
                return COUPON_CREATE_BATCH_VALUE
            
            context.user_data['batch_value'] = value
            count = context.user_data['batch_count']
            
            keyboard = [
                [InlineKeyboardButton("⏭️ تخطي", callback_data="coupon_batch_skip_name")],
                [InlineKeyboardButton("❌ إلغاء", callback_data="coupon_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"📝 **اسم المجموعة (اختياري)**\n\n"
                f"عدد الكوبونات: {count}\n"
                f"قيمة كل كوبون: {value} ريال\n"
                f"إجمالي القيمة: {count * value} ريال\n\n"
                f"أدخل اسماً وصفياً للمجموعة:\n"
                f"مثال: كوبونات الموزعين - يناير 2025\n\n"
                f"أو اضغط تخطي للمتابعة بدون اسم",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
            return COUPON_CREATE_BATCH_NAME
            
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح")
            return COUPON_CREATE_BATCH_VALUE
        except Exception as e:
            logger.error(f"خطأ في معالجة قيمة الكوبونات: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام")
            return ConversationHandler.END
    
    @staticmethod
    async def create_batch_coupons_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة اسم المجموعة وإنشاء الكوبونات"""
        try:
            batch_name = update.message.text.strip() if update.message else None
            count = context.user_data['batch_count']
            value = context.user_data['batch_value']
            
            await update.message.reply_text(
                f"⏳ **جاري إنشاء {count} كوبون...**\n\n"
                f"يرجى الانتظار، قد تستغرق العملية بضع ثوانٍ..."
            )
            
            # إنشاء المجموعة
            success, coupons, batch_id, message = coupon_system.create_batch_coupons(
                update.effective_user.id, count, value, batch_name
            )
            
            if success:
                # تصدير الكوبونات
                csv_content = coupon_system.export_coupons_to_csv(coupons, batch_id, value)
                txt_content = coupon_system.export_coupons_to_txt(coupons, batch_id, value)
                
                # إرسال ملف CSV
                csv_file = io.BytesIO(csv_content.encode('utf-8-sig'))
                csv_file.name = f"coupons_{batch_id}.csv"
                
                # إرسال ملف TXT
                txt_file = io.BytesIO(txt_content.encode('utf-8'))
                txt_file.name = f"coupons_{batch_id}.txt"
                
                keyboard = [
                    [InlineKeyboardButton("🎫 إنشاء مجموعة أخرى", callback_data="coupon_create_batch")],
                    [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="coupon_main")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"✅ **تم إنشاء المجموعة بنجاح!**\n\n"
                    f"📊 **تفاصيل المجموعة:**\n"
                    f"🆔 معرف المجموعة: `{batch_id}`\n"
                    f"📝 اسم المجموعة: {batch_name or 'غير محدد'}\n"
                    f"🎫 عدد الكوبونات: {count}\n"
                    f"💰 قيمة كل كوبون: {value} ريال\n"
                    f"💎 إجمالي القيمة: {count * value} ريال\n\n"
                    f"📄 سيتم إرسال الملفات في الرسائل التالية...",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                
                # إرسال الملفات
                await update.message.reply_document(
                    document=csv_file,
                    filename=f"كوبونات_{batch_id}.csv",
                    caption="📊 ملف CSV للكوبونات (لفتح في Excel)"
                )
                
                await update.message.reply_document(
                    document=txt_file,
                    filename=f"كوبونات_{batch_id}.txt",
                    caption="📄 ملف نصي للكوبونات (للطباعة أو المشاركة)"
                )
                
            else:
                await update.message.reply_text(f"❌ {message}")
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء مجموعة الكوبونات: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام")
        
        return ConversationHandler.END
    
    @staticmethod
    async def skip_batch_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تخطي اسم المجموعة"""
        await update.callback_query.answer()
        return await CouponHandlers.create_batch_coupons_name(update, context)
    
    @staticmethod
    async def delete_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بداية حذف كوبون"""
        await update.callback_query.answer()
        
        keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="coupon_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            "🗑️ **حذف/إلغاء كوبون**\n\n"
            "أدخل كود الكوبون المراد حذفه:\n"
            "مثال: A123456789\n\n"
            "⚠️ لا يمكن حذف الكوبونات المستخدمة\n"
            "⚠️ العملية غير قابلة للتراجع",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return COUPON_DELETE_CODE
    
    @staticmethod
    async def delete_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة حذف الكوبون"""
        try:
            code = update.message.text.strip().upper()
            
            # التحقق من صيغة الكود
            if not (code.startswith('A') and len(code) == 9 and code[1:].isdigit()):
                await update.message.reply_text("❌ صيغة الكود غير صحيحة. يجب أن يكون بصيغة A123456789")
                return COUPON_DELETE_CODE
            
            # محاولة حذف الكوبون
            success, message = coupon_system.delete_coupon(update.effective_user.id, code)
            
            keyboard = [
                [InlineKeyboardButton("🗑️ حذف كوبون آخر", callback_data="coupon_delete")],
                [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="coupon_main")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )
            
        except Exception as e:
            logger.error(f"خطأ في حذف الكوبون: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام")
        
        return ConversationHandler.END
    
    @staticmethod
    async def redeem_coupon_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """بداية استرداد كوبون (للعملاء)"""
        if update.callback_query:
            await update.callback_query.answer()
            
            keyboard = [[InlineKeyboardButton("❌ إلغاء", callback_data="main_menu")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.callback_query.edit_message_text(
                "🎫 **استرداد كوبون**\n\n"
                "أدخل كود الكوبون للحصول على الرصيد:\n"
                "مثال: A123456789\n\n"
                "🛡️ **تحذير أمني:**\n"
                "• الحد الأقصى: 20 محاولة خاطئة في الساعة\n"
                "• عند تجاوز الحد سيتم منعك مؤقتاً\n"
                "• تأكد من صحة الكود قبل الإدخال",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                "🎫 **استرداد كوبون**\n\n"
                "أدخل كود الكوبون:",
                parse_mode='Markdown'
            )
        
        return COUPON_REDEEM_CODE
    
    @staticmethod
    async def redeem_coupon_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة استرداد الكوبون"""
        try:
            code = update.message.text.strip().upper()
            user_id = update.effective_user.id
            
            # التحقق من صيغة الكود
            if not (code.startswith('A') and len(code) == 9 and code[1:].isdigit()):
                await update.message.reply_text(
                    "❌ صيغة الكود غير صحيحة\n\n"
                    "يجب أن يكون الكود بصيغة: A123456789\n"
                    "مثال: A987654321"
                )
                return COUPON_REDEEM_CODE
            
            # محاولة استرداد الكوبون
            success, value, message = coupon_system.redeem_coupon(user_id, code)
            
            if success:
                # الحصول على الرصيد الجديد
                user = get_user(user_id)
                new_balance = user['balance'] if user else 0
                
                keyboard = [
                    [InlineKeyboardButton("🎫 استرداد كوبون آخر", callback_data="redeem_coupon")],
                    [InlineKeyboardButton("💰 عرض الرصيد", callback_data="wallet")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    f"🎉 **تم استرداد الكوبون بنجاح!**\n\n"
                    f"🎫 كود الكوبون: `{code}`\n"
                    f"💰 المبلغ المضاف: {value} ريال\n"
                    f"💎 رصيدك الحالي: {new_balance} ريال\n"
                    f"📅 التاريخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"شكراً لك! 🙏",
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
            else:
                # في حالة الفشل، عرض خيارات المساعدة
                keyboard = [
                    [InlineKeyboardButton("🔄 محاولة مرة أخرى", callback_data="redeem_coupon")],
                    [InlineKeyboardButton("📞 تواصل مع الدعم", callback_data="contact_support")],
                    [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="main_menu")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await update.message.reply_text(
                    message,
                    reply_markup=reply_markup
                )
            
        except Exception as e:
            logger.error(f"خطأ في استرداد الكوبون: {e}")
            await update.message.reply_text("❌ حدث خطأ في النظام، حاول مرة أخرى")
        
        return ConversationHandler.END
    
    @staticmethod
    async def show_active_coupons(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض الكوبونات النشطة"""
        await update.callback_query.answer()
        
        user = get_user(update.effective_user.id)
        admin_id = user['telegram_id'] if has_permission(user['telegram_id'], 'super_admin') else None
        
        coupons = coupon_system.get_active_coupons(admin_id, 20)
        
        if not coupons:
            text = "📭 **لا توجد كوبونات نشطة حالياً**"
        else:
            text = f"🎫 **الكوبونات النشطة ({len(coupons)}):**\n\n"
            
            for i, coupon in enumerate(coupons, 1):
                created_date = datetime.fromisoformat(coupon['created_at']).strftime('%m-%d %H:%M')
                text += f"`{i:2d}.` `{coupon['code']}` - {coupon['value']} ريال - {created_date}\n"
            
            if len(coupons) == 20:
                text += "\n📝 *عرض أول 20 كوبون فقط*"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="coupon_list_active")],
            [InlineKeyboardButton("🔙 العودة", callback_data="coupon_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_coupon_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض إحصائيات الكوبونات"""
        await update.callback_query.answer()
        
        user = get_user(update.effective_user.id)
        admin_id = user['telegram_id'] if has_permission(user['telegram_id'], 'super_admin') else None
        
        stats = coupon_system.get_admin_coupons_stats(admin_id)
        
        if not stats:
            text = "❌ **خطأ في تحميل الإحصائيات**"
        else:
            usage_percentage = (stats['used_coupons'] / stats['total_coupons'] * 100) if stats['total_coupons'] > 0 else 0
            
            text = f"""
📊 **إحصائيات نظام الكوبونات**

🎫 **الكوبونات:**
• إجمالي الكوبونات: {stats['total_coupons']}
• المستخدمة: {stats['used_coupons']} ({usage_percentage:.1f}%)
• النشطة غير المستخدمة: {stats['active_unused']}
• الملغاة: {stats['cancelled_coupons']}

💰 **القيم المالية:**
• إجمالي قيمة الكوبونات: {stats['total_value']} ريال
• القيمة المستردة: {stats['redeemed_value']} ريال
• القيمة المتبقية: {stats['total_value'] - stats['redeemed_value']} ريال

📦 **المجموعات:**
• إجمالي المجموعات: {stats['total_batches']}

📅 **آخر تحديث:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث الإحصائيات", callback_data="coupon_stats")],
            [InlineKeyboardButton("📄 عرض السجلات", callback_data="coupon_logs")],
            [InlineKeyboardButton("🔙 العودة", callback_data="coupon_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def show_coupon_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """عرض سجل عمليات الكوبونات"""
        await update.callback_query.answer()
        
        logs = coupon_system.get_coupon_logs(20)
        
        if not logs:
            text = "📭 **لا توجد عمليات مسجلة**"
        else:
            text = f"📄 **سجل عمليات الكوبونات (آخر 20):**\n\n"
            
            for log in logs:
                timestamp = datetime.fromisoformat(log['timestamp']).strftime('%m-%d %H:%M')
                action_emoji = {
                    'CREATED': '✅',
                    'BATCH_CREATED': '📦',
                    'REDEEMED': '🎉',
                    'CANCELLED': '🗑️'
                }.get(log['action'], '📝')
                
                text += f"`{timestamp}` {action_emoji} `{log['coupon_code'][:12]}` - {log['user_name'] or 'غير معروف'}\n"
        
        keyboard = [
            [InlineKeyboardButton("🔄 تحديث", callback_data="coupon_logs")],
            [InlineKeyboardButton("🔙 العودة", callback_data="coupon_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            text,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    @staticmethod
    async def cancel_coupon_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء محادثة الكوبونات"""
        if update.callback_query:
            await update.callback_query.answer()
            return await CouponHandlers.coupon_main_menu(update, context)
        else:
            await update.message.reply_text("تم إلغاء العملية")
            return ConversationHandler.END

# معالجات المحادثة للكوبونات
from telegram.ext import CallbackQueryHandler

COUPON_CONVERSATION_HANDLERS = {
    'create_single_coupon': ConversationHandler(
        entry_points=[CallbackQueryHandler(CouponHandlers.create_single_coupon_start, pattern='^coupon_create_single$')],
        states={
            COUPON_CREATE_SINGLE_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.create_single_coupon_value)]
        },
        fallbacks=[CallbackQueryHandler(CouponHandlers.cancel_coupon_conversation, pattern='^coupon_main$')],
        persistent=True,
        name="create_single_coupon"
    ),
    
    'create_batch_coupons': ConversationHandler(
        entry_points=[CallbackQueryHandler(CouponHandlers.create_batch_coupons_start, pattern='^coupon_create_batch$')],
        states={
            COUPON_CREATE_BATCH_COUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.create_batch_coupons_count)],
            COUPON_CREATE_BATCH_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.create_batch_coupons_value)],
            COUPON_CREATE_BATCH_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.create_batch_coupons_name),
                CallbackQueryHandler(CouponHandlers.skip_batch_name, pattern='^coupon_batch_skip_name$')
            ]
        },
        fallbacks=[CallbackQueryHandler(CouponHandlers.cancel_coupon_conversation, pattern='^coupon_main$')],
        persistent=True,
        name="create_batch_coupons"
    ),
    
    'delete_coupon': ConversationHandler(
        entry_points=[CallbackQueryHandler(CouponHandlers.delete_coupon_start, pattern='^coupon_delete$')],
        states={
            COUPON_DELETE_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.delete_coupon_code)]
        },
        fallbacks=[CallbackQueryHandler(CouponHandlers.cancel_coupon_conversation, pattern='^coupon_main$')],
        persistent=True,
        name="delete_coupon"
    ),
    
    'redeem_coupon_new': ConversationHandler(
        entry_points=[CallbackQueryHandler(CouponHandlers.redeem_coupon_start, pattern='^redeem_coupon$')],
        states={
            COUPON_REDEEM_CODE: [MessageHandler(filters.TEXT & ~filters.COMMAND, CouponHandlers.redeem_coupon_code)]
        },
        fallbacks=[CallbackQueryHandler(CouponHandlers.cancel_coupon_conversation, pattern='^main_menu$')],
        persistent=True,
        name="redeem_coupon_new"
    )
}

# معالجات الاستدعاء للكوبونات
COUPON_CALLBACKS = {
    'coupon_main': CouponHandlers.coupon_main_menu,
    'coupon_create_single': CouponHandlers.create_single_coupon_start,
    'coupon_create_batch': CouponHandlers.create_batch_coupons_start,
    'coupon_batch_skip_name': CouponHandlers.skip_batch_name,
    'coupon_delete': CouponHandlers.delete_coupon_start,
    'coupon_list_active': CouponHandlers.show_active_coupons,
    'coupon_stats': CouponHandlers.show_coupon_stats,
    'coupon_logs': CouponHandlers.show_coupon_logs,
    'redeem_coupon': CouponHandlers.redeem_coupon_start,
}