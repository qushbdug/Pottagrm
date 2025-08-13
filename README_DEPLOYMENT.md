# 🚀 دليل النشر على Render - بوت يمن نت

دليل شامل لنشر بوت يمن نت على منصة Render.

## 📋 المتطلبات

- حساب على [Render.com](https://render.com)
- مستودع GitHub يحتوي على الكود
- توكن بوت تليجرام صالح

## 🔧 إعداد GitHub

### 1. رفع الكود إلى GitHub

```bash
# إضافة التغييرات
git add .

# عمل commit
git commit -m "Prepare for Render deployment"

# رفع الكود
git push origin main
```

### 2. التأكد من وجود الملفات المطلوبة

- ✅ `render.yaml` - إعدادات Render
- ✅ `main.py` - نقطة الدخول الرئيسية
- ✅ `requirements.txt` - المتطلبات
- ✅ `build.sh` - سكريبت البناء
- ✅ `Procfile` - ملف Procfile
- ✅ `runtime.txt` - إصدار Python

## 🌐 إعداد Render

### 1. إنشاء حساب Render

1. اذهب إلى [render.com](https://render.com)
2. انقر على "Sign Up"
3. اختر "Continue with GitHub"
4. اربط حساب GitHub

### 2. إنشاء Web Service

1. انقر على "New +"
2. اختر "Web Service"
3. اربط مستودع GitHub
4. اختر مستودع `yemen-net-bot`

### 3. إعدادات الخدمة

```
Name: yemen-net-bot
Environment: Python 3
Region: Frankfurt (EU Central) - أو أقرب منطقة لك
Branch: main
Build Command: chmod +x build.sh && ./build.sh
Start Command: python main.py
```

### 4. متغيرات البيئة

Render سيقوم بتعيين هذه المتغيرات تلقائياً من `render.yaml`:

```
BOT_TOKEN=7766964799:AAHex-hGfjPX6g_R2aZ7-UPrgnFxQKAjSa0
DB_PATH=/opt/render/project/src/yemen_net.db
ENCRYPTION_KEY_B64=8KqXzP9vN2mR7sL4tQ1wE6yU3iO8pA5dF2gH9jK4lZ7xV1bN6mQ3wE9rT4yU7i
PYTHONPATH=/opt/render/project/src
PORT=10000
RENDER=true
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

### 5. إعدادات متقدمة

```
Auto-Deploy: Yes
Health Check Path: /
Health Check Timeout: 300
```

## 🚀 النشر

### 1. إنشاء الخدمة

1. انقر على "Create Web Service"
2. انتظر حتى يكتمل البناء
3. تأكد من أن البوت يعمل

### 2. مراقبة النشر

- **Build Logs**: مراقبة عملية البناء
- **Runtime Logs**: مراقبة تشغيل البوت
- **Health Checks**: التأكد من صحة الخدمة

### 3. اختبار البوت

1. انتظر حتى يكتمل النشر
2. اذهب إلى بوتك على تليجرام: @Vsjsgshh_bot
3. أرسل `/start` للتأكد من عمله
4. اختبر الأوامر الأخرى

## 🔍 استكشاف الأخطاء

### مشاكل شائعة

#### 1. خطأ في البناء

```bash
# فحص ملف requirements.txt
# تأكد من صحة إصدارات المكتبات
# فحص ملف build.sh
```

#### 2. خطأ في التشغيل

```bash
# فحص Runtime Logs
# تأكد من صحة BOT_TOKEN
# فحص متغيرات البيئة
```

#### 3. البوت لا يستجيب

```bash
# فحص Health Checks
# تأكد من أن الخدمة تعمل
# فحص سجلات البوت
```

### حلول سريعة

```bash
# إعادة تشغيل الخدمة
# إعادة البناء
# فحص السجلات
```

## 📊 مراقبة الأداء

### 1. Render Dashboard

- **Uptime**: وقت التشغيل
- **Response Time**: وقت الاستجابة
- **Error Rate**: معدل الأخطاء

### 2. سجلات البوت

```bash
# في Render Dashboard
# Runtime Logs
# البحث عن أخطاء
```

### 3. مراقبة Telegram

- **Bot Status**: حالة البوت
- **Message Count**: عدد الرسائل
- **Error Reports**: تقارير الأخطاء

## 🔄 التحديثات

### 1. النشر التلقائي

- كل push إلى `main` سيؤدي إلى نشر تلقائي
- يمكن تعطيل النشر التلقائي عند الحاجة

### 2. النشر اليدوي

```bash
# في Render Dashboard
# Manual Deploy
# اختيار الفرع المطلوب
```

### 3. Rollback

- يمكن العودة لإصدار سابق
- من Render Dashboard
# Deploy History

## 💰 التكاليف

### الخطة المجانية

- **Build Time**: 500 دقيقة/شهر
- **Runtime**: 750 ساعة/شهر
- **Bandwidth**: 100GB/شهر
- **Disk**: 1GB

### الخطة المدفوعة

- **Build Time**: غير محدود
- **Runtime**: غير محدود
- **Bandwidth**: 1TB/شهر
- **Disk**: 10GB

## 🔒 الأمان

### 1. حماية التوكن

- التوكن محمي في متغيرات البيئة
- لا يظهر في السجلات العامة
- يمكن تغييره من Render Dashboard

### 2. قاعدة البيانات

- قاعدة البيانات محفوظة على قرص Render
- نسخ احتياطية تلقائية
- تشفير البيانات

### 3. الوصول

- HTTPS تلقائي
- حماية من DDoS
- مراقبة الأمان

## 📞 الدعم

### Render Support

- **Documentation**: [docs.render.com](https://docs.render.com)
- **Community**: [community.render.com](https://community.render.com)
- **Status**: [status.render.com](https://status.render.com)

### Yemen Net Bot Support

- **Email**: support@yemen-net.com
- **Telegram**: @YemenNetSupport
- **GitHub Issues**: للإبلاغ عن المشاكل

## 🎯 الخطوات التالية

1. **نشر البوت** على Render
2. **اختبار البوت** للتأكد من عمله
3. **إضافة وصف وصورة** للبوت عبر @BotFather
4. **مراقبة الأداء** من Render Dashboard
5. **إعداد النسخ الاحتياطية** لقاعدة البيانات

---

**🎉 تهانينا! البوت جاهز للنشر على Render!**

> 💡 **نصيحة**: تأكد من اختبار البوت محلياً قبل النشر على Render!