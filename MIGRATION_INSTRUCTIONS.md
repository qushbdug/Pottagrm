
# 📋 تعليمات الهجرة إلى Supabase

## الخطوة 1: إنشاء الجداول في Supabase
1. اذهب إلى https://supabase.com/dashboard/project/poxdecozxjnzbmumvqzx
2. اضغط على "SQL Editor" في القائمة الجانبية
3. انسخ محتوى ملف `create_supabase_tables.sql`
4. الصق المحتوى في SQL Editor
5. اضغط "Run" لتنفيذ السكريبت

## الخطوة 2: استيراد البيانات
1. شغل سكريبت التصدير: `python3 manual_migration.py`
2. شغل سكريبت الاستيراد: `python3 sqlite_export/import_to_supabase.py`

## الخطوة 3: تفعيل Supabase في البوت
1. أضف متغير البيئة: `export USE_SUPABASE=true`
2. أعد تشغيل البوت: `python3 main.py`

## الخطوة 4: التحقق من النجاح
- تحقق من أن البوت يعمل بدون أخطاء
- تحقق من أن البيانات موجودة في Supabase
- اختبر العمليات الأساسية (تسجيل، تحويل، شراء)

## ملاحظات مهمة:
- احتفظ بنسخة احتياطية من SQLite
- اختبر جميع الوظائف بعد الهجرة
- راقب الأداء والاستقرار
