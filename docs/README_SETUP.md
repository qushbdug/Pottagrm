# 🚀 دليل تثبيت وتشغيل بوت Pottagrm Enhanced

## 📋 نظرة عامة

بوت تليجرام متكامل لبيع كروت الشبكة، إدارة المستخدمين، والمحفظة الإلكترونية مع ميزات متقدمة شاملة.

## ⭐ الميزات الرئيسية الجديدة

### 🛒 نظام المبيعات المتكامل
- إدارة متقدمة لكروت الشبكة والمنتجات
- تتبع المخزون في الوقت الفعلي
- تقارير مبيعات تفصيلية ومرئية
- نظام التحكم في المخزون مع تنبيهات النقص

### 👥 إدارة المستخدمين المطورة
- نظام صلاحيات متعدد المستويات
- أدوار محسنة: عملاء، وكلاء، مزودين، مشرفين، مشرف أعلى
- تتبع نشاط المستخدمين وسجل العمليات
- إدارة الجلسات والأمان المعزز

### 💳 المحفظة الإلكترونية المتقدمة
- تاريخ معاملات مفصل مع إحصائيات
- تقارير الإنفاق والإيداعات
- تنبيهات الرصيد الذكية
- إعدادات محفظة قابلة للتخصيص

### 📊 التقارير والتحليلات
- تقارير شخصية للعملاء
- تحليلات أداء للمزودين
- تقارير إدارية شاملة
- تصدير البيانات بصيغ متعددة

### 🔔 نظام الإشعارات الذكي
- إشعارات مخصصة حسب تفضيلات المستخدم
- تنبيهات فورية للمعاملات
- إشعارات العروض والخصومات
- جدولة الإشعارات والساعات الهادئة

### ⭐ نظام التقييم والمراجعات
- تقييم البائعين والمنتجات
- مراجعات المستخدمين
- إحصائيات التقييمات
- نظام السمعة المتقدم

### 🎁 العروض والخصومات
- إنشاء عروض مخصصة
- خصومات شرطية ومحدودة الاستخدام
- تتبع استخدام العروض
- تنبيهات العروض الجديدة

## 🔧 متطلبات التشغيل

### البرمجيات المطلوبة
- Python 3.8 أو أحدث
- SQLite3 (مدمج مع Python)
- pip (مدير حزم Python)

### مساحة التخزين
- الحد الأدنى: 500 MB
- المستحسن: 2 GB للتشغيل المستمر

### ذاكرة النظام
- الحد الأدنى: 1 GB RAM
- المستحسن: 2 GB RAM

## 📦 التثبيت السريع

### 1. تحميل الملفات
```bash
# تحميل المشروع
git clone https://github.com/your-repo/pottagrm-enhanced.git
cd pottagrm-enhanced

# أو تحميل ملف ZIP والاستخراج
unzip pottagrm-enhanced.zip
cd pottagrm-enhanced
```

### 2. تثبيت المتطلبات
```bash
# تثبيت المكتبات المطلوبة
pip install -r requirements.txt

# أو تثبيت فردي إذا فشل الأمر السابق
pip install python-telegram-bot==20.7
pip install requests>=2.31.0
pip install cryptography>=41.0.0
pip install pandas>=2.1.0
pip install matplotlib>=3.7.0
pip install seaborn>=0.12.0
pip install Pillow>=10.0.0
pip install qrcode>=7.4.2
pip install aiofiles>=23.2.1
```

### 3. التشغيل المباشر
```bash
# تشغيل البوت
python yemen_net_bot.py
```

## ⚙️ الإعداد التفصيلي

### 1. إعدادات البوت

#### رمز البوت (محفوظ في الكود)
- الرمز الحالي: `7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0`
- **ملاحظة مهمة**: تم الحفاظ على الرمز كما طُلب

#### متغيرات البيئة الاختيارية
```bash
# إنشاء ملف .env (اختياري)
DB_PATH=yemen_net.db
CARD_COMMISSION_RATE=0.10
AGENT_COMMISSION_RATE=0.05
```

### 2. إعداد قاعدة البيانات

البوت سيقوم تلقائياً بإنشاء قاعدة البيانات والجداول عند التشغيل الأول:

```bash
# سيتم إنشاء هذه الملفات تلقائياً:
- yemen_net.db (قاعدة البيانات الرئيسية)
- encryption.key (مفتاح التشفير)
- yemen_net_bot_data (بيانات المحادثات المحفوظة)
```

### 3. إنشاء المشرف الأعلى

عند التشغيل الأول، سيتم إنشاء حساب المشرف الأعلى تلقائياً مع البيانات التالية:
- الاسم: مشرف أعلى النظام
- الهاتف: 777777777
- رقم المحفظة: 791234567

## 🐳 النشر باستخدام Docker

### 1. إنشاء Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "yemen_net_bot.py"]
```

### 2. بناء وتشغيل الحاوية
```bash
# بناء الصورة
docker build -t pottagrm-enhanced .

# تشغيل الحاوية
docker run -d --name pottagrm-bot \
  -v $(pwd)/data:/app/data \
  pottagrm-enhanced
```

## ☁️ النشر على Render

### 1. إعداد ملف render.yaml
```yaml
services:
  - type: web
    name: pottagrm-enhanced
    env: python
    buildCommand: pip install -r requirements.txt
    startCommand: python yemen_net_bot.py
    envVars:
      - key: PYTHON_VERSION
        value: 3.11.0
```

### 2. خطوات النشر
1. إنشاء حساب على [Render.com](https://render.com)
2. ربط المستودع من GitHub
3. اختيار "Web Service"
4. تحديد الإعدادات:
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `python yemen_net_bot.py`
5. النشر والتشغيل

## 🚀 النشر على Heroku

### 1. إعداد الملفات المطلوبة

#### Procfile
```
worker: python yemen_net_bot.py
```

#### runtime.txt
```
python-3.11.0
```

### 2. أوامر النشر
```bash
# تسجيل الدخول لـ Heroku
heroku login

# إنشاء تطبيق جديد
heroku create pottagrm-enhanced

# رفع الكود
git push heroku main

# تشغيل العامل
heroku ps:scale worker=1
```

## 📱 اختبار البوت

### 1. التحقق من التشغيل
```bash
# سجلات التشغيل
tail -f bot.log

# أو في Docker
docker logs -f pottagrm-bot
```

### 2. اختبار الوظائف الأساسية
1. إرسال `/start` للبوت
2. التسجيل كمستخدم جديد
3. اختبار شراء كرت تجريبي
4. فحص المحفظة والتحويلات

## 🔒 الأمان والحماية

### 1. تشفير البيانات
- جميع أكواد الكروت مشفرة في قاعدة البيانات
- مفتاح التشفير منفصل ومحمي
- كلمات المرور مُجمعة (hashed)

### 2. حماية النظام
```bash
# تحديث النظام بانتظام
pip install --upgrade -r requirements.txt

# نسخة احتياطية من قاعدة البيانات
cp yemen_net.db backup/yemen_net_$(date +%Y%m%d).db
```

### 3. مراقبة الأمان
- تسجيل جميع العمليات
- تتبع محاولات الوصول المشبوهة
- تنبيهات أمان فورية للمشرفين

## 📊 مراقبة الأداء

### 1. سجلات النظام
```bash
# عرض السجلات المباشرة
tail -f logs/bot.log

# فلترة الأخطاء
grep ERROR logs/bot.log
```

### 2. إحصائيات الاستخدام
- لوحة معلومات المشرف الأعلى
- تقارير الأداء اليومية
- إحصائيات المستخدمين النشطين

## 🔧 استكشاف الأخطاء وإصلاحها

### المشاكل الشائعة

#### 1. البوت لا يستجيب
```bash
# التحقق من الرمز المميز
python -c "import requests; print(requests.get('https://api.telegram.org/bot7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0/getMe').json())"

# إعادة تشغيل البوت
pkill -f yemen_net_bot.py
python yemen_net_bot.py
```

#### 2. خطأ في قاعدة البيانات
```bash
# التحقق من سلامة قاعدة البيانات
sqlite3 yemen_net.db "PRAGMA integrity_check;"

# إنشاء نسخة احتياطية
cp yemen_net.db yemen_net_backup.db
```

#### 3. مشاكل المكتبات
```bash
# إعادة تثبيت المكتبات
pip uninstall -y -r requirements.txt
pip install -r requirements.txt
```

## 🆕 الميزات الجديدة في هذا الإصدار

### المضافات الجديدة
✅ محفظة إلكترونية متطورة مع تحليلات
✅ نظام تقييم شامل للبائعين والمنتجات  
✅ إشعارات ذكية قابلة للتخصيص
✅ تقارير مبيعات متقدمة مع رسوم بيانية
✅ نظام عروض وخصومات متطور
✅ إدارة مخزون في الوقت الفعلي
✅ تتبع نشاط المستخدمين
✅ إعدادات أمان معززة
✅ واجهة مستخدم محسنة ومنظمة
✅ دعم للنشر السحابي

### التحسينات
🔄 أداء محسن لقاعدة البيانات
🔄 معالجة أخطاء شاملة
🔄 تسجيل متقدم للعمليات
🔄 واجهة مستخدم أكثر جاذبية
🔄 استقرار أفضل في التشغيل المستمر

## 📞 الدعم والمساعدة

### للحصول على المساعدة
- 📧 البريد الإلكتروني: support@pottagrm.com
- 💬 تلغرام: @PottagrmSupport  
- 🐛 تقارير الأخطاء: إنشاء issue في المستودع

### الموارد المفيدة
- [وثائق Telegram Bot API](https://core.telegram.org/bots/api)
- [مجتمع Python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [دليل SQLite](https://www.sqlite.org/docs.html)

## 📄 الترخيص

هذا المشروع مرخص تحت ترخيص MIT - راجع ملف [LICENSE](LICENSE) للتفاصيل.

## 🙏 شكر وتقدير

شكر خاص لجميع المساهمين والمطورين الذين ساعدوا في تطوير هذا البوت المتقدم.

---

**ملاحظة مهمة**: تم الحفاظ على جميع الميزات الموجودة في الكود الأصلي وإضافة ميزات جديدة متطورة دون التأثير على الوظائف الحالية.

© 2024 Pottagrm Enhanced. جميع الحقوق محفوظة.