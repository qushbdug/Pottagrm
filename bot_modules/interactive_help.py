#!/usr/bin/env python3
"""
Interactive Help System - نظام المساعدة التفاعلي
يوفر مساعدة تفاعلية شاملة للمستخدمين مع أمثلة وإرشادات
"""

import logging
from typing import Dict, List, Optional, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

class InteractiveHelpSystem:
    """نظام المساعدة التفاعلي"""
    
    def __init__(self):
        self.help_categories = self._initialize_help_categories()
        self.quick_tips = self._initialize_quick_tips()
        self.faq = self._initialize_faq()
        self.tutorials = self._initialize_tutorials()
    
    def _initialize_help_categories(self) -> Dict[str, Dict[str, Any]]:
        """تهيئة فئات المساعدة"""
        return {
            'getting_started': {
                'title': '🚀 البداية السريعة',
                'description': 'كيفية البدء في استخدام البوت',
                'icon': '🚀',
                'priority': 1
            },
            'wallet': {
                'title': '💰 إدارة المحفظة',
                'description': 'كل ما يتعلق بالرصيد والمحفظة',
                'icon': '💰',
                'priority': 2
            },
            'cards': {
                'title': '🎫 شراء الكروت',
                'description': 'كيفية شراء واستخدام كروت الشحن',
                'icon': '🎫',
                'priority': 3
            },
            'transfers': {
                'title': '💸 التحويلات',
                'description': 'تحويل الأموال والرصيد',
                'icon': '💸',
                'priority': 4
            },
            'networks': {
                'title': '📡 الشبكات',
                'description': 'البحث عن الشبكات والموردين',
                'icon': '📡',
                'priority': 5
            },
            'coupons': {
                'title': '🎟️ الكوبونات',
                'description': 'استخدام كوبونات الخصم والعروض',
                'icon': '🎟️',
                'priority': 6
            },
            'reports': {
                'title': '📊 التقارير',
                'description': 'كشوف الحساب والتقارير المالية',
                'icon': '📊',
                'priority': 7
            },
            'troubleshooting': {
                'title': '🔧 حل المشاكل',
                'description': 'حلول للمشاكل الشائعة',
                'icon': '🔧',
                'priority': 8
            },
            'contact': {
                'title': '📞 التواصل',
                'description': 'كيفية التواصل مع الدعم الفني',
                'icon': '📞',
                'priority': 9
            }
        }
    
    def _initialize_quick_tips(self) -> List[Dict[str, str]]:
        """تهيئة النصائح السريعة"""
        return [
            {
                'title': '💡 نصيحة سريعة',
                'content': 'يمكنك استخدام /wallet لعرض رصيدك بسرعة في أي وقت!'
            },
            {
                'title': '🔍 نصيحة البحث',
                'content': 'استخدم البحث الذكي للعثور على أفضل الشبكات والأسعار!'
            },
            {
                'title': '🎟️ نصيحة الكوبونات',
                'content': 'تابع العروض والكوبونات للحصول على خصومات رائعة!'
            },
            {
                'title': '📊 نصيحة التقارير',
                'content': 'راجع كشف حسابك بانتظام لمتابعة مصروفاتك!'
            },
            {
                'title': '🔔 نصيحة الإشعارات',
                'content': 'فعّل الإشعارات لتبقى على اطلاع بآخر العروض والتحديثات!'
            }
        ]
    
    def _initialize_faq(self) -> Dict[str, Dict[str, str]]:
        """تهيئة الأسئلة الشائعة"""
        return {
            'how_to_register': {
                'question': 'كيف أسجل في النظام؟',
                'answer': '''للتسجيل في النظام:
1. اضغط على /start
2. أدخل اسمك الكامل
3. أدخل رقم هاتفك
4. اختر نوع حسابك (عميل/مورد)
5. ستحصل على رسالة تأكيد التسجيل

✅ **مبروك!** أصبحت الآن عضواً في نظام Yemen Net'''
            },
            'how_to_add_balance': {
                'question': 'كيف أشحن رصيدي؟',
                'answer': '''لشحن رصيدك:
1. اذهب إلى 💰 **محفظتي**
2. اختر **شحن الرصيد**
3. حدد طريقة الدفع المناسبة
4. أدخل المبلغ المطلوب
5. اتبع التعليمات لإتمام العملية

💡 **نصيحة:** يمكنك أيضاً استخدام الكوبونات لشحن رصيدك!'''
            },
            'how_to_buy_cards': {
                'question': 'كيف أشتري كروت الشحن؟',
                'answer': '''لشراء كروت الشحن:
1. اختر 🛒 **شراء كروت الشحن**
2. ابحث عن الشبكة المطلوبة
3. اختر نوع وقيمة الكرت
4. تأكد من كفاية رصيدك
5. أكد عملية الشراء

📱 ستحصل على كود الكرت فوراً بعد الشراء!'''
            },
            'how_to_transfer': {
                'question': 'كيف أحول رصيد لصديق؟',
                'answer': '''لتحويل الرصيد:
1. اختر 💸 **تحويل رصيد**
2. أدخل رقم هاتف المستلم
3. حدد المبلغ المراد تحويله
4. راجع تفاصيل التحويل
5. أكد العملية

⚠️ **تنبيه:** تأكد من صحة رقم الهاتف قبل التأكيد!'''
            },
            'forgot_password': {
                'question': 'نسيت كلمة المرور أو فقدت الوصول؟',
                'answer': '''إذا فقدت الوصول لحسابك:
1. تواصل مع الدعم الفني عبر 📞 **الدعم الفني**
2. أرسل رقم هاتفك المسجل
3. قدم إثبات هوية (إذا طُلب منك)
4. سيتم استعادة حسابك خلال 24 ساعة

🔐 **أمان:** لحماية حسابك، لا تشارك معلوماتك مع أحد!'''
            },
            'refund_policy': {
                'question': 'ما هي سياسة الاسترداد؟',
                'answer': '''سياسة الاسترداد:
• **كروت الشحن:** لا يمكن استردادها بعد إرسال الكود
• **الرصيد:** يمكن استرداده خلال 7 أيام بشروط
• **التحويلات الخاطئة:** يمكن إلغاؤها خلال ساعة واحدة
• **العمولات:** غير قابلة للاسترداد

📞 للاستفسارات، تواصل مع الدعم الفني'''
            }
        }
    
    def _initialize_tutorials(self) -> Dict[str, Dict[str, Any]]:
        """تهيئة الدروس التفاعلية"""
        return {
            'first_purchase': {
                'title': '🎯 أول عملية شراء',
                'description': 'دليل خطوة بخطوة لأول عملية شراء',
                'steps': [
                    {
                        'title': 'الخطوة 1: التسجيل',
                        'content': 'تأكد من أنك مسجل في النظام باستخدام /start',
                        'action': 'start_registration'
                    },
                    {
                        'title': 'الخطوة 2: شحن الرصيد',
                        'content': 'اشحن رصيدك أولاً قبل الشراء',
                        'action': 'go_to_wallet'
                    },
                    {
                        'title': 'الخطوة 3: اختيار الشبكة',
                        'content': 'ابحث عن الشبكة التي تريد شراء كرت منها',
                        'action': 'search_networks'
                    },
                    {
                        'title': 'الخطوة 4: الشراء',
                        'content': 'اختر قيمة الكرت وأكد عملية الشراء',
                        'action': 'buy_cards'
                    },
                    {
                        'title': 'الخطوة 5: استلام الكود',
                        'content': 'ستحصل على كود الكرت فوراً',
                        'action': 'view_purchases'
                    }
                ]
            },
            'become_supplier': {
                'title': '🏪 كيف تصبح مورد',
                'description': 'دليل شامل لتصبح مورد في النظام',
                'steps': [
                    {
                        'title': 'متطلبات المورد',
                        'content': 'تحتاج لحساب نشط ووثائق إثبات',
                        'action': 'supplier_requirements'
                    },
                    {
                        'title': 'طلب التفعيل',
                        'content': 'قدم طلب تفعيل كمورد',
                        'action': 'apply_supplier'
                    },
                    {
                        'title': 'إضافة الشبكات',
                        'content': 'أضف شبكاتك وخدماتك',
                        'action': 'add_networks'
                    },
                    {
                        'title': 'رفع الكروت',
                        'content': 'ارفع كروت الشحن المتاحة',
                        'action': 'upload_cards'
                    },
                    {
                        'title': 'بدء البيع',
                        'content': 'ابدأ في استقبال الطلبات والبيع',
                        'action': 'start_selling'
                    }
                ]
            }
        }
    
    async def show_help_menu(self, update: Update, context: CallbackContext) -> None:
        """عرض القائمة الرئيسية للمساعدة"""
        help_text = """
🆘 **مركز المساعدة التفاعلي** 🆘

مرحباً بك في مركز المساعدة الشامل!
اختر الموضوع الذي تحتاج مساعدة فيه:

💡 **نصيحة:** يمكنك العودة لهذه القائمة في أي وقت باستخدام /help
"""
        
        # إنشاء أزرار الفئات
        keyboard = []
        
        # ترتيب الفئات حسب الأولوية
        sorted_categories = sorted(
            self.help_categories.items(),
            key=lambda x: x[1]['priority']
        )
        
        # إضافة أزرار الفئات (صفين في كل مرة)
        for i in range(0, len(sorted_categories), 2):
            row = []
            for j in range(2):
                if i + j < len(sorted_categories):
                    cat_key, cat_info = sorted_categories[i + j]
                    row.append(InlineKeyboardButton(
                        f"{cat_info['icon']} {cat_info['title']}",
                        callback_data=f"help_category_{cat_key}"
                    ))
            keyboard.append(row)
        
        # أزرار إضافية
        keyboard.extend([
            [
                InlineKeyboardButton("❓ أسئلة شائعة", callback_data="help_faq"),
                InlineKeyboardButton("🎯 دروس تفاعلية", callback_data="help_tutorials")
            ],
            [
                InlineKeyboardButton("💡 نصائح سريعة", callback_data="help_quick_tips"),
                InlineKeyboardButton("🔍 بحث في المساعدة", callback_data="help_search")
            ],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if hasattr(update, 'callback_query') and update.callback_query:
            await update.callback_query.edit_message_text(
                help_text, parse_mode='Markdown', reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                help_text, parse_mode='Markdown', reply_markup=reply_markup
            )
    
    async def show_help_category(self, update: Update, context: CallbackContext, category: str) -> None:
        """عرض مساعدة فئة محددة"""
        if category not in self.help_categories:
            await self.show_help_menu(update, context)
            return
        
        cat_info = self.help_categories[category]
        
        # محتوى مخصص لكل فئة
        content = self._get_category_content(category)
        
        help_text = f"""
{cat_info['icon']} **{cat_info['title']}** {cat_info['icon']}

{content}

💡 **هل تحتاج مساعدة إضافية؟**
يمكنك التواصل مع الدعم الفني أو تصفح الأسئلة الشائعة.
"""
        
        # أزرار التنقل
        keyboard = [
            [
                InlineKeyboardButton("❓ أسئلة شائعة", callback_data="help_faq"),
                InlineKeyboardButton("📞 الدعم الفني", callback_data="contact_support")
            ],
            [
                InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu"),
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        
        # إضافة أزرار إجراءات سريعة حسب الفئة
        if category == 'wallet':
            keyboard.insert(0, [
                InlineKeyboardButton("💰 عرض المحفظة", callback_data="wallet"),
                InlineKeyboardButton("💸 تحويل رصيد", callback_data="transfer")
            ])
        elif category == 'cards':
            keyboard.insert(0, [
                InlineKeyboardButton("🛒 شراء كروت", callback_data="buy"),
                InlineKeyboardButton("🔍 البحث عن شبكات", callback_data="search_networks")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            help_text, parse_mode='Markdown', reply_markup=reply_markup
        )
    
    def _get_category_content(self, category: str) -> str:
        """الحصول على محتوى فئة المساعدة"""
        content_map = {
            'getting_started': """
🚀 **مرحباً بك في Yemen Net!**

للبدء في استخدام النظام:

1️⃣ **التسجيل:** اضغط /start وأدخل بياناتك
2️⃣ **شحن الرصيد:** اذهب للمحفظة واشحن رصيدك
3️⃣ **استكشاف الشبكات:** ابحث عن الشبكات المتاحة
4️⃣ **أول عملية شراء:** اشتر أول كرت شحن
5️⃣ **المتابعة:** راجع معاملاتك وكشف حسابك

🎯 **نصيحة:** ابدأ بمبلغ صغير لتجربة النظام أولاً!
""",
            'wallet': """
💰 **إدارة محفظتك الرقمية**

محفظتك هي مركز أموالك في النظام:

📊 **عرض الرصيد:** /wallet لعرض رصيدك الحالي
💳 **شحن الرصيد:** عدة طرق متاحة للشحن
💸 **تحويل الأموال:** حول لأصدقائك بسهولة
📈 **متابعة المعاملات:** راجع جميع عملياتك
🔒 **الأمان:** محفظتك محمية بأعلى معايير الأمان

⚠️ **تذكر:** لا تشارك معلومات حسابك مع أحد!
""",
            'cards': """
🎫 **شراء كروت الشحن**

كل ما تحتاج معرفته عن الكروت:

🔍 **البحث:** ابحث عن الشبكة المناسبة
💰 **الأسعار:** قارن الأسعار بين الموردين
⚡ **الشراء السريع:** اشتر واحصل على الكود فوراً
📱 **أنواع متعددة:** كروت لجميع الشبكات
✅ **ضمان الجودة:** جميع الكروت مضمونة

💡 **نصيحة:** احفظ أكواد الكروت في مكان آمن!
""",
            'transfers': """
💸 **التحويلات المالية**

نظام تحويل آمن وسريع:

👥 **للأصدقاء:** حول لأي مستخدم مسجل
⚡ **فوري:** التحويلات تتم في الحال
🔒 **آمن:** نظام حماية متقدم
📊 **تتبع:** راقب جميع تحويلاتك
💰 **رسوم منخفضة:** رسوم تنافسية

⚠️ **مهم:** تأكد من رقم الهاتف قبل التحويل!
""",
            'networks': """
📡 **الشبكات والموردين**

اكتشف أفضل الشبكات:

🔍 **البحث الذكي:** ابحث بالاسم أو المنطقة
⭐ **التقييمات:** اطلع على تقييمات الموردين
💰 **مقارنة الأسعار:** قارن واختر الأفضل
📍 **التوفر:** تحقق من توفر الكروت
🏆 **الموردين المعتمدين:** تعامل مع موردين موثوقين

💡 **نصيحة:** اختر الموردين ذوي التقييم العالي!
""",
            'coupons': """
🎟️ **الكوبونات والعروض**

وفر أكثر مع الكوبونات:

🎁 **كوبونات الخصم:** خصومات على المشتريات
💰 **كوبونات الشحن:** اشحن رصيدك بكوبون
⏰ **عروض محدودة:** لا تفوت العروض الخاصة
🔔 **الإشعارات:** فعّل الإشعارات للعروض الجديدة
📅 **تاريخ الانتهاء:** انتبه لتاريخ انتهاء الكوبونات

🎯 **نصيحة:** تابع قناة العروض للحصول على أحدث الكوبونات!
""",
            'reports': """
📊 **التقارير المالية**

راقب أموالك بدقة:

📈 **كشف الحساب:** تقرير مفصل لجميع معاملاتك
💹 **الإحصائيات:** إحصائيات شخصية مفيدة
📅 **فترات مختلفة:** تقارير يومية، أسبوعية، شهرية
📱 **تصدير:** احفظ تقاريرك كـ PDF أو Excel
📊 **الرسوم البيانية:** تمثيل بصري لمصروفاتك

💡 **نصيحة:** راجع كشف حسابك بانتظام!
""",
            'troubleshooting': """
🔧 **حل المشاكل الشائعة**

حلول سريعة للمشاكل:

❌ **مشكلة في التسجيل:** تحقق من صحة البيانات
💰 **مشكلة في الرصيد:** تأكد من إتمام عملية الشحن
🎫 **مشكلة في الكروت:** تواصل مع المورد أولاً
📱 **مشكلة في التطبيق:** أعد تشغيل المحادثة
🌐 **مشكلة في الاتصال:** تحقق من الإنترنت

🆘 **إذا لم تحل المشكلة:** تواصل مع الدعم الفني!
""",
            'contact': """
📞 **التواصل والدعم**

نحن هنا لمساعدتك:

🕒 **ساعات العمل:** 24/7 دعم متواصل
💬 **الدردشة:** دعم فوري عبر البوت
📧 **البريد الإلكتروني:** للاستفسارات المفصلة
📱 **الهاتف:** للحالات العاجلة
🎫 **تذاكر الدعم:** لتتبع طلباتك

⚡ **استجابة سريعة:** نرد خلال دقائق معدودة!
"""
        }
        
        return content_map.get(category, "محتوى غير متوفر حالياً.")
    
    async def show_faq(self, update: Update, context: CallbackContext) -> None:
        """عرض الأسئلة الشائعة"""
        faq_text = """
❓ **الأسئلة الشائعة** ❓

إليك أهم الأسئلة التي يطرحها المستخدمون:

اختر السؤال الذي تريد معرفة إجابته:
"""
        
        keyboard = []
        for faq_key, faq_item in self.faq.items():
            keyboard.append([InlineKeyboardButton(
                faq_item['question'],
                callback_data=f"help_faq_{faq_key}"
            )])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            faq_text, parse_mode='Markdown', reply_markup=reply_markup
        )
    
    async def show_faq_answer(self, update: Update, context: CallbackContext, faq_key: str) -> None:
        """عرض إجابة سؤال شائع"""
        if faq_key not in self.faq:
            await self.show_faq(update, context)
            return
        
        faq_item = self.faq[faq_key]
        
        answer_text = f"""
❓ **{faq_item['question']}**

{faq_item['answer']}

---
💡 **هل كانت هذه الإجابة مفيدة؟**
إذا كنت تحتاج مساعدة إضافية، تواصل مع الدعم الفني.
"""
        
        keyboard = [
            [
                InlineKeyboardButton("👍 مفيدة", callback_data=f"help_feedback_yes_{faq_key}"),
                InlineKeyboardButton("👎 غير مفيدة", callback_data=f"help_feedback_no_{faq_key}")
            ],
            [
                InlineKeyboardButton("❓ أسئلة أخرى", callback_data="help_faq"),
                InlineKeyboardButton("📞 الدعم الفني", callback_data="contact_support")
            ],
            [InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            answer_text, parse_mode='Markdown', reply_markup=reply_markup
        )
    
    async def show_quick_tips(self, update: Update, context: CallbackContext) -> None:
        """عرض النصائح السريعة"""
        import random
        
        # اختيار نصيحة عشوائية
        tip = random.choice(self.quick_tips)
        
        tip_text = f"""
{tip['title']} 

{tip['content']}

---
🔄 **هل تريد نصيحة أخرى؟**
اضغط على "نصيحة أخرى" للحصول على المزيد!
"""
        
        keyboard = [
            [
                InlineKeyboardButton("💡 نصيحة أخرى", callback_data="help_quick_tips"),
                InlineKeyboardButton("🎯 دروس تفاعلية", callback_data="help_tutorials")
            ],
            [
                InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu"),
                InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            tip_text, parse_mode='Markdown', reply_markup=reply_markup
        )
    
    async def show_tutorials(self, update: Update, context: CallbackContext) -> None:
        """عرض الدروس التفاعلية"""
        tutorials_text = """
🎯 **الدروس التفاعلية** 🎯

تعلم استخدام النظام خطوة بخطوة:

اختر الدرس الذي تريد تعلمه:
"""
        
        keyboard = []
        for tutorial_key, tutorial_info in self.tutorials.items():
            keyboard.append([InlineKeyboardButton(
                f"🎯 {tutorial_info['title']}",
                callback_data=f"help_tutorial_{tutorial_key}"
            )])
        
        keyboard.extend([
            [InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu")],
            [InlineKeyboardButton("🏠 القائمة الرئيسية", callback_data="main_menu")]
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            tutorials_text, parse_mode='Markdown', reply_markup=reply_markup
        )
    
    async def show_tutorial(self, update: Update, context: CallbackContext, 
                          tutorial_key: str, step: int = 0) -> None:
        """عرض درس تفاعلي"""
        if tutorial_key not in self.tutorials:
            await self.show_tutorials(update, context)
            return
        
        tutorial = self.tutorials[tutorial_key]
        steps = tutorial['steps']
        
        if step >= len(steps):
            # انتهاء الدرس
            completion_text = f"""
✅ **تهانينا!** 

لقد أكملت درس "{tutorial['title']}" بنجاح!

🎯 **ما تعلمته:**
{tutorial['description']}

💡 **الخطوة التالية:**
جرب تطبيق ما تعلمته الآن، أو تعلم درساً جديداً!
"""
            
            keyboard = [
                [
                    InlineKeyboardButton("🎯 درس آخر", callback_data="help_tutorials"),
                    InlineKeyboardButton("🏠 تطبيق ما تعلمت", callback_data="main_menu")
                ],
                [InlineKeyboardButton("🔙 العودة للمساعدة", callback_data="help_menu")]
            ]
            
        else:
            # عرض الخطوة الحالية
            current_step = steps[step]
            
            tutorial_text = f"""
🎯 **{tutorial['title']}**

**{current_step['title']}**

{current_step['content']}

---
📊 **التقدم:** {step + 1}/{len(steps)}
{'▓' * (step + 1)}{'░' * (len(steps) - step - 1)}
"""
            
            keyboard = []
            
            # زر الإجراء إذا كان متاحاً
            if 'action' in current_step:
                action_text = self._get_action_text(current_step['action'])
                keyboard.append([InlineKeyboardButton(
                    f"🚀 {action_text}",
                    callback_data=current_step['action']
                )])
            
            # أزرار التنقل
            nav_buttons = []
            if step > 0:
                nav_buttons.append(InlineKeyboardButton(
                    "⬅️ السابق",
                    callback_data=f"help_tutorial_{tutorial_key}_{step - 1}"
                ))
            
            nav_buttons.append(InlineKeyboardButton(
                "➡️ التالي",
                callback_data=f"help_tutorial_{tutorial_key}_{step + 1}"
            ))
            
            keyboard.append(nav_buttons)
            keyboard.append([InlineKeyboardButton("🔙 قائمة الدروس", callback_data="help_tutorials")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.callback_query.edit_message_text(
            tutorial_text if step < len(steps) else completion_text,
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    def _get_action_text(self, action: str) -> str:
        """الحصول على نص الإجراء"""
        action_texts = {
            'start_registration': 'ابدأ التسجيل',
            'go_to_wallet': 'اذهب للمحفظة',
            'search_networks': 'ابحث عن الشبكات',
            'buy_cards': 'شراء الكروت',
            'view_purchases': 'عرض المشتريات',
            'supplier_requirements': 'متطلبات المورد',
            'apply_supplier': 'طلب التفعيل',
            'add_networks': 'إضافة شبكات',
            'upload_cards': 'رفع الكروت',
            'start_selling': 'بدء البيع'
        }
        
        return action_texts.get(action, 'تنفيذ الإجراء')

# إنشاء مثيل عام للاستخدام
interactive_help = InteractiveHelpSystem()