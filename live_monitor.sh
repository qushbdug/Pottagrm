#!/bin/bash

# Live Log Monitoring Script
# يعرض السجلات المباشرة مع تلوين وفلترة

echo "🔴 مراقبة مباشرة لسجلات البوت"
echo "📁 الملف: /workspace/bot.log"
echo "⏰ الوقت: $(date '+%Y-%m-%d %H:%M:%S')"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "🔍 المراقبة النشطة لـ:"
echo "   ❌ ERROR - الأخطاء"
echo "   ⚠️  WARNING - التحذيرات"
echo "   💰 المعاملات والتحويلات"
echo "   👤 تسجيل دخول المستخدمين"
echo "   🎟️ استخدام الكوبونات"
echo ""
echo "للإيقاف: اضغط Ctrl+C"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# دالة لتلوين السطور حسب النوع
colorize_line() {
    while IFS= read -r line; do
        if echo "$line" | grep -q "ERROR"; then
            echo -e "\033[1;31m❌ $line\033[0m"  # أحمر للأخطاء
        elif echo "$line" | grep -q "WARNING"; then
            echo -e "\033[1;33m⚠️  $line\033[0m"  # أصفر للتحذيرات
        elif echo "$line" | grep -qi "transaction\|معاملة\|تحويل"; then
            echo -e "\033[1;32m💰 $line\033[0m"  # أخضر للمعاملات
        elif echo "$line" | grep -qi "login\|دخول\|start"; then
            echo -e "\033[1;36m👤 $line\033[0m"  # سماوي لتسجيل الدخول
        elif echo "$line" | grep -qi "coupon\|كوبون"; then
            echo -e "\033[1;35m🎟️  $line\033[0m"  # بنفسجي للكوبونات
        else
            echo "$line"
        fi
    done
}

# المراقبة المباشرة مع الفلترة والتلوين
tail -f /workspace/bot.log | colorize_line