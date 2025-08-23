#!/usr/bin/env python3
"""
Show Networks Module - Yemen Net Bot
مسؤول عن عرض الشبكات في واجهة تيليجرام
يفصل منطق العرض عن منطق قاعدة البيانات
"""

import logging
from typing import List, Dict, Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS
from bot_modules.db_networks import (
    get_all_networks, get_network_by_id, get_network_categories,
    search_networks, get_networks_by_supplier, NetworkNotFoundError
)
from bot_modules.callback_utils import create_callback
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

class NetworkDisplayError(Exception):
    """استثناء يرمى عند خطأ في عرض الشبكات"""
    pass

class TelegramNetworkDisplay:
    """كلاس مسؤول عن عرض الشبكات في واجهة تيليجرام"""
    
    @staticmethod
    def format_network_info(network: Dict) -> str:
        """
        تنسيق معلومات الشبكة للعرض
        
        Args:
            network: بيانات الشبكة
            
        Returns:
            نص منسق للعرض
        """
        try:
            name = network.get('name', 'اسم غير محدد')
            provider = network.get('provider', 'مزود غير محدد')
            location = network.get('location', 'غير محدد')
            description = network.get('description', 'شبكة إنترنت موثوقة وسريعة')
            categories_count = network.get('categories_count', 0)
            min_price = network.get('min_price')
            max_price = network.get('max_price')
            available_cards = network.get('available_cards', 0)
            
            # تنسيق نطاق الأسعار
            if min_price and max_price:
                if min_price == max_price:
                    price_range = f"{min_price:,.0f} ريال"
                else:
                    price_range = f"{min_price:,.0f} - {max_price:,.0f} ريال"
            elif min_price:
                price_range = f"{min_price:,.0f} ريال"
            else:
                price_range = "غير محدد"
            
            # تحديد حالة التوفر
            if categories_count > 0:
                availability_status = "✅ متوفر"
                cards_info = f"📦 متاح: {available_cards} كرت"
            else:
                availability_status = "❌ لا توجد فئات"
                cards_info = "📦 متاح: 0 كرت"
            
            formatted_text = f"""
🌐 **{name}**
👤 {provider}
📍 {location}
💳 {categories_count} فئة | 💰 {price_range}
{cards_info}
{availability_status}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            return formatted_text.strip()
            
        except Exception as e:
            logger.error(f"خطأ في تنسيق معلومات الشبكة: {e}", exc_info=True)
            return f"🌐 **{network.get('name', 'شبكة غير معروفة')}** - خطأ في العرض"
    
    @staticmethod
    def format_network_details(network: Dict, categories: List[Dict], user: Dict) -> str:
        """
        تنسيق تفاصيل الشبكة مع فئات الكروت
        
        Args:
            network: بيانات الشبكة
            categories: فئات الكروت
            user: بيانات المستخدم
            
        Returns:
            نص مفصل للعرض
        """
        try:
            name = network.get('name', 'اسم غير محدد')
            provider = network.get('provider', 'مزود غير محدد')
            location = network.get('location', 'غير محدد')
            description = network.get('description', 'شبكة إنترنت موثوقة وسريعة')
            
            text = f"""
🏢 **{name}** - {provider}

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

📝 **الوصف:**
{description}

📍 **الموقع:** {location}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

💳 **فئات الكروت المتاحة والأسعار:**

"""
            
            if categories:
                for category in categories:
                    cat_name = category.get('name', 'اسم غير محدد')
                    cat_value = category.get('value', 0)
                    cat_price = category.get('price', 0)
                    cat_stock = category.get('stock_count', 0)
                    available_cards = category.get('available_cards', 0)
                    
                    # تنسيق القيمة
                    if cat_value >= 1024:
                        value_text = f"{cat_value/1024:.0f} جيجا"
                    elif cat_value >= 100:
                        value_text = f"{cat_value} ميجا"
                    else:
                        value_text = f"{cat_value} MB"
                    
                    # تحديد حالة التوفر
                    if available_cards > 0:
                        availability = "✅ متوفر"
                        stock_info = f"({available_cards} كرت)"
                    else:
                        availability = "❌ نفذ"
                        stock_info = "(نفذ)"
                    
                    text += f"""
🎫 **{cat_name}** ({value_text})
💰 **{cat_price:,.0f}** ريال
📦 {availability} {stock_info}

"""
            else:
                text += "❌ لا توجد فئات متاحة حالياً\n\n"
            
            return text.strip()
            
        except Exception as e:
            logger.error(f"خطأ في تنسيق تفاصيل الشبكة: {e}", exc_info=True)
            return f"🌐 **{network.get('name', 'شبكة غير معروفة')}** - خطأ في عرض التفاصيل"
    
    @staticmethod
    def create_networks_keyboard(networks: List[Dict], show_details: bool = True) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح للشبكات
        
        Args:
            networks: قائمة الشبكات
            show_details: هل تظهر أزرار التفاصيل
            
        Returns:
            لوحة مفاتيح
        """
        try:
            keyboard = []
            
            for network in networks:
                net_id = network.get('id')
                name = network.get('name', 'شبكة غير معروفة')
                categories_count = network.get('categories_count', 0)
                
                if categories_count > 0:
                    # شبكة تحتوي على فئات - إظهار زر الشراء
                    button_text = f"🛒 شراء من {name}"
                    callback_data = create_callback('buy_from_network', network_id=net_id)
                else:
                    # شبكة بدون فئات - إظهار زر العرض فقط
                    button_text = f"👁️ عرض {name} (لا توجد فئات)"
                    callback_data = create_callback('network', network_id=net_id)
                
                keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # إضافة أزرار التنقل والبحث
            navigation_row = []
            if show_details:
                navigation_row.append(InlineKeyboardButton('🔍 البحث عن شبكة', callback_data='search_networks'))
            
            navigation_row.append(InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu'))
            
            if navigation_row:
                keyboard.append(navigation_row)
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء لوحة مفاتيح الشبكات: {e}", exc_info=True)
            # لوحة مفاتيح بديلة في حالة الخطأ
            return InlineKeyboardMarkup([[
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
    
    @staticmethod
    def create_network_details_keyboard(network_id: int, categories: List[Dict]) -> InlineKeyboardMarkup:
        """
        إنشاء لوحة مفاتيح لتفاصيل الشبكة
        
        Args:
            network_id: معرف الشبكة
            categories: فئات الكروت
            
        Returns:
            لوحة مفاتيح
        """
        try:
            keyboard = []
            
            # أزرار شراء الفئات
            for category in categories:
                cat_id = category.get('id')
                cat_name = category.get('name', 'فئة غير معروفة')
                cat_price = category.get('price', 0)
                available_cards = category.get('available_cards', 0)
                
                if available_cards > 0:
                    button_text = f"🛒 شراء {cat_name} - {cat_price:,.0f} ريال"
                    callback_data = create_callback('buy_card', category_id=cat_id)
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=callback_data)])
            
            # أزرار التنقل
            keyboard.append([
                InlineKeyboardButton('🔙 عودة للشبكات', callback_data='search_networks'),
                InlineKeyboardButton('🔍 بحث جديد', callback_data='customer_search_networks')
            ])
            
            keyboard.append([
                InlineKeyboardButton('💰 شحن الرصيد', callback_data='deposit_balance'),
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ])
            
            return InlineKeyboardMarkup(keyboard)
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء لوحة مفاتيح تفاصيل الشبكة: {e}", exc_info=True)
            # لوحة مفاتيح بديلة في حالة الخطأ
            return InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 عودة', callback_data='search_networks'),
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])


# دوال العرض الرئيسية
async def show_all_networks(update: Update, context: CallbackContext, user_message: str = None):
    """
    عرض جميع الشبكات المتاحة
    
    Args:
        update: تحديث تيليجرام
        context: سياق البوت
        user_message: رسالة إضافية للمستخدم
    """
    try:
        logger.info("بدء عرض جميع الشبكات")
        
        # التحقق من المستخدم
        user = get_user(update.effective_user.id)
        if not user:
            error_msg = f"{EMOJIS['error']} يرجى التسجيل أولاً /start"
            if update.callback_query:
                await update.callback_query.edit_message_text(error_msg)
            else:
                await update.message.reply_text(error_msg)
            return
        
        update_user_activity(user['id'])
        
        # جلب الشبكات من قاعدة البيانات
        networks = get_all_networks()
        
        # تحضير النص
        if user_message:
            message_text = user_message + "\n\n"
        else:
            message_text = ""
        
        message_text += f"""
🛒 **شراء كروت الإنترنت** 🛒

👤 {user['full_name']}
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 إجمالي الشبكات المتاحة: **{len(networks)}** شبكة

🌐 **الشبكات المتاحة:**

"""
        
        if networks:
            # عرض الشبكات
            networks_with_categories = 0
            networks_without_categories = 0
            
            for network in networks:
                message_text += TelegramNetworkDisplay.format_network_info(network)
                if network.get('categories_count', 0) > 0:
                    networks_with_categories += 1
                else:
                    networks_without_categories += 1
            
            logger.info(f"الشبكات مع فئات كروت: {networks_with_categories}, بدون فئات: {networks_without_categories}")
            
            # إنشاء لوحة المفاتيح
            keyboard = TelegramNetworkDisplay.create_networks_keyboard(networks)
            
        else:
            message_text += f"""
❌ لا توجد شبكات متاحة حالياً

💡 **نصائح:**
• تأكد من وجود شبكات نشطة في النظام
• جرب البحث باستخدام كلمات مختلفة
• تواصل مع الإدارة إذا استمرت المشكلة

🔍 **للبحث عن شبكات محددة:**
اكتب اسم الشبكة أو اسم المزود أو المدينة
"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('🔍 البحث عن شبكة', callback_data='customer_search_networks'),
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
        
        # إرسال الرسالة
        if update.callback_query:
            await update.callback_query.edit_message_text(
                message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                message_text,
                reply_markup=keyboard,
                parse_mode='Markdown'
            )
        
        logger.info(f"تم عرض {len(networks)} شبكة بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في عرض الشبكات: {e}", exc_info=True)
        error_msg = f"{EMOJIS['error']} حدث خطأ في عرض الشبكات. يرجى المحاولة مرة أخرى."
        
        try:
            if update.callback_query:
                await update.callback_query.edit_message_text(
                    error_msg,
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='search_networks'),
                        InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
                    ]])
                )
            else:
                await update.message.reply_text(error_msg)
        except Exception as send_error:
            logger.error(f"خطأ في إرسال رسالة الخطأ: {send_error}", exc_info=True)


async def show_network_details(update: Update, context: CallbackContext, network_id: str):
    """
    عرض تفاصيل شبكة معينة
    
    Args:
        update: تحديث تيليجرام
        context: سياق البوت
        network_id: معرف الشبكة
    """
    try:
        logger.info(f"بدء عرض تفاصيل الشبكة {network_id}")
        
        # التحقق من المستخدم
        user = get_user(update.effective_user.id)
        if not user:
            await update.callback_query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # تحويل معرف الشبكة إلى رقم
        try:
            network_id_int = int(network_id)
        except ValueError:
            await update.callback_query.edit_message_text(
                f"{EMOJIS['error']} معرف الشبكة غير صحيح",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='search_networks')
                ]])
            )
            return
        
        # جلب بيانات الشبكة
        try:
            network = get_network_by_id(network_id_int)
            categories = get_network_categories(network_id_int)
        except NetworkNotFoundError:
            await update.callback_query.edit_message_text(
                "❌ الشبكة غير موجودة أو غير متاحة",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton('🔙 العودة', callback_data='search_networks')
                ]])
            )
            return
        
        # تنسيق الرسالة
        message_text = TelegramNetworkDisplay.format_network_details(network, categories, user)
        
        # إنشاء لوحة المفاتيح
        keyboard = TelegramNetworkDisplay.create_network_details_keyboard(network_id_int, categories)
        
        # إرسال الرسالة
        await update.callback_query.edit_message_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"تم عرض تفاصيل الشبكة {network['name']} بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في عرض تفاصيل الشبكة {network_id}: {e}", exc_info=True)
        await update.callback_query.edit_message_text(
            f"{EMOJIS['error']} حدث خطأ في عرض تفاصيل الشبكة",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔙 العودة', callback_data='search_networks'),
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
        )


async def show_search_results(update: Update, context: CallbackContext, search_term: str, search_type: str = 'all'):
    """
    عرض نتائج البحث في الشبكات
    
    Args:
        update: تحديث تيليجرام
        context: سياق البوت
        search_term: مصطلح البحث
        search_type: نوع البحث
    """
    try:
        logger.info(f"بدء البحث عن '{search_term}' نوع البحث: {search_type}")
        
        # التحقق من المستخدم
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        # البحث في الشبكات
        networks = search_networks(search_term, search_type)
        
        # تحضير النص
        message_text = f"""
🔍 **نتائج البحث عن: "{search_term}"** 🔍

👤 {user['full_name']}
💰 رصيدك: **{user['balance']:,.2f}** ريال

📊 تم العثور على **{len(networks)}** شبكة

🌐 **النتائج:**

"""
        
        if networks:
            for network in networks:
                message_text += TelegramNetworkDisplay.format_network_info(network)
            
            # إنشاء لوحة المفاتيح
            keyboard = TelegramNetworkDisplay.create_networks_keyboard(networks)
            
        else:
            message_text += f"""
❌ لم يتم العثور على شبكات تطابق البحث

💡 **اقتراحات:**
• جرب البحث بكلمات أخرى
• تأكد من كتابة الاسم بشكل صحيح
• جرب البحث باسم المزود أو المدينة

🔍 **للبحث مرة أخرى:**
اكتب اسم الشبكة أو اسم المزود أو المدينة
"""
            
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton('🔍 بحث جديد', callback_data='customer_search_networks'),
                InlineKeyboardButton('🌐 عرض جميع الشبكات', callback_data='search_networks')
            ], [
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
        
        # إرسال الرسالة
        await update.message.reply_text(
            message_text,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
        
        logger.info(f"تم عرض {len(networks)} نتيجة بحث بنجاح")
        
    except Exception as e:
        logger.error(f"خطأ في عرض نتائج البحث: {e}", exc_info=True)
        await update.message.reply_text(
            f"{EMOJIS['error']} حدث خطأ في البحث. يرجى المحاولة مرة أخرى.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton('🔄 إعادة المحاولة', callback_data='customer_search_networks'),
                InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')
            ]])
        )