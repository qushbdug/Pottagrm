#!/usr/bin/env python3
"""
Pagination Helper - مساعد التصفح
يوفر نظام تصفح متقدم للقوائم الطويلة
"""

import logging
import math
from typing import List, Dict, Any, Optional, Tuple
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)

class PaginationHelper:
    """مساعد التصفح للقوائم الطويلة"""
    
    def __init__(self, items_per_page: int = 10):
        self.items_per_page = items_per_page
    
    def paginate_list(self, items: List[Any], page: int = 1) -> Dict[str, Any]:
        """تقسيم قائمة إلى صفحات"""
        if not items:
            return {
                'items': [],
                'current_page': 1,
                'total_pages': 1,
                'total_items': 0,
                'has_previous': False,
                'has_next': False,
                'start_index': 0,
                'end_index': 0
            }
        
        total_items = len(items)
        total_pages = math.ceil(total_items / self.items_per_page)
        
        # التأكد من صحة رقم الصفحة
        page = max(1, min(page, total_pages))
        
        start_index = (page - 1) * self.items_per_page
        end_index = min(start_index + self.items_per_page, total_items)
        
        paginated_items = items[start_index:end_index]
        
        return {
            'items': paginated_items,
            'current_page': page,
            'total_pages': total_pages,
            'total_items': total_items,
            'has_previous': page > 1,
            'has_next': page < total_pages,
            'start_index': start_index,
            'end_index': end_index
        }
    
    def create_pagination_keyboard(self, current_page: int, total_pages: int, 
                                 callback_prefix: str, 
                                 extra_data: str = "") -> InlineKeyboardMarkup:
        """إنشاء لوحة مفاتيح للتنقل بين الصفحات"""
        if total_pages <= 1:
            return None
        
        keyboard = []
        buttons = []
        
        # زر الصفحة السابقة
        if current_page > 1:
            buttons.append(InlineKeyboardButton(
                "⬅️ السابق",
                callback_data=f"{callback_prefix}_page_{current_page - 1}{extra_data}"
            ))
        
        # أزرار أرقام الصفحات
        page_buttons = self._get_page_number_buttons(
            current_page, total_pages, callback_prefix, extra_data
        )
        
        # زر الصفحة التالية
        if current_page < total_pages:
            buttons.append(InlineKeyboardButton(
                "➡️ التالي", 
                callback_data=f"{callback_prefix}_page_{current_page + 1}{extra_data}"
            ))
        
        # ترتيب الأزرار
        if len(buttons) > 0:
            keyboard.append(buttons)
        
        if page_buttons:
            keyboard.append(page_buttons)
        
        # إضافة معلومات الصفحة
        info_text = f"📄 {current_page}/{total_pages}"
        keyboard.append([InlineKeyboardButton(info_text, callback_data="page_info")])
        
        return InlineKeyboardMarkup(keyboard)
    
    def _get_page_number_buttons(self, current_page: int, total_pages: int,
                               callback_prefix: str, extra_data: str) -> List[InlineKeyboardButton]:
        """إنشاء أزرار أرقام الصفحات"""
        if total_pages <= 7:
            # عرض جميع الصفحات إذا كانت قليلة
            return [
                InlineKeyboardButton(
                    f"{'🔘' if i == current_page else str(i)}",
                    callback_data=f"{callback_prefix}_page_{i}{extra_data}" if i != current_page else "current_page"
                )
                for i in range(1, total_pages + 1)
            ]
        
        buttons = []
        
        # الصفحة الأولى
        if current_page > 3:
            buttons.append(InlineKeyboardButton(
                "1", callback_data=f"{callback_prefix}_page_1{extra_data}"
            ))
            if current_page > 4:
                buttons.append(InlineKeyboardButton("...", callback_data="dots"))
        
        # الصفحات المحيطة بالصفحة الحالية
        start = max(1, current_page - 1)
        end = min(total_pages + 1, current_page + 2)
        
        for i in range(start, end):
            if i == current_page:
                buttons.append(InlineKeyboardButton(
                    f"🔘", callback_data="current_page"
                ))
            else:
                buttons.append(InlineKeyboardButton(
                    str(i), callback_data=f"{callback_prefix}_page_{i}{extra_data}"
                ))
        
        # الصفحة الأخيرة
        if current_page < total_pages - 2:
            if current_page < total_pages - 3:
                buttons.append(InlineKeyboardButton("...", callback_data="dots"))
            buttons.append(InlineKeyboardButton(
                str(total_pages), callback_data=f"{callback_prefix}_page_{total_pages}{extra_data}"
            ))
        
        return buttons
    
    def create_list_display(self, items: List[Dict], page_info: Dict[str, Any],
                          format_item_func, title: str = "القائمة") -> str:
        """إنشاء نص عرض القائمة مع معلومات التصفح"""
        if not items:
            return f"📋 **{title}**\n\n❌ لا توجد عناصر للعرض."
        
        text = f"📋 **{title}**\n\n"
        
        # عرض العناصر
        for i, item in enumerate(items):
            item_number = page_info['start_index'] + i + 1
            formatted_item = format_item_func(item, item_number)
            text += f"{formatted_item}\n\n"
        
        # معلومات التصفح
        text += f"📄 الصفحة {page_info['current_page']} من {page_info['total_pages']}\n"
        text += f"📊 عرض {len(items)} من أصل {page_info['total_items']} عنصر"
        
        return text
    
    def parse_page_callback(self, callback_data: str) -> Optional[Tuple[str, int, str]]:
        """تحليل بيانات callback للتصفح"""
        try:
            parts = callback_data.split('_page_')
            if len(parts) != 2:
                return None
            
            prefix = parts[0]
            page_and_extra = parts[1]
            
            # فصل رقم الصفحة عن البيانات الإضافية
            if '_' in page_and_extra:
                page_str = page_and_extra.split('_')[0]
                extra_data = '_' + '_'.join(page_and_extra.split('_')[1:])
            else:
                page_str = page_and_extra
                extra_data = ""
            
            page = int(page_str)
            return prefix, page, extra_data
            
        except (ValueError, IndexError):
            return None

class DatabasePaginator:
    """مساعد التصفح لقواعد البيانات"""
    
    def __init__(self, items_per_page: int = 10):
        self.items_per_page = items_per_page
        self.pagination_helper = PaginationHelper(items_per_page)
    
    def paginate_query(self, base_query: str, params: Tuple, 
                      page: int = 1, order_by: str = "") -> Dict[str, Any]:
        """تنفيذ استعلام مع تصفح"""
        from bot_modules.database import get_db_connection
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        try:
            # حساب إجمالي العناصر
            count_query = f"SELECT COUNT(*) as total FROM ({base_query}) as subquery"
            cursor.execute(count_query, params)
            total_items = cursor.fetchone()['total']
            
            if total_items == 0:
                return {
                    'items': [],
                    'current_page': 1,
                    'total_pages': 1,
                    'total_items': 0,
                    'has_previous': False,
                    'has_next': False
                }
            
            # حساب معلومات التصفح
            total_pages = math.ceil(total_items / self.items_per_page)
            page = max(1, min(page, total_pages))
            offset = (page - 1) * self.items_per_page
            
            # تنفيذ الاستعلام مع LIMIT وOFFSET
            paginated_query = f"{base_query}"
            if order_by:
                paginated_query += f" ORDER BY {order_by}"
            paginated_query += f" LIMIT {self.items_per_page} OFFSET {offset}"
            
            cursor.execute(paginated_query, params)
            items = cursor.fetchall()
            
            return {
                'items': [dict(item) for item in items],
                'current_page': page,
                'total_pages': total_pages,
                'total_items': total_items,
                'has_previous': page > 1,
                'has_next': page < total_pages,
                'start_index': offset,
                'end_index': offset + len(items)
            }
            
        finally:
            conn.close()
    
    def create_paginated_display(self, query_result: Dict[str, Any],
                                format_item_func, title: str,
                                callback_prefix: str, extra_data: str = "") -> Tuple[str, InlineKeyboardMarkup]:
        """إنشاء عرض مقسم مع لوحة مفاتيح التنقل"""
        
        # إنشاء النص
        text = self.pagination_helper.create_list_display(
            query_result['items'], query_result, format_item_func, title
        )
        
        # إنشاء لوحة المفاتيح
        keyboard = self.pagination_helper.create_pagination_keyboard(
            query_result['current_page'],
            query_result['total_pages'],
            callback_prefix,
            extra_data
        )
        
        return text, keyboard

# مثيل عام للاستخدام
pagination_helper = PaginationHelper()
db_paginator = DatabasePaginator()

# دوال مساعدة للتنسيق الشائع
def format_user_item(user: Dict, item_number: int) -> str:
    """تنسيق عنصر مستخدم للعرض"""
    return f"{item_number}. 👤 **{user['full_name']}**\n" \
           f"   📱 {user.get('phone', 'غير محدد')}\n" \
           f"   💰 {user.get('balance', 0):,.2f} ريال\n" \
           f"   🏷️ {user.get('role', 'عميل')}"

def format_transaction_item(transaction: Dict, item_number: int) -> str:
    """تنسيق عنصر معاملة للعرض"""
    return f"{item_number}. 💸 **{transaction['type']}**\n" \
           f"   💰 {transaction.get('amount', 0):,.2f} ريال\n" \
           f"   📅 {transaction.get('created_at', 'غير محدد')}\n" \
           f"   📝 {transaction.get('description', 'بدون وصف')[:50]}..."

def format_network_item(network: Dict, item_number: int) -> str:
    """تنسيق عنصر شبكة للعرض"""
    return f"{item_number}. 🌐 **{network['name']}**\n" \
           f"   📡 {network.get('provider', 'غير محدد')}\n" \
           f"   📍 {network.get('city', 'غير محدد')}\n" \
           f"   ✅ {'متاحة' if network.get('is_active') else 'غير متاحة'}"