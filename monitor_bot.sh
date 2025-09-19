#!/bin/bash

# Bot Monitoring Script
# يراقب البوت لمدة ساعتين ويسجل التقارير

echo "🔍 بدء مراقبة البوت - $(date '+%Y-%m-%d %H:%M:%S')"
echo "⏱️ مدة المراقبة: ساعتين"
echo "📁 ملف السجل: /workspace/bot.log"
echo "📊 ملف التقرير: /workspace/monitoring_report.txt"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# إنشاء ملف التقرير
REPORT_FILE="/workspace/monitoring_report.txt"
echo "تقرير مراقبة البوت - $(date '+%Y-%m-%d %H:%M:%S')" > $REPORT_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> $REPORT_FILE

# متغيرات للإحصائيات
ERROR_COUNT=0
WARNING_COUNT=0
TRANSACTION_COUNT=0
START_TIME=$(date +%s)
END_TIME=$((START_TIME + 7200))  # ساعتين = 7200 ثانية

# دالة لتحليل السجلات
analyze_logs() {
    local time_marker=$(date '+%Y-%m-%d %H:%M:%S')
    local current_errors=$(grep -c "ERROR" /workspace/bot.log 2>/dev/null || echo 0)
    local current_warnings=$(grep -c "WARNING" /workspace/bot.log 2>/dev/null || echo 0)
    local current_transactions=$(grep -c "transaction\|معاملة" /workspace/bot.log 2>/dev/null || echo 0)
    
    echo "" >> $REPORT_FILE
    echo "📊 تقرير دوري - $time_marker" >> $REPORT_FILE
    echo "❌ الأخطاء: $current_errors" >> $REPORT_FILE
    echo "⚠️ التحذيرات: $current_warnings" >> $REPORT_FILE
    echo "💰 المعاملات: $current_transactions" >> $REPORT_FILE
    
    # التحقق من حالة البوت
    if pgrep -f "python3.*main.py" > /dev/null; then
        echo "✅ حالة البوت: يعمل" >> $REPORT_FILE
        echo "✅ البوت يعمل بشكل طبيعي"
    else
        echo "❌ حالة البوت: متوقف!" >> $REPORT_FILE
        echo "❌ تحذير: البوت متوقف! محاولة إعادة التشغيل..."
        cd /workspace && python3 -u main.py 2>&1 &
        sleep 5
    fi
    
    # عرض آخر الأخطاء إن وجدت
    local recent_errors=$(tail -n 1000 /workspace/bot.log | grep "ERROR" | tail -n 5)
    if [ ! -z "$recent_errors" ]; then
        echo "" >> $REPORT_FILE
        echo "🔴 آخر الأخطاء:" >> $REPORT_FILE
        echo "$recent_errors" >> $REPORT_FILE
    fi
}

# مراقبة مستمرة
echo ""
echo "🚀 بدء المراقبة المستمرة..."

while [ $(date +%s) -lt $END_TIME ]; do
    # تحليل كل 5 دقائق
    analyze_logs
    
    # عرض الوقت المتبقي
    CURRENT_TIME=$(date +%s)
    REMAINING=$((END_TIME - CURRENT_TIME))
    REMAINING_MINUTES=$((REMAINING / 60))
    REMAINING_SECONDS=$((REMAINING % 60))
    
    echo ""
    echo "⏳ الوقت المتبقي: ${REMAINING_MINUTES} دقيقة و ${REMAINING_SECONDS} ثانية"
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    # الانتظار 5 دقائق أو حتى انتهاء الوقت
    if [ $REMAINING -gt 300 ]; then
        sleep 300  # 5 دقائق
    else
        sleep $REMAINING
    fi
done

# التقرير النهائي
echo "" >> $REPORT_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> $REPORT_FILE
echo "📊 التقرير النهائي - $(date '+%Y-%m-%d %H:%M:%S')" >> $REPORT_FILE

# إحصائيات نهائية
FINAL_ERRORS=$(grep -c "ERROR" /workspace/bot.log 2>/dev/null || echo 0)
FINAL_WARNINGS=$(grep -c "WARNING" /workspace/bot.log 2>/dev/null || echo 0)
FINAL_TRANSACTIONS=$(grep -c "transaction\|معاملة" /workspace/bot.log 2>/dev/null || echo 0)

echo "❌ إجمالي الأخطاء: $FINAL_ERRORS" >> $REPORT_FILE
echo "⚠️ إجمالي التحذيرات: $FINAL_WARNINGS" >> $REPORT_FILE
echo "💰 إجمالي المعاملات: $FINAL_TRANSACTIONS" >> $REPORT_FILE

# حفظ آخر 100 سطر من السجل
echo "" >> $REPORT_FILE
echo "📜 آخر 100 سطر من السجل:" >> $REPORT_FILE
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" >> $REPORT_FILE
tail -n 100 /workspace/bot.log >> $REPORT_FILE

echo ""
echo "✅ انتهت مدة المراقبة!"
echo "📊 تم حفظ التقرير في: $REPORT_FILE"
echo "🔍 يمكنك قراءة التقرير باستخدام: cat $REPORT_FILE"