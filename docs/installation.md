# 🚀 دليل التثبيت - بوت يمن نت

دليل شامل لتثبيت وتشغيل بوت يمن نت على نظامك المحلي أو على منصة Render.

## 📋 المتطلبات

### متطلبات النظام
- **نظام التشغيل**: Windows 10+, macOS 10.14+, أو Linux
- **Python**: الإصدار 3.8 أو أحدث
- **RAM**: 512 MB على الأقل
- **مساحة التخزين**: 100 MB متاحة

### متطلبات البرامج
- **Python 3.8+** مع pip
- **Git** (للاستنساخ)
- **توكن بوت تليجرام** (من @BotFather)

## 🔧 التثبيت

### 1. استنساخ المستودع

```bash
# استنساخ المستودع
git clone https://github.com/your-username/yemen-net-bot.git
cd yemen-net-bot

# أو باستخدام SSH
git clone git@github.com:your-username/yemen-net-bot.git
cd yemen-net-bot
```

### 2. إعداد البيئة الافتراضية

```bash
# إنشاء بيئة افتراضية
python3 -m venv venv

# تفعيل البيئة الافتراضية
# على Windows
venv\Scripts\activate

# على macOS/Linux
source venv/bin/activate
```

### 3. تثبيت المتطلبات

```bash
# تثبيت المتطلبات
pip install -r requirements.txt

# أو باستخدام التثبيت السريع
make install
```

### 4. إعداد متغيرات البيئة

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل الملف بإعداداتك
nano .env  # أو استخدام أي محرر نصوص
```

#### محتوى ملف `.env`:

```env
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here

# Database Configuration
DB_PATH=yemen_net.db

# Security
ENCRYPTION_KEY_B64=your_encryption_key_here

# Render Configuration (for production)
RENDER=true
PORT=10000
RENDER_EXTERNAL_HOSTNAME=your-app-name.onrender.com

# Logging
LOG_LEVEL=INFO
LOG_FILE=bot.log

# Development
DEBUG=false
ENVIRONMENT=production
```

### 5. الحصول على توكن البوت

1. اذهب إلى [@BotFather](https://t.me/BotFather) على تليجرام
2. أرسل `/newbot`
3. اتبع التعليمات لإنشاء بوت جديد
4. انسخ التوكن وأضفه في ملف `.env`

## 🚀 التشغيل

### التشغيل المحلي (للتطوير)

```bash
# تشغيل البوت
python run_bot.py

# أو باستخدام Makefile
make run
```

### التشغيل في الإنتاج

```bash
# تشغيل البوت
python main.py

# أو باستخدام Makefile
make run-prod
```

### التشغيل باستخدام Docker

```bash
# بناء وتشغيل الحاويات
docker-compose up -d

# عرض السجلات
docker-compose logs -f bot

# إيقاف الحاويات
docker-compose down
```

## ✅ التحقق من التثبيت

### 1. اختبار الاتصال

```bash
# تشغيل الاختبارات
make test

# أو يدوياً
python -m pytest tests/ -v
```

### 2. اختبار البوت

1. شغل البوت
2. اذهب إلى بوتك على تليجرام
3. أرسل `/start`
4. تأكد من استلام رسالة الترحيب

### 3. فحص السجلات

```bash
# عرض السجلات
tail -f logs/bot.log

# أو فحص الحالة
docker-compose ps
```

## 🐛 استكشاف الأخطاء

### مشاكل شائعة

#### 1. خطأ "Module not found"

```bash
# تأكد من تفعيل البيئة الافتراضية
source venv/bin/activate

# إعادة تثبيت المتطلبات
pip install -r requirements.txt
```

#### 2. خطأ "Invalid token"

- تأكد من صحة التوكن في ملف `.env`
- تأكد من أن البوت لم يتم حظره
- جرب إنشاء بوت جديد

#### 3. خطأ "Port already in use"

```bash
# تغيير المنفذ في ملف .env
PORT=10001

# أو إيقاف الخدمة التي تستخدم المنفذ
sudo lsof -ti:10000 | xargs kill -9
```

#### 4. خطأ "Database locked"

```bash
# إعادة تشغيل البوت
# أو حذف ملف قاعدة البيانات وإعادة إنشائه
rm yemen_net.db
```

## 🔧 الإعدادات المتقدمة

### 1. إعداد قاعدة البيانات

```bash
# تشغيل الترحيلات
make migrate

# أو يدوياً
python -c "from bot.database.migrations import run_migrations; run_migrations()"
```

### 2. إعداد Redis (اختياري)

```bash
# تثبيت Redis
sudo apt-get install redis-server  # Ubuntu/Debian
brew install redis                  # macOS

# تشغيل Redis
redis-server
```

### 3. إعداد Nginx (للإنتاج)

```bash
# تثبيت Nginx
sudo apt-get install nginx

# نسخ ملف الإعدادات
sudo cp nginx/nginx.conf /etc/nginx/nginx.conf

# إعادة تشغيل Nginx
sudo systemctl restart nginx
```

## 📱 النشر على Render

### 1. رفع الكود إلى GitHub

```bash
# إضافة التغييرات
git add .

# عمل commit
git commit -m "Initial commit"

# رفع الكود
git push origin main
```

### 2. إعداد Render

1. اذهب إلى [render.com](https://render.com)
2. أنشئ حساب جديد أو سجل دخول
3. انقر على "New +" → "Web Service"
4. اربط مستودع GitHub
5. اختر المستودع `yemen-net-bot`
6. أدخل الإعدادات:
   - **Name**: `yemen-net-bot`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`

### 3. إعداد متغيرات البيئة

في Render، أضف متغيرات البيئة:

```
BOT_TOKEN=your_bot_token_here
ENCRYPTION_KEY_B64=your_encryption_key_here
RENDER=true
PORT=10000
```

## 🔍 المراقبة والصيانة

### 1. مراقبة السجلات

```bash
# مراقبة السجلات في الوقت الفعلي
tail -f logs/bot.log

# البحث عن أخطاء
grep "ERROR" logs/bot.log
```

### 2. النسخ الاحتياطي

```bash
# إنشاء نسخة احتياطية
make backup

# أو باستخدام السكريبت
./scripts/backup.sh
```

### 3. التحديثات

```bash
# سحب التحديثات
git pull origin main

# إعادة تثبيت المتطلبات
pip install -r requirements.txt

# إعادة تشغيل البوت
```

## 📞 الدعم

إذا واجهت أي مشاكل:

- 📧 **البريد الإلكتروني**: support@yemen-net.com
- 💬 **تليجرام**: @YemenNetSupport
- 🐛 **GitHub Issues**: للإبلاغ عن الأخطاء
- 📚 **الوثائق**: راجع [دليل استكشاف الأخطاء](troubleshooting.md)

## 🎯 الخطوات التالية

بعد التثبيت الناجح:

1. 📖 اقرأ [دليل المستخدم](user-guide.md)
2. 🔧 تعلم [كيفية التطوير](developer.md)
3. 🚀 اكتشف [الميزات المتقدمة](features.md)
4. 📊 تعلم [كيفية المراقبة](monitoring.md)

---

**🎉 تهانينا! لقد قمت بتثبيت بوت يمن نت بنجاح!**

> 💡 **نصيحة**: استخدم `make help` لرؤية جميع الأوامر المتاحة!