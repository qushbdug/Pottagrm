#!/usr/bin/env python3
"""
Simple Unified Card Upload System for Yemen Net Bot
الطريقة الموحدة والبسيطة لرفع الكروت

Features:
- Only for suppliers and admins (no agents)
- Upload text file with card numbers (8-14 digits)
- Select card value from predefined buttons
- Enter card size description
- Simple and conflict-free

Author: Software Engineer
Version: 1.0.0 (Simple & Unified)
"""

import logging
import os
import re
from datetime import datetime
from typing import List, Optional

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# Predefined card values
CARD_VALUES = [200, 300, 500, 1000, 2000, 3000, 5000, 10000]

# =============================================================================
# SIMPLE UNIFIED CARD UPLOAD SYSTEM
# =============================================================================

async def simple_upload_cards_handler(update: Update, context: CallbackContext):
    """
    ✅ SIMPLE: Unified card upload for suppliers and admins only
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # ✅ RESTRICTION: Only suppliers and admins (NO AGENTS)
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(
                f"{EMOJIS['error']} **غير مسموح**\n\n"
                f"رفع الكروت متاح فقط للمزودين والمشرفين.\n"
                f"الوكلاء لا يمكنهم رفع الكروت."
            )
            return
        
        update_user_activity(user['id'])
        
        # Get user's networks
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] in ['admin', 'super_admin']:
            # Admins can upload to any network
            cursor.execute('''
                SELECT id, name, provider, location 
                FROM networks 
                WHERE is_active = 1 AND is_approved = 1
                ORDER BY name
            ''')
        else:
            # Suppliers can only upload to their own networks
            cursor.execute('''
                SELECT id, name, provider, location 
                FROM networks 
                WHERE supplier_id = ? AND is_active = 1 AND is_approved = 1
                ORDER BY name
            ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        if not networks:
            await query.edit_message_text(
                f"{EMOJIS['error']} **لا توجد شبكات متاحة**\n\n"
                f"{'تحتاج لإنشاء شبكة أولاً.' if user['role'] == 'supplier' else 'لا توجد شبكات في النظام.'}"
            )
            return
        
        # Show network selection
        welcome_text = f"""
📤 **رفع الكروت - النظام الموحد**

👤 **{user['full_name']}** ({user['role']})

📋 **خطوات رفع الكروت:**
1️⃣ اختر الشبكة
2️⃣ ارفع ملف نصي يحتوي على أرقام الكروت
3️⃣ اختر قيمة الكروت
4️⃣ أدخل وصف الكرت (مثل: كرت 2 جيجا)

🌐 **اختر الشبكة التي تريد رفع الكروت إليها:**
"""
        
        keyboard = []
        for network in networks:
            keyboard.append([
                InlineKeyboardButton(
                    f"📡 {network['name']} - {network['provider']}", 
                    callback_data=f'simple_upload_to_{network["id"]}'
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton('🔙 العودة', callback_data='supplier_panel' if user['role'] == 'supplier' else 'admin_panel')
        ])
        
        await query.edit_message_text(
            welcome_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in simple_upload_cards_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض خيارات رفع الكروت.")

async def simple_upload_to_network_handler(update: Update, context: CallbackContext, network_id: str):
    """Handle upload to specific network"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(f"{EMOJIS['error']} غير مسموح")
            return
        
        # Verify network access
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] in ['admin', 'super_admin']:
            cursor.execute('SELECT * FROM networks WHERE id = ?', (network_id,))
        else:
            cursor.execute('SELECT * FROM networks WHERE id = ? AND supplier_id = ?', (network_id, user['id']))
        
        network = cursor.fetchone()
        conn.close()
        
        if not network:
            await query.edit_message_text(f"{EMOJIS['error']} ليس لديك صلاحية للرفع إلى هذه الشبكة.")
            return
        
        # Store network_id in context
        context.user_data['upload_network_id'] = network_id
        context.user_data['upload_step'] = 'file'
        
        upload_instructions = f"""
📤 **رفع الكروت إلى: {network['name']}**

📝 **الخطوة 1: رفع الملف**

📋 **المطلوب:**
- ملف نصي (.txt) يحتوي على أرقام الكروت
- كل رقم في سطر منفصل
- أرقام الكروت يجب أن تكون من 8 إلى 14 رقم

✅ **مثال على محتوى الملف:**
```
12345678
987654321012
55667788990011
44556677889900
```

📎 **ارفع الملف الآن:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='simple_upload_cards')],
            [InlineKeyboardButton('🔙 العودة', callback_data='simple_upload_cards')]
        ]
        
        await query.edit_message_text(
            upload_instructions,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in simple_upload_to_network_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في إعداد رفع الكروت.")

async def simple_process_file_upload(update: Update, context: CallbackContext):
    """Process uploaded file with card numbers"""
    try:
        # Check if user is in upload mode
        if not context.user_data.get('upload_step') == 'file':
            return
        
        user = get_user(update.message.from_user.id)
        if not user or user['role'] not in ['supplier', 'admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} غير مسموح")
            return
        
        # Check if file is provided
        if not update.message.document:
            await update.message.reply_text(
                f"{EMOJIS['error']} **يرجى رفع ملف نصي**\n\n"
                f"📎 ارفع ملف نصي (.txt) يحتوي على أرقام الكروت"
            )
            return
        
        file = update.message.document
        
        # Validate file type
        if not file.file_name.lower().endswith('.txt'):
            await update.message.reply_text(
                f"{EMOJIS['error']} **نوع ملف غير صحيح**\n\n"
                f"📎 يجب أن يكون الملف نصي (.txt) فقط"
            )
            return
        
        # Download and read file
        file_obj = await context.bot.get_file(file.file_id)
        file_content = await file_obj.download_as_bytearray()
        
        try:
            # Decode file content
            content = file_content.decode('utf-8')
        except UnicodeDecodeError:
            try:
                content = file_content.decode('utf-8-sig')  # Try with BOM
            except UnicodeDecodeError:
                await update.message.reply_text(
                    f"{EMOJIS['error']} **خطأ في قراءة الملف**\n\n"
                    f"تأكد من أن الملف مُحفوظ بترميز UTF-8"
                )
                return
        
        # Extract card numbers
        lines = content.strip().split('\n')
        card_numbers = []
        invalid_lines = []
        
        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            # Validate card number (8-14 digits only)
            if re.match(r'^\d{8,14}$', line):
                card_numbers.append(line)
            else:
                invalid_lines.append(f"السطر {i}: {line}")
        
        if not card_numbers:
            await update.message.reply_text(
                f"{EMOJIS['error']} **لا توجد أرقام كروت صحيحة**\n\n"
                f"تأكد من أن الملف يحتوي على أرقام من 8 إلى 14 رقم"
            )
            return
        
        # Check for duplicates
        unique_cards = list(set(card_numbers))
        duplicates_count = len(card_numbers) - len(unique_cards)
        
        # Store cards in context
        context.user_data['upload_cards'] = unique_cards
        context.user_data['upload_step'] = 'value'
        
        # Show validation results and value selection
        validation_text = f"""
✅ **تم قراءة الملف بنجاح**

📊 **نتائج المعالجة:**
📝 إجمالي الأسطر: {len(lines)}
✅ كروت صحيحة: {len(unique_cards)}
❌ أسطر غير صحيحة: {len(invalid_lines)}
🔄 مكررات تم حذفها: {duplicates_count}

📝 **الخطوة 2: اختر قيمة الكروت**

💰 **اختر القيمة المناسبة لجميع الكروت:**
"""
        
        if invalid_lines and len(invalid_lines) <= 5:
            validation_text += f"\n⚠️ **الأسطر غير الصحيحة:**\n"
            for invalid in invalid_lines[:5]:
                validation_text += f"• {invalid}\n"
        
        # Create value selection buttons
        keyboard = []
        for i in range(0, len(CARD_VALUES), 2):
            row = []
            for j in range(2):
                if i + j < len(CARD_VALUES):
                    value = CARD_VALUES[i + j]
                    row.append(InlineKeyboardButton(
                        f"💳 {value:,} ريال", 
                        callback_data=f'simple_upload_value_{value}'
                    ))
            keyboard.append(row)
        
        keyboard.append([
            InlineKeyboardButton('❌ إلغاء', callback_data='simple_upload_cards')
        ])
        
        await update.message.reply_text(
            validation_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in simple_process_file_upload: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الملف.")

async def simple_select_card_value_handler(update: Update, context: CallbackContext, value: str):
    """Handle card value selection"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(f"{EMOJIS['error']} غير مسموح")
            return
        
        # Validate value
        try:
            card_value = int(value)
            if card_value not in CARD_VALUES:
                raise ValueError("Invalid value")
        except ValueError:
            await query.edit_message_text(f"{EMOJIS['error']} قيمة غير صحيحة")
            return
        
        # Store value in context
        context.user_data['upload_value'] = card_value
        context.user_data['upload_step'] = 'description'
        
        cards_count = len(context.user_data.get('upload_cards', []))
        
        description_text = f"""
💰 **تم اختيار القيمة: {card_value:,} ريال**

📝 **الخطوة 3: وصف الكرت**

📦 **أدخل وصف الكرت:**
مثال: "كرت 2 جيجا" أو "كرت 5 جيجا" أو "كرت مفتوح"

💡 **هذا الوصف سيظهر للعملاء عند الشراء**

📊 **ملخص:**
• عدد الكروت: {cards_count:,} كرت
• القيمة: {card_value:,} ريال لكل كرت
• الوصف: سيتم إدخاله الآن

✍️ **اكتب وصف الكرت:**
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='simple_upload_cards')]
        ]
        
        await query.edit_message_text(
            description_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in simple_select_card_value_handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار القيمة.")

async def simple_process_card_description(update: Update, context: CallbackContext):
    """Process card description and save cards to database"""
    try:
        # Check if user is in description step
        if not context.user_data.get('upload_step') == 'description':
            return
        
        user = get_user(update.message.from_user.id)
        if not user or user['role'] not in ['supplier', 'admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} غير مسموح")
            return
        
        description = update.message.text.strip()
        
        # Validate description
        if len(description) < 3:
            await update.message.reply_text(
                f"{EMOJIS['error']} **الوصف قصير جداً**\n\n"
                f"✍️ أدخل وصفاً أطول (3 أحرف على الأقل)"
            )
            return
        
        if len(description) > 100:
            await update.message.reply_text(
                f"{EMOJIS['error']} **الوصف طويل جداً**\n\n"
                f"✍️ يجب أن يكون الوصف أقل من 100 حرف"
            )
            return
        
        # Get data from context
        network_id = context.user_data.get('upload_network_id')
        card_numbers = context.user_data.get('upload_cards', [])
        card_value = context.user_data.get('upload_value')
        
        if not all([network_id, card_numbers, card_value]):
            await update.message.reply_text(
                f"{EMOJIS['error']} **انتهت جلسة الرفع**\n\n"
                f"يرجى البدء من جديد"
            )
            context.user_data.clear()
            return
        
        # Save to database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # Create or get category
            category_name = f"{description} - {card_value:,} ريال"
            
            cursor.execute('''
                INSERT INTO card_categories (network_id, name, value, price, currency, is_available, stock_count, created_at)
                VALUES (?, ?, ?, ?, 'YER', 1, ?, CURRENT_TIMESTAMP)
            ''', (network_id, category_name, card_value, card_value, len(card_numbers)))
            
            category_id = cursor.lastrowid
            
            # Save cards
            cards_saved = 0
            cards_failed = []
            
            for card_number in card_numbers:
                try:
                    cursor.execute('''
                        INSERT INTO cards (category_id, card_number, pin_code, is_sold, created_at, created_by)
                        VALUES (?, ?, NULL, 0, CURRENT_TIMESTAMP, ?)
                    ''', (category_id, card_number, user['id']))
                    cards_saved += 1
                except Exception as card_error:
                    cards_failed.append(card_number)
                    logger.warning(f"Failed to save card {card_number}: {card_error}")
            
            conn.commit()
            
            # Clear context
            context.user_data.clear()
            
            # Get network info
            cursor.execute('SELECT name, provider FROM networks WHERE id = ?', (network_id,))
            network = cursor.fetchone()
            
            # Success message
            success_text = f"""
🎉 **تم رفع الكروت بنجاح!**

🌐 **الشبكة:** {network['name']} - {network['provider']}
🏷️ **الفئة:** {category_name}
💰 **القيمة:** {card_value:,} ريال لكل كرت

📊 **النتائج:**
✅ تم حفظ: {cards_saved:,} كرت
❌ فشل: {len(cards_failed)} كرت
💯 نسبة النجاح: {(cards_saved / len(card_numbers) * 100):.1f}%

🎯 **الكروت جاهزة للبيع!**
"""
            
            if cards_failed and len(cards_failed) <= 5:
                success_text += f"\n⚠️ **الكروت التي فشلت:**\n"
                for failed_card in cards_failed[:5]:
                    success_text += f"• {failed_card}\n"
            
            keyboard = [
                [InlineKeyboardButton('📤 رفع كروت أخرى', callback_data='simple_upload_cards')],
                [InlineKeyboardButton('📊 عرض الشبكة', callback_data=f'enhanced_network_details_{network_id}')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await update.message.reply_text(
                success_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
            # Log the upload
            logger.info(f"Cards uploaded successfully: User {user['id']} uploaded {cards_saved} cards to network {network_id}")
            
        except Exception as db_error:
            conn.rollback()
            logger.error(f"Database error during card upload: {db_error}")
            await update.message.reply_text(
                f"{EMOJIS['error']} **حدث خطأ في حفظ الكروت**\n\n"
                f"يرجى المحاولة مرة أخرى"
            )
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Error in simple_process_card_description: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الوصف.")

# =============================================================================
# CALLBACK HANDLERS MAPPING
# =============================================================================

SIMPLE_UPLOAD_CALLBACKS = {
    'simple_upload_cards': simple_upload_cards_handler,
}

async def handle_simple_upload_callbacks(update: Update, context: CallbackContext, callback_data: str):
    """Handle all simple upload callbacks"""
    try:
        if callback_data.startswith('simple_upload_to_'):
            network_id = callback_data.split('_')[-1]
            await simple_upload_to_network_handler(update, context, network_id)
        elif callback_data.startswith('simple_upload_value_'):
            value = callback_data.split('_')[-1]
            await simple_select_card_value_handler(update, context, value)
        else:
            await update.callback_query.edit_message_text(f"{EMOJIS['error']} خيار غير معروف")
    except Exception as e:
        logger.error(f"Error in handle_simple_upload_callbacks: {e}")
        await update.callback_query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في معالجة الطلب")

# =============================================================================
# TEXT MESSAGE HANDLER
# =============================================================================

async def handle_simple_upload_text_messages(update: Update, context: CallbackContext):
    """Handle text messages for upload process"""
    try:
        upload_step = context.user_data.get('upload_step')
        
        if upload_step == 'description':
            await simple_process_card_description(update, context)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error in handle_simple_upload_text_messages: {e}")
        return False

# =============================================================================
# DOCUMENT HANDLER
# =============================================================================

async def handle_simple_upload_documents(update: Update, context: CallbackContext):
    """Handle document uploads for card upload"""
    try:
        upload_step = context.user_data.get('upload_step')
        
        if upload_step == 'file':
            await simple_process_file_upload(update, context)
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error in handle_simple_upload_documents: {e}")
        return False