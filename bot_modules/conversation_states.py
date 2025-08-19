#!/usr/bin/env python3
"""
إدارة حالات المحادثة للبوت
Conversation States Management
"""

from enum import IntEnum
from telegram.ext import ConversationHandler

# تعريف حالات المحادثة
class ConversationStates(IntEnum):
    """حالات المحادثة المختلفة"""
    
    # حالات التسجيل
    REGISTRATION_PHONE = 1
    REGISTRATION_NAME = 2
    
    # حالات شراء الكروت
    BUY_SELECT_NETWORK = 10
    BUY_SELECT_CATEGORY = 11
    BUY_CONFIRM_PURCHASE = 12
    BUY_PAYMENT_METHOD = 13
    
    # حالات تحويل الرصيد
    TRANSFER_SEARCH_USER = 20
    TRANSFER_ENTER_AMOUNT = 21
    TRANSFER_CONFIRM = 22
    
    # حالات إضافة الشبكة (للمزود)
    ADD_NETWORK_NAME = 30
    ADD_NETWORK_PROVIDER = 31
    ADD_NETWORK_DESCRIPTION = 32
    ADD_NETWORK_LOCATION = 33
    
    # حالات رفع الكروت
    UPLOAD_SELECT_NETWORK = 40
    UPLOAD_SELECT_CATEGORY = 41
    UPLOAD_ENTER_CARDS = 42
    UPLOAD_CONFIRM = 43
    
    # حالات إنشاء العروض (للمشرف الأعلى)
    CREATE_OFFER_TITLE = 50
    CREATE_OFFER_DESCRIPTION = 51
    CREATE_OFFER_DISCOUNT = 52
    CREATE_OFFER_DURATION = 53
    CREATE_OFFER_MAX_USES = 54
    
    # حالات إنشاء الكوبونات
    CREATE_COUPON_AMOUNT = 60
    CREATE_COUPON_QUANTITY = 61
    CREATE_COUPON_EXPIRY = 62
    
    # حالات البحث
    SEARCH_USER_INPUT = 70
    SEARCH_NETWORK_INPUT = 71
    
    # حالات الإدارة
    ADMIN_BROADCAST_MESSAGE = 80
    ADMIN_ADD_BALANCE = 81
    ADMIN_BAN_USER = 82

# قاموس ترجمة الحالات للعربية
STATE_NAMES = {
    ConversationStates.REGISTRATION_PHONE: "إدخال رقم الهاتف",
    ConversationStates.REGISTRATION_NAME: "إدخال الاسم",
    ConversationStates.BUY_SELECT_NETWORK: "اختيار الشبكة للشراء",
    ConversationStates.BUY_SELECT_CATEGORY: "اختيار فئة الكرت",
    ConversationStates.BUY_CONFIRM_PURCHASE: "تأكيد الشراء",
    ConversationStates.TRANSFER_SEARCH_USER: "البحث عن المستخدم للتحويل",
    ConversationStates.TRANSFER_ENTER_AMOUNT: "إدخال مبلغ التحويل",
    ConversationStates.TRANSFER_CONFIRM: "تأكيد التحويل",
    ConversationStates.ADD_NETWORK_NAME: "إدخال اسم الشبكة",
    ConversationStates.ADD_NETWORK_PROVIDER: "إدخال اسم المزود",
    ConversationStates.ADD_NETWORK_DESCRIPTION: "إدخال وصف الشبكة",
    ConversationStates.ADD_NETWORK_LOCATION: "إدخال موقع الشبكة",
    ConversationStates.CREATE_OFFER_TITLE: "إدخال عنوان العرض",
    ConversationStates.CREATE_OFFER_DESCRIPTION: "إدخال وصف العرض",
    ConversationStates.CREATE_OFFER_DISCOUNT: "إدخال نسبة الخصم",
    ConversationStates.SEARCH_USER_INPUT: "إدخال معايير البحث",
    ConversationStates.ADMIN_BROADCAST_MESSAGE: "إدخال رسالة البث",
}

def get_state_name(state: int) -> str:
    """الحصول على اسم الحالة بالعربية"""
    return STATE_NAMES.get(state, f"حالة غير معرفة ({state})")

def clear_conversation_state(context):
    """مسح حالة المحادثة"""
    context.user_data.clear()

def set_conversation_state(context, state: ConversationStates, **data):
    """تعيين حالة المحادثة مع بيانات إضافية"""
    context.user_data.clear()  # مسح الحالة السابقة
    context.user_data['conversation_state'] = state
    context.user_data['state_name'] = get_state_name(state)
    context.user_data['state_started_at'] = datetime.now().isoformat()
    
    # إضافة البيانات الإضافية
    for key, value in data.items():
        context.user_data[key] = value

def get_conversation_state(context) -> tuple:
    """الحصول على حالة المحادثة الحالية"""
    state = context.user_data.get('conversation_state')
    state_name = context.user_data.get('state_name', 'غير محدد')
    return state, state_name

def is_in_conversation(context) -> bool:
    """التحقق من وجود محادثة نشطة"""
    return 'conversation_state' in context.user_data

# معالجات الإلغاء
async def cancel_conversation(update, context):
    """إلغاء المحادثة الحالية"""
    try:
        state, state_name = get_conversation_state(context)
        
        if state:
            clear_conversation_state(context)
            await update.message.reply_text(
                f"❌ تم إلغاء: {state_name}\n\n"
                f"يمكنك البدء من جديد في أي وقت.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
        else:
            await update.message.reply_text(
                "ℹ️ لا توجد عملية نشطة للإلغاء.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
                ])
            )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in cancel conversation: {e}")
        clear_conversation_state(context)
        await update.message.reply_text("تم الإلغاء.")
        return ConversationHandler.END

# معالج انتهاء المهلة الزمنية
async def conversation_timeout(update, context):
    """معالجة انتهاء مهلة المحادثة"""
    try:
        state, state_name = get_conversation_state(context)
        clear_conversation_state(context)
        
        await update.message.reply_text(
            f"⏰ انتهت مهلة العملية: {state_name}\n\n"
            f"يمكنك البدء من جديد في أي وقت.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
            ])
        )
        
        return ConversationHandler.END
        
    except Exception as e:
        logger.error(f"Error in conversation timeout: {e}")
        return ConversationHandler.END