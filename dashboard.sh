#!/bin/bash

# Bot Monitoring Dashboard
# لوحة معلومات مراقبة البوت

while true; do
    clear
    echo "╔═══════════════════════════════════════════════════════════════╗"
    echo "║             🤖 لوحة مراقبة Yemen Net Bot 🤖                   ║"
    echo "║                  $(date '+%Y-%m-%d %H:%M:%S')                      ║"
    echo "╚═══════════════════════════════════════════════════════════════╝"
    echo ""
    
    # حالة البوت
    if pgrep -f "python3.*main.py" > /dev/null; then
        BOT_PID=$(pgrep -f "python3.*main.py")
        BOT_MEM=$(ps aux | grep -E "python3.*main.py" | grep -v grep | awk '{print $4}')
        BOT_CPU=$(ps aux | grep -E "python3.*main.py" | grep -v grep | awk '{print $3}')
        echo "┌─────────────────────────────────────────────────────────────┐"
        echo "│ 🟢 حالة البوت: يعمل                                        │"
        echo "│ 🆔 معرف العملية: $BOT_PID                                  │"
        echo "│ 💾 استخدام الذاكرة: ${BOT_MEM}%                           │"
        echo "│ 🖥️  استخدام المعالج: ${BOT_CPU}%                          │"
        echo "└─────────────────────────────────────────────────────────────┘"
    else
        echo "┌─────────────────────────────────────────────────────────────┐"
        echo "│ 🔴 حالة البوت: متوقف!                                      │"
        echo "└─────────────────────────────────────────────────────────────┘"
    fi
    echo ""
    
    # إحصائيات السجل
    if [ -f /workspace/bot.log ]; then
        LOG_SIZE=$(ls -lh /workspace/bot.log | awk '{print $5}')
        LOG_LINES=$(wc -l /workspace/bot.log | awk '{print $1}')
        ERROR_COUNT=$(grep -c "ERROR" /workspace/bot.log 2>/dev/null || echo 0)
        WARNING_COUNT=$(grep -c "WARNING" /workspace/bot.log 2>/dev/null || echo 0)
        
        echo "┌─────────────────────────────────────────────────────────────┐"
        echo "│ 📊 إحصائيات السجل                                          │"
        echo "├─────────────────────────────────────────────────────────────┤"
        echo "│ 📁 حجم الملف: $LOG_SIZE                                    │"
        echo "│ 📝 عدد الأسطر: $LOG_LINES                                  │"
        echo "│ ❌ الأخطاء: $ERROR_COUNT                                    │"
        echo "│ ⚠️  التحذيرات: $WARNING_COUNT                               │"
        echo "└─────────────────────────────────────────────────────────────┘"
    fi
    echo ""
    
    # آخر الأحداث
    echo "┌─────────────────────────────────────────────────────────────┐"
    echo "│ 📜 آخر 5 أحداث                                             │"
    echo "├─────────────────────────────────────────────────────────────┤"
    tail -n 5 /workspace/bot.log | while IFS= read -r line; do
        # اقتطاع السطر إذا كان طويلاً
        if [ ${#line} -gt 60 ]; then
            line="${line:0:57}..."
        fi
        printf "│ %-60s│\n" "$line"
    done
    echo "└─────────────────────────────────────────────────────────────┘"
    echo ""
    
    # آخر الأخطاء
    LAST_ERROR=$(tail -n 100 /workspace/bot.log | grep "ERROR" | tail -n 1)
    if [ ! -z "$LAST_ERROR" ]; then
        echo "┌─────────────────────────────────────────────────────────────┐"
        echo "│ 🔴 آخر خطأ                                                 │"
        echo "├─────────────────────────────────────────────────────────────┤"
        if [ ${#LAST_ERROR} -gt 60 ]; then
            LAST_ERROR="${LAST_ERROR:0:57}..."
        fi
        printf "│ %-60s│\n" "$LAST_ERROR"
        echo "└─────────────────────────────────────────────────────────────┘"
    fi
    echo ""
    
    # حالة المراقبة
    if pgrep -f "monitor_bot.sh" > /dev/null; then
        MONITOR_TIME=$(ps aux | grep -E "monitor_bot.sh" | grep -v grep | awk '{print $9}')
        echo "┌─────────────────────────────────────────────────────────────┐"
        echo "│ 🔍 المراقبة: نشطة منذ $MONITOR_TIME                        │"
        echo "└─────────────────────────────────────────────────────────────┘"
    fi
    
    echo ""
    echo "🔄 التحديث كل 5 ثوان | Ctrl+C للإيقاف"
    
    sleep 5
done