# 🤖 بوت يمن نت - Yemen Net Bot

بوت تليجرام متطور لبيع كروت الشبكة مع ميزات متقدمة وإدارة ذكية للمستخدمين.

## ✨ الميزات الرئيسية

- 🛒 نظام بيع كروت الشبكة
- 💰 إدارة المحافظ الإلكترونية
- 📊 نظام تقييم المستخدمين
- 🔔 نظام إشعارات ذكي
- 📈 تقارير وإحصائيات مفصلة
- 🔐 نظام صلاحيات متقدم
- 🌐 دعم webhook و polling

## 🚀 التثبيت والتشغيل

### المتطلبات
- Python 3.8+
- قاعدة بيانات SQLite
- توكن بوت تليجرام

### التثبيت
```bash
# استنساخ المستودع
git clone <repository-url>
cd yemen-net-bot

# تثبيت المتطلبات
pip install -r requirements.txt

# إعداد متغيرات البيئة
cp .env.example .env
# تعديل .env بإعداداتك
```

### التشغيل

#### للتطوير المحلي (Polling)
```bash
python run_bot.py
```

#### للإنتاج (Webhook)
```bash
python start.py
```

## 📁 هيكل المشروع

```
yemen-net-bot/
├── bot/                    # الوحدات الرئيسية
│   ├── config.py          # إعدادات البوت
│   ├── database/          # قاعدة البيانات
│   ├── models/            # نماذج البيانات
│   ├── services/          # الخدمات
│   └── utils/             # أدوات مساعدة
├── main_bot.py            # البوت الرئيسي
├── run_bot.py             # تشغيل البوت (polling)
├── start.py               # تشغيل البوت (webhook)
├── render.yaml            # إعدادات Render
└── requirements.txt       # المتطلبات
```

## 🔧 الإعداد

### متغيرات البيئة
```env
BOT_TOKEN=your_bot_token_here
DATABASE_URL=sqlite:///yemen_net.db
WEBHOOK_URL=https://your-domain.com
PORT=10000
```

### إعداد قاعدة البيانات
```bash
# تشغيل الترحيلات
python -c "from bot.database.migrations import run_migrations; run_migrations()"
```

## 📱 الأوامر المتاحة

- `/start` - بدء البوت
- `/menu` - القائمة الرئيسية
- `/balance` - عرض الرصيد
- `/wallet` - إدارة المحفظة
- `/stats` - الإحصائيات
- `/rating` - نظام التقييم
- `/notifications` - الإشعارات
- `/reports` - التقارير

## 🚀 النشر على Render

1. اربط مستودع GitHub بـ Render
2. اختر "Web Service"
3. استخدم `start.py` كملف التشغيل
4. أضف متغيرات البيئة المطلوبة

## 🐛 استكشاف الأخطاء

### مشكلة "Application is still running"
- تأكد من استخدام ملف تشغيل واحد فقط
- استخدم `start.py` للإنتاج و `run_bot.py` للتطوير

### مشاكل قاعدة البيانات
- تأكد من تشغيل الترحيلات
- تحقق من صلاحيات الملفات

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT.

## 🤝 المساهمة

نرحب بالمساهمات! يرجى:
1. عمل Fork للمشروع
2. إنشاء branch جديد
3. إجراء التغييرات
4. إرسال Pull Request

## 📞 الدعم

للحصول على المساعدة:
- 📧 البريد الإلكتروني: support@example.com
- 💬 مجموعة تليجرام: [رابط المجموعة]
- 🐛 تقارير الأخطاء: [رابط Issues]

---

**تم التطوير بواسطة فريق يمن نت** 🇾🇪