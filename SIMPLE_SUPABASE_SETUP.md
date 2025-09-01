# 🚀 دليل إعداد Supabase المبسط

## 🎯 المشكلة:
الجداول لم تظهر في Supabase لأنها لم يتم إنشاؤها بعد.

## ✅ **الحل البسيط:**

### الخطوة 1: اذهب إلى Supabase
1. افتح الرابط: https://supabase.com/dashboard/project/poxdecozxjnzbmumvqzx
2. اضغط على **"SQL Editor"** في القائمة الجانبية

### الخطوة 2: إنشاء الجداول
انسخ والصق هذا الكود في SQL Editor واضغط **"Run"**:

```sql
-- إنشاء جدول المستخدمين
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone VARCHAR(20) UNIQUE NOT NULL,
    role VARCHAR(20) DEFAULT 'customer',
    balance DECIMAL(15,2) DEFAULT 0.00,
    wallet_number VARCHAR(20) UNIQUE,
    is_active BOOLEAN DEFAULT FALSE,
    total_referrals INTEGER DEFAULT 0,
    total_purchases INTEGER DEFAULT 0,
    total_spent DECIMAL(15,2) DEFAULT 0.00,
    invite_code VARCHAR(50) UNIQUE,
    referred_by INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول الشبكات
CREATE TABLE networks (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    description TEXT,
    city VARCHAR(100),
    location VARCHAR(255),
    network_code VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول البطاقات
CREATE TABLE network_cards (
    id SERIAL PRIMARY KEY,
    network_id INTEGER NOT NULL,
    card_code VARCHAR(255) NOT NULL,
    card_value DECIMAL(10,2) NOT NULL,
    is_sold BOOLEAN DEFAULT FALSE,
    sold_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول المعاملات
CREATE TABLE transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user INTEGER NOT NULL,
    to_user INTEGER NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول معاملات المحفظة
CREATE TABLE wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    balance_before DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    reference_id VARCHAR(100),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول الكوبونات
CREATE TABLE coupons (
    id SERIAL PRIMARY KEY,
    coupon_code VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    is_used BOOLEAN DEFAULT FALSE,
    used_by INTEGER,
    used_at TIMESTAMP,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    description TEXT
);

-- إنشاء جدول دليل الحسابات
CREATE TABLE chart_of_accounts (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(20) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- إنشاء جدول دفتر الأستاذ
CREATE TABLE general_ledger (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL,
    debit_amount DECIMAL(15,2) DEFAULT 0.00,
    credit_amount DECIMAL(15,2) DEFAULT 0.00,
    description TEXT,
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'YER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER
);

-- إنشاء الفهارس الأساسية
CREATE INDEX idx_users_telegram_id ON users(telegram_id);
CREATE INDEX idx_users_phone ON users(phone);
CREATE INDEX idx_transactions_from_user ON transactions(from_user);
CREATE INDEX idx_transactions_to_user ON transactions(to_user);
CREATE INDEX idx_network_cards_network_id ON network_cards(network_id);
CREATE INDEX idx_wallet_transactions_user_id ON wallet_transactions(user_id);

-- رسالة نجاح
SELECT 'تم إنشاء جميع الجداول بنجاح!' as message;
```

### الخطوة 3: التحقق من النجاح
بعد تنفيذ السكريبت، يجب أن ترى:
- ✅ رسالة "تم إنشاء جميع الجداول بنجاح!"
- ✅ الجداول تظهر في قسم "Table Editor"

### الخطوة 4: استيراد البيانات
```bash
cd sqlite_export
python3 import_to_supabase.py
```

---

## 🔧 **إذا لم يعمل:**

### البديل 1: إنشاء الجداول من Table Editor
1. اذهب إلى **"Table Editor"**
2. اضغط **"New table"**
3. أنشئ جدول `users` مع الأعمدة:
   - `id` (int8, primary key, auto-increment)
   - `telegram_id` (int8, unique)
   - `full_name` (text)
   - `phone` (text, unique)
   - `role` (text, default: 'customer')
   - `balance` (numeric, default: 0)
   - `is_active` (bool, default: false)

### البديل 2: استخدام Migration
1. اذهب إلى **"Database"** → **"Migrations"**
2. اضغط **"New migration"**
3. الصق محتوى SQL
4. اضغط **"Run migration"**

---

## 📞 **إذا احتجت مساعدة:**
- تأكد من أنك في المشروع الصحيح: `poxdecozxjnzbmumvqzx`
- تأكد من وجود صلاحيات الكتابة
- جرب إنشاء جدول واحد أولاً للاختبار