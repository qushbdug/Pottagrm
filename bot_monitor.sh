#!/bin/bash

# Yemen Net Bot Monitor Script
# مراقب البوت اليمني نت

echo "🤖 مراقب بوت اليمن نت"
echo "======================="
echo "⏰ بدء المراقبة: $(date)"
echo ""

# دالة لطباعة الوقت المتبقي
show_remaining_time() {
    local start_time="$1"
    local duration=7200  # ساعتين بالثواني
    local current_time=$(date +%s)
    local elapsed=$((current_time - start_time))
    local remaining=$((duration - elapsed))
    
    if [ $remaining -gt 0 ]; then
        local hours=$((remaining / 3600))
        local minutes=$(((remaining % 3600) / 60))
        local seconds=$((remaining % 60))
        printf "⏳ الوقت المتبقي: %02d:%02d:%02d\n" $hours $minutes $seconds
    else
        echo "⏰ انتهى وقت التشغيل المحدد"
    fi
}

# التحقق من حالة البوت
check_bot_status() {
    if ps aux | grep -q "timeout.*python main.py" | grep -v grep; then
        echo "✅ البوت يعمل بشكل طبيعي"
        
        # عرض آخر الأحداث
        if [ -f "bot_runtime.log" ]; then
            echo ""
            echo "📋 آخر 3 أحداث:"
            echo "---------------"
            tail -3 bot_runtime.log | while read line; do
                echo "  $line"
            done
        fi
        
        if [ -f "bot.log" ]; then
            echo ""
            echo "📝 آخر حدث في السجل الرسمي:"
            echo "----------------------------"
            tail -1 bot.log | while read line; do
                echo "  $line"
            done
        fi
        
        return 0
    else
        echo "❌ البوت متوقف!"
        return 1
    fi
}

# بدء المراقبة
start_time=$(date +%s)

while true; do
    clear
    echo "🤖 مراقب بوت اليمن نت"
    echo "======================="
    echo "⏰ وقت الفحص: $(date)"
    echo ""
    
    show_remaining_time $start_time
    echo ""
    
    check_bot_status
    
    echo ""
    echo "🔄 المراقبة التالية خلال 30 ثانية..."
    echo "Press Ctrl+C to stop monitoring"
    
    sleep 30
done