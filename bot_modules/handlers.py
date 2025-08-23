#!/usr/bin/env python3
"""
Handlers Module
Main handlers for bot commands and text messages
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, filters
from bot_modules.config import *
from bot_modules.utils import *
from bot_modules.wallet_handlers import enhanced_wallet_handler
from bot_modules.network_handlers import (
    buy_cards_handler, customer_search_networks_handler, perform_quick_search
)

logger = logging.getLogger(__name__)

# Command handlers
async def start_command(update: Update, context: CallbackContext):
    """Handle /start command"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # Check if user exists
        existing_user = get_user(user_id)
        
        if existing_user:
            # User exists, show main menu
            await show_main_menu(update, context, existing_user['role'])
        else:
            # New user, register them
            await register_new_user(update, context)
            
    except Exception as e:
        logger.error(f"Error in start command: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في بدء البوت.")

async def register_new_user(update: Update, context: CallbackContext):
    """Register new user"""
    try:
        user = update.effective_user
        user_id = user.id
        
        # Create new user with default values
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO users (telegram_id, full_name, phone, role, balance, is_active)
            VALUES (?, ?, ?, 'customer', 0.0, 1)
        ''', (user_id, user.full_name or f"User{user_id}", "000000000"))
        
        conn.commit()
        conn.close()
        
        # Show main menu
        await show_main_menu(update, context, 'customer')
        
    except Exception as e:
        logger.error(f"Error registering new user: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في التسجيل. يرجى المحاولة مرة أخرى.")

async def help_command(update: Update, context: CallbackContext):
    """Handle /help command"""
    try:
        help_text = """
🤖 **مرحباً بك في بوت يمن نت!** 🤖

📱 **الأوامر المتاحة:**
/start - بدء البوت
/help - عرض المساعدة
/wallet - عرض المحفظة
/buy - شراء كروت
/profile - الملف الشخصي

💡 **الميزات:**
• شراء كروت الإنترنت
• إدارة المحفظة
• تحويل الأرصدة
• إدارة الشبكات (للمزودين)

🔧 **للمساعدة:** تواصل مع الدعم الفني
"""
        
        await update.message.reply_text(help_text, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in help command: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض المساعدة.")

async def wallet_command(update: Update, context: CallbackContext):
    """Handle /wallet command"""
    try:
        user = get_user(update.effective_user.id)
        
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Call wallet handler
        await enhanced_wallet_handler(update, context)
        
    except Exception as e:
        logger.error(f"Error in wallet command: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض المحفظة.")

async def buy_command(update: Update, context: CallbackContext):
    """Handle /buy command"""
    try:
        user = get_user(update.effective_user.id)
        
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Call buy cards handler
        await buy_cards_handler(update, context)
        
    except Exception as e:
        logger.error(f"Error in buy command: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض قائمة الشراء.")

async def profile_command(update: Update, context: CallbackContext):
    """Handle /profile command"""
    try:
        user = get_user(update.effective_user.id)
        
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        profile_text = f"""
👤 **الملف الشخصي** 👤

📱 **المعلومات الأساسية:**
👤 **الاسم:** {user['full_name']}
🆔 **المعرف:** {user['id']}
📞 **رقم الهاتف:** {user.get('phone', 'غير محدد')}
👑 **الدور:** {get_role_name(user['role'])}
💰 **الرصيد:** {user['balance']:,.2f} ريال

📊 **الإحصائيات:**
📅 **تاريخ التسجيل:** {user.get('created_at', 'غير محدد')}
🕐 **آخر نشاط:** {user.get('last_activity', 'غير محدد')}
"""
        
        keyboard = [
            [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
            [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.message.reply_text(profile_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in profile command: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض الملف الشخصي.")

# Text message handler
async def handle_text_message(update: Update, context: CallbackContext):
    """Handle text messages with state management"""
    try:
        user = get_user(update.effective_user.id)
        
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        text = update.message.text.strip()
        
        # ===== HIGH PRIORITY STATES (Card input flow) =====
        # Check if supplier is entering custom price (PRIORITY HIGH)
        if context.user_data.get('awaiting_custom_price'):
            return await process_custom_price_input(update, context)
        
        # Check if supplier is entering card size (PRIORITY HIGH)
        if context.user_data.get('awaiting_card_size'):
            return await process_card_size_input(update, context)
        
        # Check if supplier is entering card numbers (PRIORITY HIGH)
        if context.user_data.get('awaiting_card_numbers'):
            return await process_card_numbers_input(update, context)
        
        # ===== NETWORK SEARCH STATES =====
        # Check if waiting for network search
        if context.user_data.get('awaiting_network_search'):
            return await process_network_search(update, context, text)
        
        # Check if searching for networks (new search feature)
        if context.user_data.get('searching_network'):
            from yemen_net_bot_new import perform_network_search
            return await perform_network_search(update, context)
        
        # Check if customer is searching for networks
        if context.user_data.get('customer_searching_network'):
            from yemen_net_bot_new import perform_customer_network_search
            return await perform_customer_network_search(update, context)
        
        # ===== TRANSFER STATES =====
        # Check if waiting for transfer recipient
        if context.user_data.get('awaiting_transfer_step1'):
            return await process_transfer_recipient(update, context, text)
        
        # Check if waiting for transfer amount
        if context.user_data.get('awaiting_transfer_step2'):
            return await process_transfer_amount(update, context, text)
        
        # Check if waiting for user search
        if context.user_data.get('awaiting_user_search'):
            return await process_user_search(update, context, text)
        
        # ===== DEFAULT RESPONSE =====
        # If no specific state, show main menu
        await show_main_menu(update, context, user['role'])
        
    except Exception as e:
        logger.error(f"Error in handle text message: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة الرسالة.")

# State processing functions
async def process_custom_price_input(update: Update, context: CallbackContext):
    """Process custom price input from supplier"""
    try:
        text = update.message.text.strip()
        
        # Validate price
        try:
            price = int(text)
            if price < 50:
                await update.message.reply_text("❌ السعر يجب أن يكون 50 ريال أو أكثر.")
                return
        except ValueError:
            await update.message.reply_text("❌ يرجى إدخال رقم صحيح للسعر.")
            return
        
        # Store price and move to card size
        context.user_data['selected_price'] = price
        context.user_data['awaiting_card_size'] = True
        del context.user_data['awaiting_custom_price']
        
        await update.message.reply_text(f"""
✅ **تم تحديد السعر:** {price} ريال

📏 **الآن أدخل حجم الكرت:**
• مثال: `1 جيجا` → 1000 ميجابايت
• مثال: `500 ميجابايت` → 500 ميجابايت
• مثال: `2 جيجا` → 2000 ميجابايت

💡 **اكتب الحجم الآن:**
""")
        
    except Exception as e:
        logger.error(f"Error in process custom price input: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة السعر.")

async def process_card_size_input(update: Update, context: CallbackContext):
    """Process card size input from supplier"""
    try:
        text = update.message.text.strip().lower()
        
        # Parse size input
        size_mb = parse_size_input(text)
        if size_mb is None:
            await update.message.reply_text("""
❌ **تنسيق الحجم غير صحيح**

💡 **أمثلة صحيحة:**
• `1 جيجا` أو `1 جيجابايت` → 1000 ميجابايت
• `500 ميجابايت` → 500 ميجابايت
• `2 جيجا` → 2000 ميجابايت
• `1.5 جيجا` → 1500 ميجابايت

🔍 **اكتب الحجم مرة أخرى:**
""")
            return
        
        # Store size and move to card numbers
        context.user_data['selected_size'] = size_mb
        context.user_data['awaiting_card_numbers'] = True
        del context.user_data['awaiting_card_size']
        
        await update.message.reply_text(f"""
✅ **تم تحديد حجم الكرت:** {size_mb} ميجابايت

💳 **الآن أرسل أرقام الكروت:**
• كل كرت في سطر منفصل
• مثال:
```
1234567890123456
9876543210987654
1111222233334444
```

💡 **أرسل أرقام الكروت الآن:**
""")
        
    except Exception as e:
        logger.error(f"Error in process card size input: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة حجم الكرت.")

async def process_card_numbers_input(update: Update, context: CallbackContext):
    """Process card numbers input from supplier"""
    try:
        text = update.message.text.strip()
        lines = text.split('\n')
        
        # Validate card numbers
        valid_cards = []
        for line in lines:
            card = line.strip()
            if len(card) >= 10:  # Basic validation
                valid_cards.append(card)
        
        if not valid_cards:
            await update.message.reply_text("❌ لم يتم العثور على أرقام كروت صحيحة.")
            return
        
        # Process cards
        await process_cards_upload(update, context, valid_cards)
        
        # Clear states
        del context.user_data['awaiting_card_numbers']
        del context.user_data['selected_price']
        del context.user_data['selected_size']
        del context.user_data['manual_network_id']
        
    except Exception as e:
        logger.error(f"Error in process card numbers input: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في معالجة أرقام الكروت.")

async def process_cards_upload(update: Update, context: CallbackContext, card_numbers: list):
    """Process the actual cards upload"""
    try:
        user = get_user(update.effective_user.id)
        network_id = context.user_data.get('manual_network_id')
        price = context.user_data.get('selected_price')
        size = context.user_data.get('selected_size')
        
        if not all([network_id, price, size]):
            await update.message.reply_text("❌ بيانات غير مكتملة. يرجى المحاولة مرة أخرى.")
            return
        
        # Upload cards to database
        success_count = await upload_cards_to_database(user, network_id, price, size, card_numbers)
        
        success_text = f"""
✅ **تم رفع الكروت بنجاح!** ✅

📊 **تفاصيل الرفع:**
🌐 **الشبكة:** {network_id}
💰 **السعر:** {price} ريال
📏 **الحجم:** {size} ميجابايت
💳 **عدد الكروت:** {len(card_numbers)}
✅ **تم رفع:** {success_count} كرت

🎉 **تم إنشاء فئة كروت جديدة تلقائياً!**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔄 رفع كروت أخرى', callback_data='upload_cards')],
            [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await update.message.reply_text(success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in process cards upload: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في رفع الكروت.")

# Helper functions
def parse_size_input(text: str) -> int:
    """Parse size input and convert to MB"""
    try:
        text = text.lower().replace('جيجابايت', 'جيجا').replace('ميجابايت', 'ميجا')
        
        if 'جيجا' in text:
            # Extract number before جيجا
            number = float(text.split('جيجا')[0].strip())
            return int(number * 1000)
        elif 'ميجا' in text:
            # Extract number before ميجا
            number = float(text.split('ميجا')[0].strip())
            return int(number)
        else:
            # Try to extract just the number
            import re
            numbers = re.findall(r'\d+\.?\d*', text)
            if numbers:
                number = float(numbers[0])
                if 'جيجا' in text or 'جيجابايت' in text:
                    return int(number * 1000)
                else:
                    return int(number)
        
        return None
    except:
        return None

async def upload_cards_to_database(user: dict, network_id: str, price: int, size: int, card_numbers: list) -> int:
    """Upload cards to database and return success count"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Check if category exists, create if not
        cursor.execute('''
            SELECT id FROM card_categories 
            WHERE network_id = ? AND price = ? AND value = ?
        ''', (network_id, price, size))
        
        category = cursor.fetchone()
        if category:
            category_id = category[0]
        else:
            # Create new category
            cursor.execute('''
                INSERT INTO card_categories (network_id, name, price, value, stock_count, is_available)
                VALUES (?, ?, ?, ?, 0, 1)
            ''', (network_id, f"{size} ميجابايت - {price} ريال", price, size))
            category_id = cursor.lastrowid
        
        # Upload cards
        success_count = 0
        for card_number in card_numbers:
            try:
                cursor.execute('''
                    INSERT INTO cards (card_number, category_id, is_used, uploaded_by)
                    VALUES (?, ?, 0, ?)
                ''', (card_number, category_id, user['id']))
                success_count += 1
            except:
                # Card might already exist
                continue
        
        # Update stock count
        cursor.execute('''
            UPDATE card_categories 
            SET stock_count = (SELECT COUNT(*) FROM cards WHERE category_id = ? AND is_used = 0)
            WHERE id = ?
        ''', (category_id, category_id))
        
        conn.commit()
        conn.close()
        
        return success_count
        
    except Exception as e:
        logger.error(f"Error uploading cards to database: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        raise

# Main menu function
async def show_main_menu(update: Update, context: CallbackContext, user_role: str):
    """Show main menu based on user role"""
    try:
        user = get_user(update.effective_user.id)
        
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Build menu text
        menu_text = f"""
🏠 **القائمة الرئيسية** 🏠

👤 **{user['full_name']}**
💰 **رصيدك:** {user['balance']:,.2f} ريال
👑 **دورك:** {get_role_name(user_role)}

💡 **اختر الخدمة المطلوبة:**
"""
        
        # Build keyboard based on role
        keyboard = []
        
        if user_role == 'customer':
            keyboard.extend([
                [InlineKeyboardButton('🛒 شراء كروت', callback_data='buy_cards')],
                [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('👤 الملف الشخصي', callback_data='profile')]
            ])
        elif user_role == 'supplier':
            keyboard.extend([
                [InlineKeyboardButton('🏪 لوحة المزود', callback_data='supplier_panel')],
                [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('👤 الملف الشخصي', callback_data='profile')]
            ])
        elif user_role == 'super_admin':
            keyboard.extend([
                [InlineKeyboardButton('👑 لوحة المشرف الأعلى', callback_data='super_admin_panel')],
                [InlineKeyboardButton('💰 محفظتي', callback_data='enhanced_wallet')],
                [InlineKeyboardButton('👤 الملف الشخصي', callback_data='profile')]
            ])
        
        # Add common buttons
        keyboard.extend([
            [InlineKeyboardButton('❓ المساعدة', callback_data='help')],
            [InlineKeyboardButton('📞 الدعم الفني', callback_data='support')]
        ])
        
        await update.message.reply_text(menu_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in show main menu: {e}")
        await update.message.reply_text(f"{EMOJIS['error']} حدث خطأ في عرض القائمة الرئيسية.")

def get_role_name(role: str) -> str:
    """Get Arabic role name"""
    role_names = {
        'customer': '👤 عميل',
        'supplier': '🏪 مزود',
        'super_admin': '👑 مشرف أعلى'
    }
    return role_names.get(role, role)

# Setup handlers function
def setup_handlers(application):
    """Setup all command and message handlers"""
    # Command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("wallet", wallet_command))
    application.add_handler(CommandHandler("buy", buy_command))
    application.add_handler(CommandHandler("profile", profile_command))
    
    # Message handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_message))
    
    logger.info("All handlers setup completed successfully")
