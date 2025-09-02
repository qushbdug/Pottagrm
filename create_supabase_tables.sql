-- إنشاء جداول قاعدة البيانات في Supabase
-- يجب تشغيل هذا السكريبت في SQL Editor في لوحة تحكم Supabase

-- جدول المستخدمين
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    telegram_id BIGINT UNIQUE NOT NULL,
    full_name VARCHAR(255) NOT NULL CHECK (LENGTH(full_name) >= 2),
    phone VARCHAR(20) UNIQUE NOT NULL CHECK (LENGTH(phone) >= 9),
    role VARCHAR(20) NOT NULL DEFAULT 'customer' 
        CHECK (role IN ('customer', 'supplier', 'agent', 'admin', 'super_admin')),
    balance DECIMAL(15,2) DEFAULT 0.00 CHECK (balance >= 0),
    invite_code VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT FALSE,
    bank_account VARCHAR(100),
    total_referrals INTEGER DEFAULT 0 CHECK (total_referrals >= 0),
    total_purchases INTEGER DEFAULT 0 CHECK (total_purchases >= 0),
    total_spent DECIMAL(15,2) DEFAULT 0.00 CHECK (total_spent >= 0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_activity TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    referred_by INTEGER REFERENCES users(id) ON DELETE SET NULL,
    wallet_number VARCHAR(20) UNIQUE,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول الشبكات
CREATE TABLE IF NOT EXISTS networks (
    id SERIAL PRIMARY KEY,
    supplier_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    provider VARCHAR(255) NOT NULL,
    description TEXT,
    logo_url TEXT,
    city VARCHAR(100),
    location VARCHAR(255),
    network_code VARCHAR(50) UNIQUE,
    is_active BOOLEAN DEFAULT TRUE,
    is_approved BOOLEAN DEFAULT FALSE,
    created_by INTEGER REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    approved_at TIMESTAMP,
    approved_by INTEGER REFERENCES users(id)
);

-- جدول بطاقات الشبكة
CREATE TABLE IF NOT EXISTS network_cards (
    id SERIAL PRIMARY KEY,
    network_id INTEGER NOT NULL REFERENCES networks(id) ON DELETE CASCADE,
    card_code VARCHAR(255) NOT NULL,
    card_value DECIMAL(10,2) NOT NULL CHECK (card_value > 0),
    is_sold BOOLEAN DEFAULT FALSE,
    sold_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    batch_id VARCHAR(100),
    serial_number VARCHAR(100)
);

-- جدول المعاملات
CREATE TABLE IF NOT EXISTS transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    from_user INTEGER NOT NULL REFERENCES users(id),
    to_user INTEGER NOT NULL REFERENCES users(id),
    amount DECIMAL(15,2) NOT NULL CHECK (amount > 0),
    type VARCHAR(50) NOT NULL,
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    reference_id VARCHAR(100),
    metadata JSONB,
    CHECK (from_user != to_user OR type != 'transfer')
);

-- جدول معاملات المحفظة
CREATE TABLE IF NOT EXISTS wallet_transactions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_type VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    balance_before DECIMAL(15,2) NOT NULL,
    balance_after DECIMAL(15,2) NOT NULL,
    reference_id VARCHAR(100),
    description TEXT,
    status VARCHAR(20) DEFAULT 'completed',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB
);

-- جدول الكوبونات
CREATE TABLE IF NOT EXISTS coupons (
    id SERIAL PRIMARY KEY,
    coupon_code VARCHAR(50) UNIQUE NOT NULL,
    amount DECIMAL(10,2) NOT NULL CHECK (amount > 0),
    is_used BOOLEAN DEFAULT FALSE,
    used_by INTEGER REFERENCES users(id),
    used_at TIMESTAMP,
    created_by INTEGER NOT NULL REFERENCES users(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP,
    description TEXT,
    usage_limit INTEGER DEFAULT 1,
    usage_count INTEGER DEFAULT 0
);

-- جدول دليل الحسابات
CREATE TABLE IF NOT EXISTS chart_of_accounts (
    id SERIAL PRIMARY KEY,
    account_code VARCHAR(20) UNIQUE NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    account_type VARCHAR(50) NOT NULL 
        CHECK (account_type IN ('asset', 'liability', 'equity', 'revenue', 'expense')),
    parent_account INTEGER REFERENCES chart_of_accounts(id),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- جدول دفتر الأستاذ العام
CREATE TABLE IF NOT EXISTS general_ledger (
    id SERIAL PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES chart_of_accounts(id),
    debit_amount DECIMAL(15,2) DEFAULT 0.00,
    credit_amount DECIMAL(15,2) DEFAULT 0.00,
    description TEXT,
    reference_type VARCHAR(50),
    reference_id VARCHAR(100),
    currency VARCHAR(3) DEFAULT 'YER',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER REFERENCES users(id),
    CHECK ((debit_amount > 0 AND credit_amount = 0) OR (credit_amount > 0 AND debit_amount = 0))
);

-- إنشاء الفهارس المحسنة
CREATE INDEX IF NOT EXISTS idx_users_telegram_id ON users(telegram_id);
CREATE INDEX IF NOT EXISTS idx_users_phone ON users(phone);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_balance ON users(balance);
CREATE INDEX IF NOT EXISTS idx_users_wallet_number ON users(wallet_number);

CREATE INDEX IF NOT EXISTS idx_networks_supplier ON networks(supplier_id);
CREATE INDEX IF NOT EXISTS idx_networks_active ON networks(is_active, is_approved);

CREATE INDEX IF NOT EXISTS idx_cards_network ON network_cards(network_id);
CREATE INDEX IF NOT EXISTS idx_cards_sold ON network_cards(is_sold);
CREATE INDEX IF NOT EXISTS idx_cards_value ON network_cards(card_value);

CREATE INDEX IF NOT EXISTS idx_transactions_from_user ON transactions(from_user);
CREATE INDEX IF NOT EXISTS idx_transactions_to_user ON transactions(to_user);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(type);
CREATE INDEX IF NOT EXISTS idx_transactions_created_at ON transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_wallet_trans_user ON wallet_transactions(user_id);
CREATE INDEX IF NOT EXISTS idx_wallet_trans_type ON wallet_transactions(transaction_type);
CREATE INDEX IF NOT EXISTS idx_wallet_trans_created_at ON wallet_transactions(created_at);

CREATE INDEX IF NOT EXISTS idx_coupons_code ON coupons(coupon_code);
CREATE INDEX IF NOT EXISTS idx_coupons_used ON coupons(is_used);

CREATE INDEX IF NOT EXISTS idx_ledger_account ON general_ledger(account_id);
CREATE INDEX IF NOT EXISTS idx_ledger_date ON general_ledger(created_at);

-- إنشاء RLS (Row Level Security) policies
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE wallet_transactions ENABLE ROW LEVEL SECURITY;

-- Policy للمستخدمين - يمكن للمستخدم رؤية بياناته فقط
CREATE POLICY "Users can view own data" ON users
    FOR SELECT USING (auth.uid()::text = telegram_id::text);

-- Policy للمعاملات - يمكن للمستخدم رؤية معاملاته فقط
CREATE POLICY "Users can view own transactions" ON transactions
    FOR SELECT USING (
        auth.uid()::text IN (
            SELECT telegram_id::text FROM users WHERE id = from_user OR id = to_user
        )
    );

-- Policy لمعاملات المحفظة
CREATE POLICY "Users can view own wallet transactions" ON wallet_transactions
    FOR SELECT USING (
        auth.uid()::text IN (
            SELECT telegram_id::text FROM users WHERE id = user_id
        )
    );

-- إنشاء دالة لتحديث updated_at تلقائياً
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- تطبيق الدالة على الجداول المناسبة
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_networks_updated_at BEFORE UPDATE ON networks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_transactions_updated_at BEFORE UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- رسالة نجاح
SELECT 'تم إنشاء جميع الجداول والفهارس بنجاح في Supabase!' as message;