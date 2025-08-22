# Yemen Net Bot v2.0 🚀

بوت تيليجرام محسن ومتطور لإدارة البطاقات والمدفوعات مع هيكل برمجي متقدم وإدارة أخطاء محسنة.

## ✨ الميزات الرئيسية

### 🔧 الهيكل المحسن
- **هيكل معماري متقدم**: تقسيم واضح للمسؤوليات مع فصل الخدمات
- **إدارة قاعدة البيانات المحسنة**: تجميع الاتصالات وتجميع الاستعلامات
- **نظام تخزين مؤقت ذكي**: تحسين الأداء مع إدارة الذاكرة
- **مدير معدل الطلبات**: منع الاستخدام المفرط وحماية النظام

### 🛡️ الأمان والاستقرار
- **معالجة أخطاء متقدمة**: استثناءات مخصصة ومعالجة شاملة للأخطاء
- **نظام إشعارات متعدد القنوات**: تيليجرام، إيميل، رسائل نصية
- **مراقبة صحة النظام**: فحص مستمر لقاعدة البيانات والخدمات
- **نسخ احتياطية تلقائية**: حماية البيانات مع استرداد سريع

### 📊 المراقبة والأداء
- **إحصائيات شاملة**: تتبع الأداء واستخدام الموارد
- **سجلات مفصلة**: تسجيل شامل لجميع العمليات
- **مراقبة الأداء**: تحليل سرعة الاستجابة واستخدام الذاكرة
- **تنبيهات ذكية**: إشعارات فورية للمشاكل

## 🏗️ هيكل المشروع

```
bot_v2/
├── core/                   # الوظائف الأساسية
│   ├── __init__.py
│   ├── config.py          # إدارة التكوين
│   ├── exceptions.py      # الاستثناءات المخصصة
│   └── bot_core.py        # الفئة الأساسية للبوت
├── services/              # الخدمات
│   ├── __init__.py
│   ├── database_manager.py    # إدارة قاعدة البيانات
│   ├── rate_limiter.py        # مدير معدل الطلبات
│   ├── cache_manager.py       # مدير التخزين المؤقت
│   └── notification_manager.py # مدير الإشعارات
├── handlers/              # معالجات الرسائل
│   ├── __init__.py
│   ├── user_handlers.py   # معالجات المستخدمين
│   ├── admin_handlers.py  # معالجات المديرين
│   └── payment_handlers.py # معالجات المدفوعات
├── utils/                 # الأدوات المساعدة
│   ├── __init__.py
│   ├── validators.py      # التحقق من صحة البيانات
│   ├── helpers.py         # وظائف مساعدة
│   └── decorators.py      # الديكورات
├── models/                # نماذج البيانات
│   ├── __init__.py
│   ├── user.py           # نموذج المستخدم
│   ├── transaction.py    # نموذج المعاملة
│   └── card.py          # نموذج البطاقة
├── main.py               # نقطة البداية الرئيسية
├── requirements.txt      # المتطلبات
└── README.md            # هذا الملف
```

## 🚀 التثبيت والتشغيل

### المتطلبات الأساسية
- Python 3.8+
- pip
- قاعدة بيانات SQLite

### خطوات التثبيت

1. **استنساخ المشروع**
```bash
git clone <repository-url>
cd bot_v2
```

2. **إنشاء بيئة افتراضية**
```bash
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# أو
venv\Scripts\activate     # Windows
```

3. **تثبيت المتطلبات**
```bash
pip install -r requirements.txt
```

4. **إعداد التكوين**
```bash
# نسخ ملف التكوين
cp config.example.yaml config.yaml

# تعديل المتغيرات البيئية
export BOT_TOKEN="your_bot_token_here"
export DB_PATH="yemen_net.db"
export ADMIN_USER_IDS="123456789,987654321"
```

5. **تشغيل البوت**
```bash
python main.py
```

## ⚙️ التكوين

### المتغيرات البيئية

| المتغير | الوصف | القيمة الافتراضية |
|---------|--------|-------------------|
| `BOT_TOKEN` | توكن البوت من BotFather | مطلوب |
| `DB_PATH` | مسار قاعدة البيانات | `yemen_net.db` |
| `ADMIN_USER_IDS` | قائمة معرفات المديرين | فارغ |
| `BOT_LOG_LEVEL` | مستوى السجلات | `INFO` |

### ملف التكوين (config.yaml)

```yaml
bot:
  token: "your_bot_token"
  log_level: "INFO"
  log_file: "bot.log"
  rate_limit_per_user: 10
  rate_limit_per_minute: 60

database:
  path: "yemen_net.db"
  max_connections: 10
  timeout: 30.0

payment:
  min_transfer_amount: 1.0
  max_transfer_amount: 10000.0
  transfer_fee_percent: 0.5

notification:
  enable_telegram: true
  enable_email: false
  enable_sms: false
```

## 🔧 الاستخدام

### الأوامر الأساسية

- `/start` - بدء استخدام البوت
- `/help` - عرض المساعدة
- `/status` - عرض حالة الحساب
- `/admin` - لوحة الإدارة (للمديرين)

### الميزات المتاحة

#### 👤 المستخدمون العاديون
- عرض وإدارة المحفظة
- شراء البطاقات
- تحويل الأموال
- عرض سجل المعاملات
- إعدادات الحساب

#### 👑 المديرون
- إدارة المستخدمين
- مراقبة النظام
- التقارير والإحصائيات
- إرسال إشعارات
- إعدادات النظام

#### 🏪 الموردون
- إدارة الشبكات
- رفع البطاقات
- تقارير المبيعات
- إدارة العمولات

## 📊 المراقبة والصيانة

### فحص صحة النظام
```bash
# فحص قاعدة البيانات
python -c "from services.database_manager import db_manager; print(db_manager.health_check())"

# فحص التخزين المؤقت
python -c "from services.cache_manager import cache_manager; print(cache_manager.get_stats())"

# فحص معدل الطلبات
python -c "from services.rate_limiter import rate_limiter; print(rate_limiter.get_system_stats())"
```

### النسخ الاحتياطية
```bash
# نسخ احتياطي لقاعدة البيانات
python -c "from services.database_manager import db_manager; db_manager.backup_database('backup.db')"

# نسخ احتياطي للتخزين المؤقت
python -c "from services.cache_manager import cache_manager; cache_manager.persist_to_disk('cache_backup.json')"
```

### تحسين الأداء
```bash
# تحسين قاعدة البيانات
python -c "from services.database_manager import db_manager; db_manager.optimize_database()"

# تنظيف التخزين المؤقت
python -c "from services.cache_manager import cache_manager; cache_manager.clear()"
```

## 🐛 استكشاف الأخطاء

### المشاكل الشائعة

1. **خطأ في الاتصال بقاعدة البيانات**
   - تأكد من وجود ملف قاعدة البيانات
   - تحقق من الصلاحيات
   - فحص صحة قاعدة البيانات

2. **مشاكل في معدل الطلبات**
   - انتظار انتهاء فترة الحظر
   - إعادة تعيين حدود المستخدم
   - فحص إعدادات معدل الطلبات

3. **مشاكل في الإشعارات**
   - التحقق من إعدادات SMTP
   - فحص معرفات المستخدمين
   - مراجعة سجلات الأخطاء

### السجلات

```bash
# عرض السجلات في الوقت الفعلي
tail -f bot.log

# البحث عن أخطاء
grep "ERROR" bot.log

# البحث عن تحذيرات
grep "WARNING" bot.log
```

## 🔒 الأمان

### ميزات الأمان
- **معدل الطلبات**: منع الهجمات والاستخدام المفرط
- **التحقق من الصلاحيات**: فحص الأدوار والصلاحيات
- **تشفير البيانات**: حماية المعلومات الحساسة
- **مراقبة النشاط**: تتبع الأنشطة المشبوهة

### أفضل الممارسات
- تحديث التوكن بانتظام
- استخدام بيئات افتراضية
- مراقبة السجلات باستمرار
- نسخ احتياطية منتظمة

## 📈 التطوير المستقبلي

### الميزات المخططة
- [ ] واجهة ويب للإدارة
- [ ] دعم العملات المشفرة
- [ ] نظام تقييم المستخدمين
- [ ] تكامل مع خدمات خارجية
- [ ] نظام المكافآت والولاء
- [ ] تحليلات متقدمة

### المساهمة
نرحب بمساهماتكم! يرجى:
1. Fork المشروع
2. إنشاء فرع للميزة الجديدة
3. إجراء التغييرات
4. إرسال Pull Request

## 📞 الدعم

### طرق التواصل
- **GitHub Issues**: للإبلاغ عن الأخطاء
- **Discord**: للمناقشات والدعم
- **Email**: للاستفسارات العامة

### الموارد المفيدة
- [وثائق python-telegram-bot](https://python-telegram-bot.readthedocs.io/)
- [دليل SQLite](https://www.sqlite.org/docs.html)
- [أفضل ممارسات Python](https://docs.python-guide.org/)

## 📄 الترخيص

هذا المشروع مرخص تحت رخصة MIT. راجع ملف `LICENSE` للتفاصيل.

## 🙏 الشكر والتقدير

- فريق python-telegram-bot
- مجتمع Python العربي
- جميع المساهمين والمطورين

---

**ملاحظة**: هذا البوت مصمم للاستخدام التجاري والتعليمي. يرجى الالتزام بقوانين بلدك عند الاستخدام.

**الإصدار**: 2.0.0  
**آخر تحديث**: ديسمبر 2024  
**المطور**: فريق يمن نت