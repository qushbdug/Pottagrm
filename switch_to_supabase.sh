#!/bin/bash
# Switch to Supabase - التبديل إلى Supabase
# سكريبت سريع لتفعيل Supabase بدلاً من SQLite

echo "🔄 التبديل إلى Supabase..."

# إيقاف البوت الحالي
echo "⏹️ إيقاف البوت الحالي..."
pkill -f "python3 main.py"
sleep 3

# تفعيل Supabase
echo "🔧 تفعيل Supabase..."
export USE_SUPABASE=true

# إنشاء ملف بيئة
echo "USE_SUPABASE=true" > .env
echo "DATABASE_TYPE=supabase" >> .env

echo "✅ تم تفعيل Supabase"

# تشغيل البوت مع Supabase
echo "🚀 تشغيل البوت مع Supabase..."
python3 main.py &

sleep 5

# فحص الحالة
if ps aux | grep -q "python3 main.py"; then
    echo "✅ البوت يعمل مع Supabase بنجاح!"
    echo "📊 فحص آخر السجلات..."
    tail -10 bot.log | grep -E "(Supabase|PostgreSQL|database)" || echo "لا توجد رسائل خاصة بقاعدة البيانات"
else
    echo "❌ فشل تشغيل البوت مع Supabase"
    echo "🔄 العودة إلى SQLite..."
    unset USE_SUPABASE
    echo "USE_SUPABASE=false" > .env
    python3 main.py &
fi

echo "🎉 انتهى التبديل!"