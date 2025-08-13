# 🚀 دليل النشر - Deployment Guide

## 📋 النشر على Render

### 1. إعداد GitHub
```bash
# إضافة التغييرات
git add .
git commit -m "إصلاح مشكلة Application is still running وتنظيف المستودع"
git push origin main
```

### 2. إعداد Render
1. اذهب إلى [render.com](https://render.com)
2. اضغط "New +" → "Web Service"
3. اربط مستودع GitHub
4. اختر المستودع `yemen-net-bot`

### 3. إعدادات الخدمة
- **Name**: `yemen-net-bot`
- **Environment**: `Python 3`
- **Build Command**: `pip install -r requirements.txt`
- **Start Command**: `python start.py`
- **Plan**: `Free`

### 4. متغيرات البيئة
أضف هذه المتغيرات في Render:

| المتغير | القيمة | الوصف |
|---------|--------|--------|
| `BOT_TOKEN` | `your_bot_token` | توكن البوت من @BotFather |
| `ENCRYPTION_KEY_B64` | `auto_generated` | مفتاح التشفير (سيتم إنشاؤه تلقائياً) |
| `ENVIRONMENT` | `production` | بيئة التشغيل |
| `PORT` | `10000` | منفذ التشغيل |

### 5. النشر
1. اضغط "Create Web Service"
2. انتظر انتهاء عملية البناء
3. البوت سيعمل تلقائياً على الرابط المقدم

## 🔧 النشر المحلي

### للتطوير
```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# تشغيل البوت
python run_bot.py
```

### للإنتاج المحلي
```bash
# إعداد متغيرات البيئة
export BOT_TOKEN="your_bot_token"
export ENVIRONMENT="production"

# تشغيل البوت
python start.py
```

## 📱 اختبار البوت

### 1. التحقق من التشغيل
- ✅ رسالة "تم إعداد الأوامر السريعة بنجاح"
- ✅ رسالة "تشغيل webhook على المنفذ 10000"
- ✅ رسالة "Application started"

### 2. اختبار الأوامر
- `/start` - بدء البوت
- `/menu` - القائمة الرئيسية
- `/balance` - عرض الرصيد

## 🐛 استكشاف الأخطاء

### مشكلة "Application is still running"
**الحل**: استخدم ملف تشغيل واحد فقط:
- `start.py` للإنتاج
- `run_bot.py` للتطوير

### مشكلة webhook
**الحل**: تأكد من:
- صحة `WEBHOOK_URL`
- صحة `PORT`
- إعدادات Render

### مشكلة قاعدة البيانات
**الحل**: شغل الترحيلات:
```bash
python -c "from bot.database.migrations import run_migrations; run_migrations()"
```

## 📊 مراقبة الأداء

### سجلات Render
- اذهب إلى خدمتك في Render
- اضغط على "Logs"
- راقب السجلات للتأكد من عدم وجود أخطاء

### إحصائيات البوت
- استخدم أمر `/stats` في البوت
- راقب عدد المستخدمين والنشاط

## 🔄 التحديثات

### تحديث الكود
```bash
git pull origin main
# Render سيقوم بالتحديث تلقائياً
```

### تحديث المتطلبات
```bash
# تحديث requirements.txt
git add requirements.txt
git commit -m "تحديث المتطلبات"
git push origin main
```

---

**🎯 نصائح مهمة**:
- تأكد من صحة `BOT_TOKEN`
- استخدم `start.py` للإنتاج فقط
- راقب السجلات بانتظام
- احتفظ بنسخة احتياطية من قاعدة البيانات