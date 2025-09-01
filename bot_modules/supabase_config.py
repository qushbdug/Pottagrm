#!/usr/bin/env python3
"""
Supabase Configuration - إعدادات Supabase
تكوين الاتصال مع قاعدة بيانات Supabase
"""

import os
from supabase import create_client, Client

# Supabase Configuration
SUPABASE_URL = "https://poxdecozxjnzbmumvqzx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InBveGRlY296eGpuemJtdW12cXp4Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTY2ODIzNDIsImV4cCI6MjA3MjI1ODM0Mn0.OpoVMldNCBqIkhSSvic29LlSrhfmOIqt7NBp5v27CUk"

# Database connection settings
DATABASE_URL = f"postgresql://postgres:[YOUR_PASSWORD]@db.poxdecozxjnzbmumvqzx.supabase.co:5432/postgres"

# Create Supabase client
def get_supabase_client() -> Client:
    """إنشاء عميل Supabase"""
    return create_client(SUPABASE_URL, SUPABASE_KEY)

# PostgreSQL connection for direct SQL operations
def get_postgres_connection_string():
    """الحصول على نص الاتصال بـ PostgreSQL"""
    # سنحتاج كلمة مرور قاعدة البيانات من Supabase
    # يمكن الحصول عليها من Settings -> Database في لوحة تحكم Supabase
    return DATABASE_URL