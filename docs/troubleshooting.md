# 🛠️ دليل استكشاف الأخطاء - بوت يمن نت

دليل شامل لحل المشاكل الشائعة التي قد تواجهها عند استخدام بوت يمن نت.

## 🚨 مشاكل التشغيل

### 1. خطأ "This Application is still running!"

**المشكلة**: 
```
ERROR - خطأ حرج في تشغيل البوت: This Application is still running!
```

**السبب**: 
- البوت يعمل بالفعل في مكان آخر
- مشكلة في إدارة event loop
- ملفات مؤقتة قديمة

**الحل**:
```bash
# 1. إيقاف جميع عمليات Python
pkill -f python

# 2. حذف الملفات المؤقتة
make clean

# 3. إعادة تشغيل البوت
python main.py
```

### 2. خطأ "Module not found"

**المشكلة**:
```
ModuleNotFoundError: No module named 'bot'
```

**السبب**:
- عدم تفعيل البيئة الافتراضية
- مشكلة في Python path
- عدم تثبيت المتطلبات

**الحل**:
```bash
# 1. تفعيل البيئة الافتراضية
source venv/bin/activate

# 2. إعادة تثبيت المتطلبات
pip install -r requirements.txt

# 3. التأكد من Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### 3. خطأ "Invalid token"

**المشكلة**:
```
telegram.error.InvalidToken: Invalid token
```

**السبب**:
- توكن البوت غير صحيح
- البوت تم حظره
- مشكلة في ملف .env

**الحل**:
```bash
# 1. التحقق من التوكن
cat .env | grep BOT_TOKEN

# 2. إنشاء بوت جديد عبر @BotFather
# 3. تحديث التوكن في .env
# 4. إعادة تشغيل البوت
```

## 🗄️ مشاكل قاعدة البيانات

### 1. خطأ "Database is locked"

**المشكلة**:
```
sqlite3.OperationalError: database is locked
```

**السبب**:
- قاعدة البيانات مفتوحة في مكان آخر
- مشكلة في الصلاحيات
- عملية كتابة متعددة

**الحل**:
```bash
# 1. إيقاف البوت
pkill -f python

# 2. حذف ملف قاعدة البيانات
rm yemen_net.db

# 3. إعادة تشغيل البوت (سيتم إنشاء قاعدة جديدة)
python main.py
```

### 2. خطأ "Table doesn't exist"

**المشكلة**:
```
sqlite3.OperationalError: no such table
```

**السبب**:
- عدم تشغيل الترحيلات
- قاعدة البيانات تالفة
- مشكلة في النماذج

**الحل**:
```bash
# 1. تشغيل الترحيلات
make migrate

# 2. أو يدوياً
python -c "from bot.database.migrations import run_migrations; run_migrations()"
```

### 3. خطأ "Permission denied"

**المشكلة**:
```
sqlite3.OperationalError: unable to open database file
```

**السبب**:
- مشكلة في الصلاحيات
- المسار غير صحيح
- القرص ممتلئ

**الحل**:
```bash
# 1. فحص الصلاحيات
ls -la yemen_net.db

# 2. تغيير الصلاحيات
chmod 644 yemen_net.db

# 3. فحص المساحة المتاحة
df -h
```

## 🌐 مشاكل الشبكة

### 1. خطأ "Connection timeout"

**المشكلة**:
```
httpx.ConnectTimeout: connection timeout
```

**السبب**:
- مشكلة في الإنترنت
- حظر من قبل مزود الخدمة
- مشكلة في DNS

**الحل**:
```bash
# 1. فحص الاتصال
ping api.telegram.org

# 2. تغيير DNS
echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf

# 3. استخدام VPN إذا لزم الأمر
```

### 2. خطأ "SSL Certificate"

**المشكلة**:
```
ssl.SSLCertVerificationError: certificate verify failed
```

**السبب**:
- شهادة SSL منتهية الصلاحية
- مشكلة في تاريخ النظام
- مشكلة في Python SSL

**الحل**:
```bash
# 1. تحديث شهادات SSL
sudo apt-get update && sudo apt-get install ca-certificates

# 2. تحديث Python
pip install --upgrade python-telegram-bot

# 3. فحص تاريخ النظام
date
```

## 🔐 مشاكل الأمان

### 1. خطأ "Encryption key"

**المشكلة**:
```
cryptography.fernet.InvalidToken
```

**السبب**:
- مفتاح التشفير غير صحيح
- مشكلة في متغير البيئة
- مفتاح تالف

**الحل**:
```bash
# 1. إنشاء مفتاح جديد
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# 2. تحديث .env
echo "ENCRYPTION_KEY_B64=your_new_key_here" >> .env

# 3. إعادة تشغيل البوت
```

### 2. خطأ "Authentication failed"

**المشكلة**:
```
telegram.error.Unauthorized: Unauthorized
```

**السبب**:
- البوت تم حظره
- التوكن منتهي الصلاحية
- مشكلة في حساب البوت

**الحل**:
```bash
# 1. فحص حالة البوت عبر @BotFather
# 2. إنشاء بوت جديد إذا لزم الأمر
# 3. تحديث التوكن
```

## 📱 مشاكل Telegram

### 1. البوت لا يستجيب

**المشكلة**: البوت لا يستجيب للأوامر

**السبب**:
- البوت متوقف
- مشكلة في webhook
- مشكلة في polling

**الحل**:
```bash
# 1. فحص حالة البوت
ps aux | grep python

# 2. فحص السجلات
tail -f logs/bot.log

# 3. إعادة تشغيل البوت
python main.py
```

### 2. خطأ في webhook

**المشكلة**:
```
telegram.error.TelegramError: Bad Request: wrong webhook
```

**السبب**:
- عنوان webhook غير صحيح
- مشكلة في SSL
- مشكلة في المنفذ

**الحل**:
```bash
# 1. فحص إعدادات webhook
cat .env | grep WEBHOOK

# 2. إعادة تعيين webhook
curl -X POST "https://api.telegram.org/bot<TOKEN>/deleteWebhook"

# 3. إعادة تشغيل البوت
```

## 🐳 مشاكل Docker

### 1. خطأ "Port already in use"

**المشكلة**:
```
Error: Port 10000 is already in use
```

**الحل**:
```bash
# 1. فحص المنافذ المستخدمة
netstat -tulpn | grep :10000

# 2. إيقاف الخدمة
sudo lsof -ti:10000 | xargs kill -9

# 3. أو تغيير المنفذ في docker-compose.yml
```

### 2. خطأ "Container won't start"

**المشكلة**: الحاوية لا تبدأ

**الحل**:
```bash
# 1. فحص السجلات
docker-compose logs bot

# 2. إعادة بناء الحاوية
docker-compose build --no-cache

# 3. إعادة تشغيل
docker-compose up -d
```

## 🔧 مشاكل النظام

### 1. خطأ "Out of memory"

**المشكلة**:
```
MemoryError: out of memory
```

**الحل**:
```bash
# 1. فحص استخدام الذاكرة
free -h

# 2. إيقاف الخدمات غير الضرورية
# 3. زيادة swap
sudo fallocate -l 1G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

### 2. خطأ "Disk full"

**المشكلة**:
```
OSError: [Errno 28] No space left on device
```

**الحل**:
```bash
# 1. فحص المساحة
df -h

# 2. تنظيف الملفات المؤقتة
make clean

# 3. حذف النسخ الاحتياطية القديمة
find . -name "*_backup_*.db" -mtime +7 -delete
```

## 📊 تشخيص المشاكل

### 1. فحص السجلات

```bash
# عرض السجلات في الوقت الفعلي
tail -f logs/bot.log

# البحث عن أخطاء
grep "ERROR" logs/bot.log

# البحث عن تحذيرات
grep "WARNING" logs/bot.log
```

### 2. فحص العمليات

```bash
# فحص عمليات Python
ps aux | grep python

# فحص استخدام الموارد
top -p $(pgrep -f python)

# فحص المنافذ
netstat -tulpn | grep python
```

### 3. فحص قاعدة البيانات

```bash
# فحص حالة قاعدة البيانات
sqlite3 yemen_net.db ".tables"

# فحص حجم قاعدة البيانات
ls -lh yemen_net.db

# فحص الصلاحيات
ls -la yemen_net.db
```

## 🚀 حلول سريعة

### إعادة تشغيل كاملة

```bash
# 1. إيقاف البوت
pkill -f python

# 2. تنظيف الملفات
make clean

# 3. إعادة تشغيل
python main.py
```

### إعادة تثبيت

```bash
# 1. حذف البيئة الافتراضية
rm -rf venv

# 2. إنشاء بيئة جديدة
python3 -m venv venv
source venv/bin/activate

# 3. تثبيت المتطلبات
pip install -r requirements.txt

# 4. تشغيل البوت
python main.py
```

### فحص شامل

```bash
# 1. تشغيل الاختبارات
make test

# 2. فحص جودة الكود
make lint

# 3. تنسيق الكود
make format

# 4. فحص قاعدة البيانات
make migrate
```

## 📞 الحصول على المساعدة

إذا لم تتمكن من حل المشكلة:

1. **📚 راجع الوثائق**: اقرأ [دليل التثبيت](installation.md)
2. **🔍 ابحث في Issues**: تحقق من [GitHub Issues](https://github.com/your-username/yemen-net-bot/issues)
3. **💬 تواصل معنا**:
   - 📧 البريد الإلكتروني: support@yemen-net.com
   - 💬 تليجرام: @YemenNetSupport
4. **🐛 أبلغ عن المشكلة**: أنشئ Issue جديد مع تفاصيل المشكلة

### معلومات مطلوبة للمساعدة

عند الإبلاغ عن مشكلة، تأكد من تضمين:

- **نظام التشغيل**: Ubuntu 20.04, Windows 10, macOS 12
- **إصدار Python**: python --version
- **إصدار البوت**: من CHANGELOG.md
- **رسالة الخطأ الكاملة**: مع traceback
- **خطوات إعادة الإنتاج**: خطوات واضحة
- **السجلات**: محتوى logs/bot.log

---

**💡 نصيحة**: استخدم `make help` لرؤية جميع الأوامر المتاحة للمساعدة في استكشاف الأخطاء!