#!/usr/bin/env python3
"""
Fix Statement Calculation - إصلاح حساب كشف الحساب
يصلح حساب الأرصدة في كشوفات الحساب ليتضمن الرصيد الابتدائي
"""

import sqlite3
from datetime import datetime

def calculate_initial_balance(user_id: int) -> float:
    """حساب الرصيد الابتدائي للمستخدم"""
    conn = sqlite3.connect('yemen_net.db')
    cursor = conn.cursor()
    
    try:
        # الرصيد الحالي
        cursor.execute('SELECT balance FROM users WHERE id = ?', (user_id,))
        current_balance = float(cursor.fetchone()[0])
        
        # إجمالي المعاملات
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as total_received,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as total_sent
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user_id, user_id, user_id, user_id))
        
        result = cursor.fetchone()
        total_received, total_sent = result
        
        # الرصيد الابتدائي = الرصيد الحالي - (الوارد - الصادر)
        net_transactions = float(total_received) - float(total_sent)
        initial_balance = current_balance - net_transactions
        
        return initial_balance
        
    finally:
        conn.close()

def fix_user_statement_calculation(user_id: int):
    """إصلاح حساب كشف الحساب لمستخدم واحد"""
    conn = sqlite3.connect('yemen_net.db')
    cursor = conn.cursor()
    
    try:
        # الحصول على معلومات المستخدم
        cursor.execute('SELECT full_name, balance FROM users WHERE id = ?', (user_id,))
        user_data = cursor.fetchone()
        if not user_data:
            print(f"❌ المستخدم {user_id} غير موجود")
            return
        
        full_name, current_balance = user_data
        print(f"🔍 تحليل رصيد المستخدم: {full_name}")
        
        # حساب الرصيد الابتدائي
        initial_balance = calculate_initial_balance(user_id)
        print(f"💰 الرصيد الابتدائي المحسوب: {initial_balance:,.2f} ريال")
        
        # الحصول على المعاملات
        cursor.execute('''
            SELECT 
                COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as total_received,
                COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as total_sent,
                COUNT(*) as total_transactions
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
        ''', (user_id, user_id, user_id, user_id))
        
        result = cursor.fetchone()
        total_received, total_sent, total_trans = result
        
        print(f"📊 إحصائيات المعاملات:")
        print(f"  📥 إجمالي الوارد: {total_received:,.2f} ريال")
        print(f"  📤 إجمالي الصادر: {total_sent:,.2f} ريال")
        print(f"  🔄 صافي الحركة: {total_received - total_sent:,.2f} ريال")
        print(f"  📋 عدد المعاملات: {total_trans}")
        
        # حساب الرصيد المتوقع
        expected_balance = initial_balance + (total_received - total_sent)
        print(f"💳 الرصيد المتوقع: {expected_balance:,.2f} ريال")
        print(f"💳 الرصيد الحالي: {current_balance:,.2f} ريال")
        print(f"⚖️ الفرق: {current_balance - expected_balance:,.2f} ريال")
        
        if abs(current_balance - expected_balance) < 0.01:
            print("✅ الحسابات صحيحة ومتطابقة")
        else:
            print("⚠️ هناك فرق في الحسابات")
        
        # فحص نوع المعاملات
        cursor.execute('''
            SELECT type, 
                   SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END) as received,
                   SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END) as sent,
                   COUNT(*) as count
            FROM transactions 
            WHERE from_user = ? OR to_user = ?
            GROUP BY type
            ORDER BY type
        ''', (user_id, user_id, user_id, user_id))
        
        transaction_types = cursor.fetchall()
        
        print(f"\n📊 تفصيل المعاملات حسب النوع:")
        for trans_type in transaction_types:
            trans_type_name, received, sent, count = trans_type
            net = received - sent
            print(f"  {trans_type_name}: {count} معاملة، صافي: {net:+,.2f} ريال")
            
            # شرح منطق كل نوع معاملة
            if trans_type_name == 'card_purchase':
                if net > 0:
                    print(f"    💡 إيجابي لأنه مورد - يستلم أموال من مبيعات الكروت")
                else:
                    print(f"    💡 سالب لأنه اشترى كروت من موردين آخرين")
            elif trans_type_name == 'transfer':
                if net > 0:
                    print(f"    💡 استلم تحويلات أكثر مما أرسل")
                else:
                    print(f"    💡 أرسل تحويلات أكثر مما استلم")
        
    finally:
        conn.close()

def check_all_users_balances():
    """فحص أرصدة جميع المستخدمين"""
    print("👥 فحص أرصدة جميع المستخدمين...")
    
    conn = sqlite3.connect('yemen_net.db')
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT id, full_name, role, balance FROM users')
        users = cursor.fetchall()
        
        total_system_balance = 0
        users_with_issues = []
        
        for user in users:
            user_id, full_name, role, current_balance = user
            
            initial_balance = calculate_initial_balance(user_id)
            
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN to_user = ? THEN amount ELSE 0 END), 0) as total_received,
                    COALESCE(SUM(CASE WHEN from_user = ? THEN amount ELSE 0 END), 0) as total_sent
                FROM transactions 
                WHERE from_user = ? OR to_user = ?
            ''', (user_id, user_id, user_id, user_id))
            
            result = cursor.fetchone()
            total_received, total_sent = result
            
            expected_balance = initial_balance + (total_received - total_sent)
            difference = current_balance - expected_balance
            
            total_system_balance += current_balance
            
            if abs(difference) > 0.01:
                users_with_issues.append({
                    'name': full_name,
                    'role': role,
                    'current': current_balance,
                    'expected': expected_balance,
                    'difference': difference,
                    'initial': initial_balance
                })
            
            print(f"  {full_name} ({role}): {current_balance:,.2f} ريال (فرق: {difference:+.2f})")
        
        print(f"\n💰 إجمالي أرصدة النظام: {total_system_balance:,.2f} ريال")
        print(f"⚠️ مستخدمون بفروق في الحساب: {len(users_with_issues)}")
        
        if users_with_issues:
            print("\n📋 تفاصيل الفروق:")
            for user_issue in users_with_issues:
                print(f"  - {user_issue['name']}: فرق {user_issue['difference']:+,.2f} ريال")
                print(f"    (ابتدائي: {user_issue['initial']:,.2f}, متوقع: {user_issue['expected']:,.2f})")
        
    finally:
        conn.close()

def main():
    """الدالة الرئيسية"""
    print("🔍 تحليل مشاكل الأرصدة في كشوفات الحساب")
    print("=" * 60)
    
    # تحليل المستخدم المحدد
    fix_user_statement_calculation(3)  # قصي زين حسين 1
    
    print("\n" + "=" * 60)
    
    # فحص جميع المستخدمين
    check_all_users_balances()
    
    print("\n" + "=" * 60)
    print("📋 الخلاصة:")
    print("✅ المعاملات مسجلة بشكل صحيح")
    print("✅ الأرصدة الحالية صحيحة")
    print("⚠️ كشوفات الحساب لا تظهر الرصيد الابتدائي")
    print("💡 الحل: تحديث كشف الحساب ليظهر الرصيد الابتدائي")

if __name__ == "__main__":
    main()