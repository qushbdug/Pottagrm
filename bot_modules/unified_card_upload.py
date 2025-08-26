#!/usr/bin/env python3
"""
Unified Card Upload Manager for Yemen Net Bot
Merges supplier and admin card upload methods into one unified system

Features:
- Single unified upload method for both suppliers and admins
- Supports Excel, CSV, and text formats
- Automatic network detection for suppliers
- Network selection for admins
- Batch processing with progress tracking
- Comprehensive error handling

Author: Software Maintenance Engineer
Version: 1.0.0 (Unified)
"""

import logging
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS, PANDAS_AVAILABLE
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# =============================================================================
# UNIFIED CARD UPLOAD SYSTEM
# =============================================================================

async def unified_upload_cards_handler(update: Update, context: CallbackContext):
    """
    UNIFIED: Card upload handler for both suppliers and admins
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Check permissions - suppliers and admins only
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text(
                f"""
{EMOJIS['error']} **غير مسموح**

هذه الميزة متاحة للمزودين والمشرفين فقط.
للحصول على حساب مزود، تواصل مع الإدارة.
"""
            )
            return
        
        update_user_activity(user['id'])
        
        # Get user's networks
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] in ['admin', 'super_admin']:
            # Admins can see all networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, u.full_name as supplier_name,
                       COUNT(cc.id) as categories
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                WHERE n.is_active = 1 AND n.is_approved = 1
                GROUP BY n.id, n.name, n.provider, u.full_name
                ORDER BY n.created_at DESC
            ''')
        else:
            # Suppliers see only their networks
            cursor.execute('''
                SELECT n.id, n.name, n.provider, u.full_name as supplier_name,
                       COUNT(cc.id) as categories
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id AND cc.is_available = 1
                WHERE n.supplier_id = ? AND n.is_active = 1 AND n.is_approved = 1
                GROUP BY n.id, n.name, n.provider, u.full_name
                ORDER BY n.created_at DESC
            ''', (user['id'],))
        
        networks = cursor.fetchall()
        conn.close()
        
        role_title = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
        
        upload_text = f"""
📤 **رفع كروت الشحن** 📤

👤 **{user['full_name']}** ({role_title})

📊 **شبكاتك المتاحة: {len(networks)}**

"""
        
        if networks:
            upload_text += "🌐 **اختر الشبكة لرفع الكروت:**\n\n"
            
            for network in networks:
                net_id, name, provider, supplier_name, categories = network
                
                # Show supplier name for admins
                if user['role'] in ['admin', 'super_admin'] and supplier_name:
                    provider_text = f"👤 {supplier_name}"
                else:
                    provider_text = f"👤 {provider}"
                
                upload_text += f"""
🌐 **{name}**
{provider_text}
💳 {categories} فئة متاحة
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            upload_text += """
❌ **لا توجد شبكات متاحة**

🔧 **يجب إضافة شبكة أولاً قبل رفع الكروت**
"""
        
        keyboard = []
        
        # Add network selection buttons
        if networks:
            for network in networks[:6]:  # First 6 networks
                net_id, name = network[0], network[1]
                display_name = name[:25] + "..." if len(name) > 25 else name
                
                keyboard.append([InlineKeyboardButton(
                    f'📤 رفع لـ {display_name}',
                    callback_data=f'unified_upload_to_{net_id}'
                )])
        
        # Navigation buttons
        if user['role'] in ['admin', 'super_admin']:
            keyboard.extend([
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='unified_add_network')],
                [InlineKeyboardButton('📊 إدارة الشبكات', callback_data='unified_manage_networks')],
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ])
        else:
            keyboard.extend([
                [InlineKeyboardButton('🌐 إضافة شبكة جديدة', callback_data='unified_add_network')],
                [InlineKeyboardButton('📶 إدارة شبكاتي', callback_data='manage_networks')],
                [InlineKeyboardButton('🏠 لوحة المزود', callback_data='supplier_panel')]
            ])
        
        await query.edit_message_text(upload_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in unified upload cards handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في عرض صفحة رفع الكروت.")

async def unified_select_network_for_upload(update: Update, context: CallbackContext, network_id: str):
    """
    UNIFIED: Select network and show upload options
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get network details and categories
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT n.id, n.name, n.provider, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.id = ? AND n.is_active = 1
        ''', (network_id,))
        
        network = cursor.fetchone()
        
        if not network:
            await query.edit_message_text("❌ الشبكة غير موجودة أو غير متاحة")
            return
        
        net_id, name, provider, supplier_name = network
        
        # Get available categories
        cursor.execute('''
            SELECT id, name, value, price, stock_count
            FROM card_categories
            WHERE network_id = ? AND is_available = 1
            ORDER BY price ASC
        ''', (network_id,))
        categories = cursor.fetchall()
        
        conn.close()
        
        role_title = "مشرف" if user['role'] in ['admin', 'super_admin'] else "مزود"
        supplier_text = supplier_name if user['role'] in ['admin', 'super_admin'] and supplier_name else provider
        
        select_text = f"""
📤 **رفع كروت للشبكة** 📤

👤 **{user['full_name']}** ({role_title})

🌐 **الشبكة المختارة:**
📋 **{name}**
👤 المزود: {supplier_text}

💳 **الفئات المتاحة ({len(categories)}):**

"""
        
        if categories:
            for category in categories:
                cat_id, cat_name, cat_value, cat_price, stock = category
                select_text += f"""
🎫 **{cat_name}**
💰 السعر: {cat_price:,.0f} ريال
📦 المخزون الحالي: {stock} كرت
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            select_text += f"""

📁 **طرق الرفع المتاحة:**
• رفع ملف Excel (.xlsx, .xls)
• رفع ملف CSV (.csv)
• إدخال نصي (للكميات الصغيرة)

📤 **قم برفع ملف الكروت الآن**
"""
        else:
            select_text += """
❌ **لا توجد فئات كروت لهذه الشبكة**

🔧 **يجب إضافة فئات كروت أولاً**
"""
        
        keyboard = []
        
        if categories:
            # Add category-specific upload if needed
            keyboard.extend([
                [InlineKeyboardButton('💳 إضافة فئة جديدة', callback_data=f'unified_add_categories_{net_id}')],
                [InlineKeyboardButton('📊 إحصائيات الشبكة', callback_data=f'simple_details_{net_id}')]
            ])
        else:
            keyboard.append([InlineKeyboardButton('💳 إضافة فئة جديدة', callback_data=f'unified_add_categories_{net_id}')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔙 العودة لاختيار الشبكة', callback_data='unified_upload_cards')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(select_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
        # Set context for file upload
        context.user_data['uploading_to_network'] = network_id
        context.user_data['upload_network_name'] = name
        
    except Exception as e:
        logger.error(f"Error in unified select network for upload: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في اختيار الشبكة.")

async def unified_process_card_upload(update: Update, context: CallbackContext):
    """
    UNIFIED: Process uploaded card file
    """
    try:
        if not update.message.document:
            await update.message.reply_text("❌ يرجى رفع ملف صحيح")
            return
        
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        network_id = context.user_data.get('uploading_to_network')
        network_name = context.user_data.get('upload_network_name', 'غير محدد')
        
        if not network_id:
            await update.message.reply_text("❌ يرجى اختيار شبكة أولاً")
            return
        
        document = update.message.document
        file_name = document.file_name
        file_size = document.file_size
        
        # Validate file
        if file_size > 10 * 1024 * 1024:  # 10MB limit
            await update.message.reply_text("❌ حجم الملف كبير جداً (الحد الأقصى 10 ميجابايت)")
            return
        
        allowed_extensions = ['.xlsx', '.xls', '.csv', '.txt']
        if not any(file_name.lower().endswith(ext) for ext in allowed_extensions):
            await update.message.reply_text(f"❌ نوع الملف غير مدعوم. الأنواع المدعومة: {', '.join(allowed_extensions)}")
            return
        
        # Download file
        processing_msg = await update.message.reply_text(f"{EMOJIS['loading']} جاري معالجة الملف...")
        
        try:
            file = await context.bot.get_file(document.file_id)
            file_path = f"uploads/{file_name}_{uuid.uuid4().hex[:8]}"
            
            # Create uploads directory if not exists
            os.makedirs('uploads', exist_ok=True)
            
            await file.download_to_drive(file_path)
            
            # Process file based on type
            if file_name.lower().endswith(('.xlsx', '.xls')):
                result = await process_excel_upload(file_path, network_id, user)
            elif file_name.lower().endswith('.csv'):
                result = await process_csv_upload(file_path, network_id, user)
            else:
                result = await process_text_upload(file_path, network_id, user)
            
            # Clean up file
            if os.path.exists(file_path):
                os.remove(file_path)
            
            # Clear context
            context.user_data.pop('uploading_to_network', None)
            context.user_data.pop('upload_network_name', None)
            
            # Show result
            if result['success']:
                success_text = f"""
✅ **تم رفع الكروت بنجاح!**

📁 **الملف:** {file_name}
🌐 **الشبكة:** {network_name}
📊 **النتائج:**
• ✅ تم رفع: {result['uploaded']} كرت
• ⚠️ تم تجاهل: {result['skipped']} كرت مكرر
• ❌ أخطاء: {result['errors']} كرت

💳 **إجمالي الكروت المرفوعة:** {result['uploaded']}
"""
                
                keyboard = [
                    [InlineKeyboardButton('📤 رفع ملف آخر', callback_data='unified_upload_cards')],
                    [InlineKeyboardButton('📊 إحصائيات الشبكة', callback_data=f'simple_details_{network_id}')],
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ]
                
                await processing_msg.edit_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
            else:
                await processing_msg.edit_text(f"❌ فشل في رفع الكروت: {result['error']}")
        
        except Exception as e:
            logger.error(f"Error processing upload: {e}")
            await processing_msg.edit_text(f"❌ حدث خطأ في معالجة الملف: {e}")
        
    except Exception as e:
        logger.error(f"Error in unified process card upload: {e}")
        await update.message.reply_text(f"❌ حدث خطأ في رفع الكروت: {e}")

# =============================================================================
# FILE PROCESSING FUNCTIONS
# =============================================================================

async def process_excel_upload(file_path: str, network_id: str, user: dict) -> dict:
    """Process Excel file upload"""
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "مكتبة pandas غير متاحة"}
        
        import pandas as pd
        
        # Read Excel file
        df = pd.read_excel(file_path)
        
        # Expected columns: card_number, serial_number (optional), category_value, expiry_date (optional)
        required_cols = ['card_number', 'category_value']
        
        if not all(col in df.columns for col in required_cols):
            return {"success": False, "error": f"الملف يجب أن يحتوي على الأعمدة: {', '.join(required_cols)}"}
        
        uploaded = 0
        skipped = 0
        errors = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        for _, row in df.iterrows():
            try:
                card_number = str(row['card_number']).strip()
                category_value = int(row['category_value'])
                serial_number = str(row.get('serial_number', '')).strip() if 'serial_number' in row else None
                expiry_date = str(row.get('expiry_date', '')).strip() if 'expiry_date' in row else None
                
                if not card_number or len(card_number) < 10:
                    errors += 1
                    continue
                
                # Find category
                cursor.execute('SELECT id FROM card_categories WHERE network_id = ? AND value = ?', (network_id, category_value))
                category = cursor.fetchone()
                
                if not category:
                    errors += 1
                    continue
                
                category_id = category['id']
                
                # Check if card already exists
                cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_number,))
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Insert card
                cursor.execute('''
                    INSERT INTO cards (category_id, card_number, serial_number, expiry_date, uploaded_by, uploaded_at)
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ''', (category_id, card_number, serial_number, expiry_date, user['id']))
                
                uploaded += 1
                
            except Exception as e:
                logger.error(f"Error processing row: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "uploaded": uploaded,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error processing Excel file: {e}")
        return {"success": False, "error": str(e)}

async def process_csv_upload(file_path: str, network_id: str, user: dict) -> dict:
    """Process CSV file upload"""
    try:
        if not PANDAS_AVAILABLE:
            return {"success": False, "error": "مكتبة pandas غير متاحة"}
        
        import pandas as pd
        
        # Read CSV file
        df = pd.read_csv(file_path)
        
        # Same processing as Excel
        return await process_excel_upload(file_path, network_id, user)
        
    except Exception as e:
        logger.error(f"Error processing CSV file: {e}")
        return {"success": False, "error": str(e)}

async def process_text_upload(file_path: str, network_id: str, user: dict) -> dict:
    """Process text file upload"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        uploaded = 0
        skipped = 0
        errors = 0
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get default category (first available)
        cursor.execute('SELECT id FROM card_categories WHERE network_id = ? AND is_available = 1 ORDER BY price ASC LIMIT 1', (network_id,))
        category = cursor.fetchone()
        
        if not category:
            return {"success": False, "error": "لا توجد فئات متاحة لهذه الشبكة"}
        
        category_id = category['id']
        
        for line in lines:
            try:
                card_number = line.strip()
                
                if not card_number or len(card_number) < 10:
                    errors += 1
                    continue
                
                # Check if card already exists
                cursor.execute('SELECT id FROM cards WHERE card_number = ?', (card_number,))
                if cursor.fetchone():
                    skipped += 1
                    continue
                
                # Insert card
                cursor.execute('''
                    INSERT INTO cards (category_id, card_number, uploaded_by, uploaded_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ''', (category_id, card_number, user['id']))
                
                uploaded += 1
                
            except Exception as e:
                logger.error(f"Error processing line: {e}")
                errors += 1
        
        conn.commit()
        conn.close()
        
        return {
            "success": True,
            "uploaded": uploaded,
            "skipped": skipped,
            "errors": errors
        }
        
    except Exception as e:
        logger.error(f"Error processing text file: {e}")
        return {"success": False, "error": str(e)}

# =============================================================================
# CALLBACK HANDLERS MAPPING
# =============================================================================

UNIFIED_UPLOAD_CALLBACKS = {
    'unified_upload_cards': unified_upload_cards_handler,
    'upload_cards': unified_upload_cards_handler,  # Backward compatibility
}

async def handle_unified_upload_callbacks(update: Update, context: CallbackContext, callback_data: str):
    """Handle unified upload callbacks"""
    try:
        if callback_data.startswith('unified_upload_to_'):
            network_id = callback_data.split('_')[-1]
            await unified_select_network_for_upload(update, context, network_id)
        else:
            if callback_data in UNIFIED_UPLOAD_CALLBACKS:
                await UNIFIED_UPLOAD_CALLBACKS[callback_data](update, context)
    except Exception as e:
        logger.error(f"Error in unified upload callback handler: {e}")
        query = update.callback_query
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")