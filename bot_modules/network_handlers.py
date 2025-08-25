#!/usr/bin/env python3
"""
Network Handlers module for Pottagrm Enhanced Bot
Contains unified network creation and management functions
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.database import get_db_connection
from bot_modules.utils import *

logger = logging.getLogger(__name__)

async def process_unified_network_creation(update: Update, context: CallbackContext):
    """معالجة إضافة الشبكة الموحدة للمزود والمشرف - مُحسن"""
    try:
        text = update.message.text.strip()
        user = get_user(update.effective_user.id)
        step = context.user_data.get('network_step', 'name')
        
        # التحقق من الصلاحيات
        if user['role'] not in ['supplier', 'admin', 'super_admin']:
            await update.message.reply_text(f"{EMOJIS['error']} ليس لديك صلاحية لإضافة الشبكات.")
            context.user_data.clear()
            return
        
        if step == 'name':
            context.user_data['network_name'] = text
            context.user_data['network_step'] = 'provider'
            await update.message.reply_text(
                f"✅ **تم حفظ اسم الشبكة:** {text}\n\n🔸 **الخطوة 2 من 5**\n👤 **أدخل اسم المزود:**",
                parse_mode='Markdown'
            )
            
        elif step == 'provider':
            context.user_data['network_provider'] = text
            context.user_data['network_step'] = 'description'
            await update.message.reply_text(
                f"✅ **تم حفظ اسم المزود:** {text}\n\n🔸 **الخطوة 3 من 5**\n📝 **أدخل وصف الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'description':
            context.user_data['network_description'] = text
            context.user_data['network_step'] = 'location'
            await update.message.reply_text(
                f"✅ **تم حفظ وصف الشبكة:** {text}\n\n🔸 **الخطوة 4 من 5**\n📍 **أدخل موقع الشبكة:**",
                parse_mode='Markdown'
            )
            
        elif step == 'location':
            context.user_data['network_location'] = text
            context.user_data['network_step'] = 'categories'
            
            # عرض خيارات فئات الكروت
            categories_text = f"""
✅ **تم حفظ موقع الشبكة:** {text}

🔸 **الخطوة 5 من 5**
💳 **اختر فئات الكروت المتاحة:**

يمكنك اختيار فئة واحدة أو أكثر من الفئات التالية:
• 1000 ريال
• 2000 ريال  
• 5000 ريال
• 10000 ريال
• 20000 ريال

📝 **أدخل قيم الفئات مفصولة بفاصلة:**
مثال: 1000,2000,5000

أو اكتب **تخطي** لإضافة الفئات لاحقاً
"""
            await update.message.reply_text(categories_text, parse_mode='Markdown')
            
        elif step == 'categories':
            network_name = context.user_data.get('network_name')
            provider = context.user_data.get('network_provider')
            description = context.user_data.get('network_description')
            location = context.user_data.get('network_location')
            
            try:
                conn = get_db_connection()
                cursor = conn.cursor()
                
                # تحديد supplier_id بناءً على دور المستخدم
                if user['role'] in ['admin', 'super_admin']:
                    # المشرف يمكنه إضافة شبكة لأي مزود، هنا نضعه لنفسه
                    supplier_id = user['id'] 
                else:
                    supplier_id = user['id']
                
                # إدراج الشبكة
                cursor.execute('''
                    INSERT INTO networks (supplier_id, name, city, provider, description, location, created_by, is_active, is_approved, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, 1, CURRENT_TIMESTAMP)
                ''', (supplier_id, network_name, location, provider, description, location, user['id']))
                
                network_id = cursor.lastrowid
                
                # معالجة فئات الكروت
                if text.lower().strip() != 'تخطي':
                    try:
                        # تحليل الفئات المدخلة
                        category_values = [int(val.strip()) for val in text.split(',') if val.strip().isdigit()]
                        
                        for value in category_values:
                            cursor.execute('''
                                INSERT INTO card_categories (network_id, category_name, category_value, max_cards, is_available, created_at)
                                VALUES (?, ?, ?, 10000, 1, CURRENT_TIMESTAMP)
                            ''', (network_id, f"كرت {value} ريال", value))
                        
                        categories_info = f"\n💳 **تم إضافة {len(category_values)} فئة:** {', '.join([f'{v} ريال' for v in category_values])}"
                    except:
                        categories_info = "\n⚠️ **لم يتم إضافة فئات** - يمكن إضافتها لاحقاً"
                else:
                    categories_info = "\n⚠️ **تم تخطي إضافة الفئات** - يمكن إضافتها لاحقاً"
                
                conn.commit()
                conn.close()
                context.user_data.clear()
                
                # إنشاء لوحة للخيارات التالية
                keyboard = [
                    [InlineKeyboardButton('💳 إضافة فئات كروت', callback_data=f'add_categories_{network_id}'),
                     InlineKeyboardButton('📤 رفع كروت', callback_data=f'upload_to_network_{network_id}')],
                    [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks'),
                     InlineKeyboardButton('🏪 القائمة الرئيسية', callback_data='main_menu')]
                ]
                
                success_text = f"""
✅ **تم إنشاء الشبكة بنجاح!**

🌐 **{network_name}**
👤 **المزود:** {provider}
📍 **الموقع:** {location}
🆔 **معرف الشبكة:** #{network_id}{categories_info}

🔧 **الخيارات المتاحة:**
"""
                
                await update.message.reply_text(
                    success_text,
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode='Markdown'
                )
                
            except Exception as e:
                logger.error(f"Error creating network: {e}")
                await update.message.reply_text(f"❌ خطأ في إنشاء الشبكة: {e}")
                context.user_data.clear()
        
    except Exception as e:
        logger.error(f"Error in unified network creation: {e}")
        await update.message.reply_text(f"❌ خطأ في معالجة الشبكة: {e}")
        context.user_data.clear()

async def process_category_addition(update: Update, context: CallbackContext):
    """معالجة إضافة فئات الكروت"""
    try:
        if not context.user_data.get('adding_categories'):
            return
            
        text = update.message.text.strip()
        network_id = context.user_data.get('target_network_id')
        user = get_user(update.effective_user.id)
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على الفئات الموجودة
        cursor.execute('SELECT category_value FROM card_categories WHERE network_id = ?', (network_id,))
        existing_values = [row['category_value'] for row in cursor.fetchall()]
        
        try:
            # تحليل الفئات المدخلة
            category_values = [int(val.strip()) for val in text.split(',') if val.strip().isdigit()]
            new_categories = [val for val in category_values if val not in existing_values]
            skipped_categories = [val for val in category_values if val in existing_values]
            
            added_count = 0
            for value in new_categories:
                cursor.execute('''
                    INSERT INTO card_categories (network_id, category_name, category_value, max_cards, is_available, created_at)
                    VALUES (?, ?, ?, 10000, 1, CURRENT_TIMESTAMP)
                ''', (network_id, f"كرت {value} ريال", value))
                added_count += 1
            
            conn.commit()
            conn.close()
            
            result_text = f"✅ **تم إضافة {added_count} فئة جديدة بنجاح!**\n\n"
            
            if new_categories:
                result_text += f"💳 **الفئات المضافة:** {', '.join([f'{v} ريال' for v in new_categories])}\n\n"
            
            if skipped_categories:
                result_text += f"⚠️ **فئات تم تجاهلها (موجودة مسبقاً):** {', '.join([f'{v} ريال' for v in skipped_categories])}\n\n"
            
            # إنشاء لوحة للخيارات التالية
            keyboard = [
                [InlineKeyboardButton('📤 رفع كروت للشبكة', callback_data=f'upload_to_network_{network_id}'),
                 InlineKeyboardButton('💳 إضافة فئات أخرى', callback_data=f'add_categories_{network_id}')],
                [InlineKeyboardButton('📶 إدارة الشبكات', callback_data='manage_networks'),
                 InlineKeyboardButton('🏪 القائمة الرئيسية', callback_data='main_menu')]
            ]
            
            await update.message.reply_text(
                result_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            
        except ValueError:
            await update.message.reply_text("❌ تنسيق غير صحيح. يرجى إدخال أرقام مفصولة بفواصل.\nمثال: 1000,2000,5000")
        except Exception as e:
            logger.error(f"Error processing categories: {e}")
            await update.message.reply_text(f"❌ خطأ في إضافة الفئات: {e}")
        
        # تنظيف البيانات
        context.user_data.pop('adding_categories', None)
        context.user_data.pop('target_network_id', None)
        
    except Exception as e:
        logger.error(f"Error in process category addition: {e}")
        await update.message.reply_text(f"❌ خطأ في معالجة الفئات: {e}")