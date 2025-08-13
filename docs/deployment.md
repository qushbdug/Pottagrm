# 🚀 دليل النشر - بوت يمن نت

دليل شامل لنشر بوت يمن نت على منصات مختلفة مع أفضل الممارسات.

## 📋 قبل النشر

### 1. التحقق من الكود

```bash
# تشغيل الاختبارات
make test

# فحص جودة الكود
make lint

# تنسيق الكود
make format

# فحص قاعدة البيانات
make migrate
```

### 2. إعداد متغيرات البيئة

```bash
# نسخ ملف البيئة
cp .env.example .env

# تعديل الملف
nano .env
```

#### متغيرات البيئة المطلوبة:

```env
# Telegram Bot
BOT_TOKEN=your_bot_token_here

# Security
ENCRYPTION_KEY_B64=your_encryption_key_here

# Environment
ENVIRONMENT=production
DEBUG=false

# Database
DB_PATH=yemen_net.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=bot.log
```

### 3. إنشاء مفتاح التشفير

```bash
# إنشاء مفتاح جديد
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"

# نسخ النتيجة إلى .env
echo "ENCRYPTION_KEY_B64=your_generated_key" >> .env
```

## 🌐 النشر على Render

### 1. إعداد GitHub

```bash
# إضافة التغييرات
git add .

# عمل commit
git commit -m "Prepare for deployment"

# رفع الكود
git push origin main
```

### 2. إنشاء حساب Render

1. اذهب إلى [render.com](https://render.com)
2. أنشئ حساب جديد أو سجل دخول
3. اربط حساب GitHub

### 3. إنشاء Web Service

1. انقر على "New +" → "Web Service"
2. اختر مستودع `yemen-net-bot`
3. أدخل الإعدادات:

```
Name: yemen-net-bot
Environment: Python 3
Region: Frankfurt (EU Central)
Branch: main
Build Command: pip install -r requirements.txt
Start Command: python main.py
```

### 4. إعداد متغيرات البيئة

في Render، أضف متغيرات البيئة:

```
BOT_TOKEN=your_bot_token_here
ENCRYPTION_KEY_B64=your_encryption_key_here
RENDER=true
PORT=10000
ENVIRONMENT=production
DEBUG=false
```

### 5. إعدادات متقدمة

```
Auto-Deploy: Yes
Health Check Path: /
Health Check Timeout: 300
```

### 6. النشر

1. انقر على "Create Web Service"
2. انتظر حتى يكتمل البناء
3. تأكد من أن البوت يعمل

## 🐳 النشر باستخدام Docker

### 1. بناء الصورة

```bash
# بناء صورة Docker
docker build -t yemen-net-bot .

# فحص الصورة
docker images | grep yemen-net-bot
```

### 2. تشغيل الحاوية

```bash
# تشغيل الحاوية
docker run -d \
  --name yemen-net-bot \
  -p 10000:10000 \
  -e BOT_TOKEN=your_token \
  -e ENCRYPTION_KEY_B64=your_key \
  yemen-net-bot

# فحص الحالة
docker ps
```

### 3. استخدام Docker Compose

```bash
# تشغيل جميع الخدمات
docker-compose up -d

# عرض السجلات
docker-compose logs -f bot

# إيقاف الخدمات
docker-compose down
```

## ☁️ النشر على VPS

### 1. إعداد الخادم

```bash
# تحديث النظام
sudo apt update && sudo apt upgrade -y

# تثبيت Python
sudo apt install python3 python3-pip python3-venv -y

# تثبيت Git
sudo apt install git -y

# تثبيت Nginx
sudo apt install nginx -y
```

### 2. استنساخ المشروع

```bash
# استنساخ المستودع
git clone https://github.com/your-username/yemen-net-bot.git
cd yemen-net-bot

# إنشاء بيئة افتراضية
python3 -m venv venv
source venv/bin/activate

# تثبيت المتطلبات
pip install -r requirements.txt
```

### 3. إعداد Systemd Service

```bash
# إنشاء ملف الخدمة
sudo nano /etc/systemd/system/yemen-net-bot.service
```

#### محتوى الملف:

```ini
[Unit]
Description=Yemen Net Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/yemen-net-bot
Environment=PATH=/home/ubuntu/yemen-net-bot/venv/bin
ExecStart=/home/ubuntu/yemen-net-bot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 4. تشغيل الخدمة

```bash
# إعادة تحميل systemd
sudo systemctl daemon-reload

# تفعيل الخدمة
sudo systemctl enable yemen-net-bot

# تشغيل الخدمة
sudo systemctl start yemen-net-bot

# فحص الحالة
sudo systemctl status yemen-net-bot
```

### 5. إعداد Nginx

```bash
# إنشاء ملف إعدادات
sudo nano /etc/nginx/sites-available/yemen-net-bot
```

#### محتوى الملف:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
# تفعيل الموقع
sudo ln -s /etc/nginx/sites-available/yemen-net-bot /etc/nginx/sites-enabled/

# اختبار الإعدادات
sudo nginx -t

# إعادة تشغيل Nginx
sudo systemctl restart nginx
```

## 🔒 إعدادات الأمان

### 1. جدار الحماية

```bash
# تثبيت UFW
sudo apt install ufw -y

# إعداد القواعد
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow 80
sudo ufw allow 443
sudo ufw allow 10000

# تفعيل جدار الحماية
sudo ufw enable
```

### 2. SSL Certificate

```bash
# تثبيت Certbot
sudo apt install certbot python3-certbot-nginx -y

# الحصول على شهادة SSL
sudo certbot --nginx -d your-domain.com

# تجديد تلقائي
sudo crontab -e
# أضف: 0 12 * * * /usr/bin/certbot renew --quiet
```

### 3. تحديثات أمنية

```bash
# تحديث تلقائي للأمان
sudo apt install unattended-upgrades -y

# تفعيل التحديثات التلقائية
sudo dpkg-reconfigure -plow unattended-upgrades
```

## 📊 المراقبة والصيانة

### 1. مراقبة السجلات

```bash
# مراقبة سجلات البوت
tail -f logs/bot.log

# مراقبة سجلات النظام
sudo journalctl -u yemen-net-bot -f

# مراقبة سجلات Nginx
sudo tail -f /var/log/nginx/access.log
```

### 2. النسخ الاحتياطي

```bash
# إنشاء نسخة احتياطية
./scripts/backup.sh

# أو يدوياً
cp yemen_net.db "backup_$(date +%Y%m%d_%H%M%S).db"
```

### 3. التحديثات

```bash
# سحب التحديثات
git pull origin main

# إعادة تثبيت المتطلبات
pip install -r requirements.txt

# إعادة تشغيل الخدمة
sudo systemctl restart yemen-net-bot
```

## 🚨 استكشاف الأخطاء

### 1. مشاكل شائعة

#### البوت لا يعمل
```bash
# فحص حالة الخدمة
sudo systemctl status yemen-net-bot

# فحص السجلات
sudo journalctl -u yemen-net-bot -n 50

# فحص المنافذ
sudo netstat -tulpn | grep :10000
```

#### مشاكل في Nginx
```bash
# اختبار الإعدادات
sudo nginx -t

# فحص السجلات
sudo tail -f /var/log/nginx/error.log

# إعادة تشغيل Nginx
sudo systemctl restart nginx
```

### 2. إعادة التشغيل

```bash
# إعادة تشغيل كاملة
sudo systemctl restart yemen-net-bot
sudo systemctl restart nginx

# أو إعادة تشغيل النظام
sudo reboot
```

## 📱 اختبار النشر

### 1. اختبار الاتصال

```bash
# اختبار البوت
curl -X POST "https://api.telegram.org/bot<TOKEN>/getMe"

# اختبار الخادم
curl http://your-domain.com/health
```

### 2. اختبار البوت

1. اذهب إلى بوتك على تليجرام
2. أرسل `/start`
3. تأكد من استلام رسالة الترحيب
4. اختبر الأوامر الأخرى

### 3. مراقبة الأداء

```bash
# فحص استخدام الموارد
htop

# فحص استخدام الذاكرة
free -h

# فحص استخدام القرص
df -h
```

## 🔄 النشر المستمر

### 1. إعداد GitHub Actions

```yaml
# .github/workflows/deploy.yml
name: Deploy to Production

on:
  push:
    branches: [ main ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    
    - name: Deploy to VPS
      uses: appleboy/ssh-action@v0.1.4
      with:
        host: ${{ secrets.HOST }}
        username: ${{ secrets.USERNAME }}
        key: ${{ secrets.KEY }}
        script: |
          cd yemen-net-bot
          git pull origin main
          source venv/bin/activate
          pip install -r requirements.txt
          sudo systemctl restart yemen-net-bot
```

### 2. إعداد Render Auto-Deploy

1. في Render، تأكد من تفعيل "Auto-Deploy"
2. كل push إلى main سيؤدي إلى نشر تلقائي
3. يمكنك تعطيل النشر التلقائي عند الحاجة

## 📞 الدعم

إذا واجهت مشاكل في النشر:

- 📧 **البريد الإلكتروني**: support@yemen-net.com
- 💬 **تليجرام**: @YemenNetSupport
- 🐛 **GitHub Issues**: للإبلاغ عن المشاكل
- 📚 **الوثائق**: راجع [دليل استكشاف الأخطاء](troubleshooting.md)

---

**🎉 تهانينا! لقد نشرت بوت يمن نت بنجاح!**

> 💡 **نصيحة**: استخدم `make deploy` للنشر السريع!