#!/usr/bin/env python3
"""
Unified Search Manager for Pottagrm Enhanced Bot
Consolidates all search-related functions to eliminate conflicts

This module merges all search functions from multiple files and resolves
the duplicate search_networks_handler issue.

Author: Software Maintainer
Version: 1.0.0 (Unified)
"""

import logging
from typing import List, Dict, Optional, Tuple

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

from bot_modules.config import EMOJIS
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user, update_user_activity

logger = logging.getLogger(__name__)

# =============================================================================
# UNIFIED SEARCH FUNCTIONS - NO MORE DUPLICATES
# =============================================================================

async def unified_search_networks_handler(update: Update, context: CallbackContext):
    """
    THE ONLY search_networks_handler - resolves duplicate function names
    Merges all search_networks_handler functions from yemen_net_bot_new.py
    """
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        update_user_activity(user['id'])
        
        search_text = f"""
🔍 **البحث المتقدم في الشبكات** 🔍

👤 **{user['full_name']}**

📡 **خيارات البحث المتاحة:**

🔸 **بحث سريع:** ابحث في جميع الحقول
🔸 **بحث بالاسم:** اسم الشبكة أو المزود
🔸 **بحث بالموقع:** المدينة أو المنطقة
🔸 **بحث بالفئة:** حسب نوع الخدمة
🔸 **فلترة متقدمة:** عدة معايير معاً

💡 **اختر نوع البحث المناسب:**
"""
        
        keyboard = [
            [InlineKeyboardButton('⚡ بحث سريع', callback_data='unified_quick_search'),
             InlineKeyboardButton('📝 بحث بالاسم', callback_data='unified_search_by_name')],
            [InlineKeyboardButton('📍 بحث بالموقع', callback_data='unified_search_by_location'),
             InlineKeyboardButton('🏷️ بحث بالفئة', callback_data='unified_search_by_category')],
            [InlineKeyboardButton('🔍 فلترة متقدمة', callback_data='unified_advanced_search'),
             InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='unified_view_all_networks')],
            [InlineKeyboardButton('📱 شبكات المحمول', callback_data='unified_mobile_networks'),
             InlineKeyboardButton('🏠 شبكات منزلية', callback_data='unified_home_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            search_text, 
            reply_markup=InlineKeyboardMarkup(keyboard), 
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error in unified search networks handler: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في البحث عن الشبكات.")

async def process_unified_search(update: Update, context: CallbackContext, search_term: str):
    """
    Process unified search - combines all search logic
    Merges: process_network_search, search_networks_by_name, etc.
    """
    try:
        user = get_user(update.effective_user.id)
        if not user:
            await update.message.reply_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Get search type from context
        search_type = context.user_data.get('search_type', 'general')
        
        # Perform search based on type
        if search_type == 'name':
            results = search_networks_by_name(search_term)
        elif search_type == 'location':
            results = search_networks_by_location(search_term)
        elif search_type == 'provider':
            results = search_networks_by_provider(search_term)
        elif search_type == 'category':
            results = search_networks_by_category(search_term)
        else:
            # General search - search in all fields
            results = search_networks_general(search_term)
        
        # Clear search context
        context.user_data.pop('awaiting_search', None)
        context.user_data.pop('search_type', None)
        
        if not results:
            no_results_text = f"""
❌ **لا توجد نتائج**

🔍 **مصطلح البحث:** {search_term}
📊 **عدد النتائج:** 0

💡 **اقتراحات:**
• تأكد من صحة الكتابة
• جرب مصطلحات أخرى
• استخدم البحث العام

🔄 **جرب البحث مرة أخرى:**
"""
            keyboard = [
                [InlineKeyboardButton('🔍 بحث جديد', callback_data='unified_search_networks')],
                [InlineKeyboardButton('📊 عرض جميع الشبكات', callback_data='unified_view_all_networks')],
                [InlineKeyboardButton('🔙 عودة', callback_data='main_menu')]
            ]
            
            await update.message.reply_text(
                no_results_text,
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
            return
        
        # Display results
        await display_search_results(update, results, search_term, search_type)
        
    except Exception as e:
        logger.error(f"Error processing unified search: {e}")
        await update.message.reply_text(f"❌ خطأ في البحث: {e}")

async def display_search_results(update: Update, results: List[Dict], 
                                search_term: str, search_type: str):
    """Display search results in a unified format"""
    try:
        results_count = len(results)
        search_type_text = {
            'name': 'بالاسم',
            'location': 'بالموقع', 
            'provider': 'بالمزود',
            'category': 'بالفئة',
            'general': 'عام'
        }.get(search_type, 'عام')
        
        results_text = f"""
✅ **نتائج البحث** ✅

🔍 **مصطلح البحث:** {search_term}
📊 **نوع البحث:** {search_type_text}
📈 **عدد النتائج:** {results_count} شبكة

🌐 **الشبكات المتاحة:**
"""
        
        keyboard = []
        for i, network in enumerate(results[:10]):  # Limit to first 10 results
            status_emoji = "✅" if network.get('is_active') else "⚠️"
            approval_emoji = "✅" if network.get('is_approved') else "⏳"
            
            button_text = f"{status_emoji}{approval_emoji} {network['name']}"
            if network.get('location'):
                button_text += f" - {network['location']}"
            
            # Truncate if too long
            if len(button_text) > 50:
                button_text = button_text[:47] + "..."
            
            keyboard.append([InlineKeyboardButton(
                button_text,
                callback_data=f'unified_network_details_{network["id"]}'
            )])
        
        # Add pagination if more than 10 results
        if results_count > 10:
            results_text += f"\n⚠️ **عرض أول 10 نتائج من {results_count}**"
            keyboard.append([InlineKeyboardButton('📄 عرض المزيد', callback_data='unified_more_results')])
        
        keyboard.extend([
            [InlineKeyboardButton('🔍 بحث جديد', callback_data='unified_search_networks')],
            [InlineKeyboardButton('🔙 عودة', callback_data='main_menu')]
        ])
        
        await update.message.reply_text(
            results_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error displaying search results: {e}")
        await update.message.reply_text(f"❌ خطأ في عرض النتائج: {e}")

# =============================================================================
# SEARCH IMPLEMENTATION FUNCTIONS
# =============================================================================

def search_networks_general(search_term: str) -> List[Dict]:
    """General search in all network fields"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute('''
            SELECT n.*, u.full_name as supplier_name,
                   COUNT(cc.id) as categories_count,
                   COUNT(c.id) as cards_count
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id AND c.is_sold = 0
            WHERE (n.name LIKE ? OR n.provider LIKE ? OR n.location LIKE ? 
                   OR n.description LIKE ? OR u.full_name LIKE ?)
                  AND n.is_active = 1 AND n.is_approved = 1
            GROUP BY n.id
            ORDER BY n.created_at DESC
        ''', (search_pattern, search_pattern, search_pattern, search_pattern, search_pattern))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error in general search: {e}")
        return []

def search_networks_by_name(search_term: str) -> List[Dict]:
    """Search networks by name"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute('''
            SELECT n.*, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.name LIKE ? AND n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.name
        ''', (search_pattern,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error searching by name: {e}")
        return []

def search_networks_by_location(search_term: str) -> List[Dict]:
    """Search networks by location"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute('''
            SELECT n.*, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE (n.location LIKE ? OR n.city LIKE ?) 
                  AND n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.location
        ''', (search_pattern, search_pattern))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error searching by location: {e}")
        return []

def search_networks_by_provider(search_term: str) -> List[Dict]:
    """Search networks by provider"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        cursor.execute('''
            SELECT n.*, u.full_name as supplier_name
            FROM networks n
            LEFT JOIN users u ON n.supplier_id = u.id
            WHERE n.provider LIKE ? AND n.is_active = 1 AND n.is_approved = 1
            ORDER BY n.provider
        ''', (search_pattern,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error searching by provider: {e}")
        return []

def search_networks_by_category(search_term: str) -> List[Dict]:
    """Search networks by card category"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Try to parse as number for category value search
        try:
            category_value = int(search_term)
            cursor.execute('''
                SELECT DISTINCT n.*, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id
                WHERE cc.category_value = ? AND n.is_active = 1 AND n.is_approved = 1
                ORDER BY n.name
            ''', (category_value,))
        except ValueError:
            # Search by category name
            search_pattern = f"%{search_term}%"
            cursor.execute('''
                SELECT DISTINCT n.*, u.full_name as supplier_name
                FROM networks n
                LEFT JOIN users u ON n.supplier_id = u.id
                LEFT JOIN card_categories cc ON n.id = cc.network_id
                WHERE cc.category_name LIKE ? AND n.is_active = 1 AND n.is_approved = 1
                ORDER BY n.name
            ''', (search_pattern,))
        
        results = cursor.fetchall()
        conn.close()
        
        return [dict(row) for row in results]
    except Exception as e:
        logger.error(f"Error searching by category: {e}")
        return []

# =============================================================================
# SEARCH INITIATION HANDLERS
# =============================================================================

async def initiate_search_by_type(update: Update, context: CallbackContext, search_type: str):
    """Initiate search of specific type"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text(f"{EMOJIS['error']} يرجى التسجيل أولاً /start")
            return
        
        # Set search context
        context.user_data['awaiting_search'] = True
        context.user_data['search_type'] = search_type
        
        search_prompts = {
            'name': '📝 **أدخل اسم الشبكة للبحث:**\nمثال: شبكة النور',
            'location': '📍 **أدخل الموقع للبحث:**\nمثال: صنعاء، عدن، تعز',
            'provider': '👤 **أدخل اسم المزود للبحث:**\nمثال: محمد علي',
            'category': '🏷️ **أدخل فئة الكرت للبحث:**\nمثال: 1000، 5000',
            'quick': '⚡ **أدخل أي كلمة للبحث السريع:**\nسيتم البحث في جميع الحقول'
        }
        
        prompt_text = f"""
🔍 **بحث {search_prompts.get(search_type, 'عام')}**

{search_prompts.get(search_type, 'أدخل مصطلح البحث:')}

💡 **نصائح:**
• استخدم كلمات واضحة
• يمكن البحث بالكلمات الجزئية
• البحث غير حساس لحالة الأحرف
"""
        
        keyboard = [
            [InlineKeyboardButton('❌ إلغاء', callback_data='unified_search_networks')]
        ]
        
        await query.edit_message_text(
            prompt_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='Markdown'
        )
        
    except Exception as e:
        logger.error(f"Error initiating search: {e}")
        await query.edit_message_text(f"{EMOJIS['error']} حدث خطأ في بدء البحث.")

# =============================================================================
# UNIFIED SEARCH CALLBACKS MAPPING
# =============================================================================

UNIFIED_SEARCH_CALLBACKS = {
    'unified_search_networks': unified_search_networks_handler,
    'unified_search_by_name': lambda u, c: initiate_search_by_type(u, c, 'name'),
    'unified_search_by_location': lambda u, c: initiate_search_by_type(u, c, 'location'),
    'unified_search_by_provider': lambda u, c: initiate_search_by_type(u, c, 'provider'),
    'unified_search_by_category': lambda u, c: initiate_search_by_type(u, c, 'category'),
    'unified_quick_search': lambda u, c: initiate_search_by_type(u, c, 'quick'),
}