from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
import random
import logging
from deep_translator import GoogleTranslator  # استبدال googletrans بـ deep-translator

# تفعيل التسجيل للتحقق من الأخطاء
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# تخزين بيانات المستخدمين والمحادثات
users_waiting = []  # قائمة بالمستخدمين الذين ينتظرون شريك دردشة
active_chats = {}   # تخزين المحادثات النشطة {user_id: partner_id}
user_languages = {}  # تخزين لغات المستخدمين {user_id: language}
user_settings = {}   # تخزين إعدادات المستخدمين {user_id: {"gender": "male", "age": 25, "hide_media": False, "notifications": True}}
user_points = {}     # تخزين نقاط المكافآت للمستخدمين {user_id: points}

# قائمة اللغات المدعومة
LANGUAGES = {
    "en": "الإنجليزية",
    "ar": "العربية",
    "es": "الإسبانية",
    "fr": "الفرنسية",
    "de": "الألمانية",
    "zh": "الصينية",
    "hi": "الهندية",
    "ru": "الروسية",
    "pt": "البرتغالية",
    "ja": "اليابانية",
    "tr": "التركية"
}

# تعريف الأمر /start
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    await update.message.reply_text(
        "🏠 مرحبًا! أنا بوت دردشة عشوائية.\n"
        "🔍 استخدم /search للبحث عن شريك دردشة.\n"
        "⏹️ استخدم /stop لإنهاء المحادثة الحالية.\n"
        "⭐ استخدم /rate لتقييم شريكك بعد انتهاء المحادثة.\n"
        "🌐 استخدم /language لتغيير اللغة.\n"
        "⚙️ استخدم /settings لتغيير الإعدادات.\n"
        "🎁 استخدم /rewards لعرض نقاط المكافآت."
    )

# تعريف الأمر /settings
async def settings(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    keyboard = [
        [InlineKeyboardButton("🔍 البحث عن شريك", callback_data="find_partner")],
        [InlineKeyboardButton("👫 البحث حسب الجنس", callback_data="search_by_gender")],
        [InlineKeyboardButton("🌐 تغيير اللغة", callback_data="set_language")],
        [InlineKeyboardButton("⚙️ الإعدادات الأخرى", callback_data="other_settings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚙️ اختر الإعداد الذي تريد تغييره:\n\n"
        "ملاحظة: سيتم مطابقتك فقط مع مستخدمين يتحدثون نفس اللغة.",
        reply_markup=reply_markup
    )

# معالجة اختيار الإعدادات
async def settings_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    action = query.data

    if action == "find_partner":
        await search(update, context)

    elif action == "search_by_gender":
        keyboard = [
            [InlineKeyboardButton("👨 ذكر", callback_data="gender_male")],
            [InlineKeyboardButton("👩 أنثى", callback_data="gender_female")],
            [InlineKeyboardButton("🤖 غير محدد", callback_data="gender_other")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("👫 اختر الجنس الذي تريد البحث عنه:", reply_markup=reply_markup)

    elif action == "set_language":
        keyboard = []
        for code, name in LANGUAGES.items():
            keyboard.append([InlineKeyboardButton(name, callback_data=f"lang_{code}")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🌐 اختر اللغة المفضلة:", reply_markup=reply_markup)

    elif action == "other_settings":
        keyboard = [
            [InlineKeyboardButton("🎂 العمر", callback_data="set_age")],
            [InlineKeyboardButton("🖼️ إخفاء الصور/الفيديوهات", callback_data="toggle_hide_media")],
            [InlineKeyboardButton("🔔 الإشعارات", callback_data="toggle_notifications")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("⚙️ الإعدادات الأخرى:", reply_markup=reply_markup)

# معالجة اختيار اللغة
async def language_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    language_code = query.data.replace("lang_", "")
    user_languages[user_id] = language_code
    await query.edit_message_text(f"✅ تم تعيين اللغة إلى: {LANGUAGES[language_code]}")

# معالجة اختيار الجنس
async def gender_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    gender = query.data.replace("gender_", "")
    user_settings[user_id]["gender"] = gender
    await query.edit_message_text(f"✅ تم تعيين الجنس إلى: {gender}")

# معالجة إدخال العمر
async def age_handler(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    age_text = update.message.text

    if not age_text.isdigit() or not (13 <= int(age_text) <= 100):
        await update.message.reply_text("⚠️ الرجاء إدخال عمر صحيح (رقم بين 13 و 100).")
        return

    user_settings[user_id]["age"] = int(age_text)
    await update.message.reply_text(f"✅ تم تعيين العمر إلى: {age_text}")

# تعريف الأمر /search
async def search(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id in active_chats:
        await update.message.reply_text("⚠️ أنت بالفعل في محادثة! استخدم /stop لإنهاء المحادثة الحالية.")
        return

    if user_id in users_waiting:
        await update.message.reply_text("⏳ جارٍ البحث عن شريك...")
        return

    users_waiting.append(user_id)
    await update.message.reply_text("🔍 جارٍ البحث عن شريك دردشة...")

    if len(users_waiting) >= 2:
        user1 = users_waiting.pop(0)
        user2 = users_waiting.pop(0)
        active_chats[user1] = user2
        active_chats[user2] = user1

        await context.bot.send_message(user1, "✅ تم العثور على شريك! ابدأ المحادثة الآن.")
        await context.bot.send_message(user2, "✅ تم العثور على شريك! ابدأ المحادثة الآن.")

# تعريف الأمر /stop
async def stop(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in active_chats:
        await update.message.reply_text("⚠️ أنت لست في محادثة حاليًا.")
        return

    partner_id = active_chats[user_id]
    del active_chats[user_id]
    del active_chats[partner_id]

    await update.message.reply_text("⏹️ تم إنهاء المحادثة. استخدم /search للبحث عن شريك جديد.")
    await context.bot.send_message(partner_id, "⏹️ قام شريكك بإنهاء المحادثة. استخدم /search للبحث عن شريك جديد.")

# تعريف الأمر /rate
async def rate(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in active_chats:
        await update.message.reply_text("⚠️ يجب أن تكون في محادثة لتقييم شريكك.")
        return

    keyboard = [
        [InlineKeyboardButton("⭐ 1", callback_data="1"),
         InlineKeyboardButton("⭐ 2", callback_data="2"),
         InlineKeyboardButton("⭐ 3", callback_data="3"),
         InlineKeyboardButton("⭐ 4", callback_data="4"),
         InlineKeyboardButton("⭐ 5", callback_data="5")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⭐ قم بتقييم شريكك:", reply_markup=reply_markup)

# معالجة تقييم المستخدم
async def rate_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    rating = query.data
    await query.edit_message_text(f"شكرًا لتقييمك! لقد قمت بتقييم شريكك بــ {rating} نجوم.")

# تعريف الأمر /rewards
async def rewards(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    points = user_points.get(user_id, 0)
    await update.message.reply_text(f"🎁 لديك {points} نقطة مكافأة. استخدمها للحصول على مزايا إضافية!")

# معالجة الرسائل النصية
async def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id

    if user_id not in active_chats:
        await update.message.reply_text("⚠️ استخدم /search للبحث عن شريك دردشة.")
        return

    partner_id = active_chats[user_id]
    user_lang = user_languages.get(user_id, "en")
    partner_lang = user_languages.get(partner_id, "en")

    # ترجمة الرسالة إلى لغة الشريك
    translated_text = GoogleTranslator(source=user_lang, target=partner_lang).translate(update.message.text)
    await context.bot.send_message(partner_id, translated_text)

# تعريف الأمر /help
async def help_command(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "🛠️ قائمة الأوامر:\n"
        "🏠 /start - بدء البوت وعرض التعليمات.\n"
        "🔍 /search - البحث عن شريك دردشة.\n"
        "⏹️ /stop - إنهاء المحادثة الحالية.\n"
        "⭐ /rate - تقييم شريكك بعد انتهاء المحادثة.\n"
        "🌐 /language - تغيير اللغة.\n"
        "⚙️ /settings - تغيير الإعدادات.\n"
        "🎁 /rewards - عرض نقاط المكافآت.\n"
        "🛡️ /help - عرض قائمة الأوامر."
    )

# تشغيل البوت
async def main():
    # استبدل "YOUR_TELEGRAM_BOT_TOKEN" بتوكن البوت الخاص بك
    application = Application.builder().token("7876398831:AAHY5P7JOARoFE8KlNecP-2UNR8kDUA3-WM").build()

    # تعريف الأوامر
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("search", search))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("rate", rate))
    application.add_handler(CommandHandler("settings", settings))
    application.add_handler(CommandHandler("rewards", rewards))
    application.add_handler(CommandHandler("help", help_command))

    # معالجة الرسائل النصية
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # معالجة الأزرار التفاعلية
    application.add_handler(CallbackQueryHandler(settings_handler, pattern="^(find_partner|search_by_gender|set_language|other_settings)$"))
    application.add_handler(CallbackQueryHandler(language_handler, pattern="^lang_"))
    application.add_handler(CallbackQueryHandler(gender_handler, pattern="^gender_"))
    application.add_handler(CallbackQueryHandler(rate_handler, pattern="^(1|2|3|4|5)$"))

    # معالجة إدخال العمر
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, age_handler))

    # بدء البوت
    await application.run_polling()

# تشغيل البوت في Google Colab أو بيئة Python
if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
