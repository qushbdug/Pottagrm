#!/usr/bin/env python3
"""
معالجات الميزات المتقدمة - 35 ميزة جديدة
Advanced Features Handlers - 35 New Features
"""

import logging
import sqlite3
import json
import datetime
import secrets
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from bot_modules.config import *
from bot_modules.database import get_db_connection
from bot_modules.utils import get_user

logger = logging.getLogger(__name__)

# ===== ميزات المستخدم العادي =====

async def loyalty_points_handler(update: Update, context: CallbackContext):
    """🎯 نظام النقاط والولاء"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على نقاط المستخدم
        cursor.execute('SELECT * FROM loyalty_points WHERE user_id = ?', (user['id'],))
        loyalty = cursor.fetchone()
        
        if not loyalty:
            # إنشاء حساب نقاط جديد
            cursor.execute('''
                INSERT INTO loyalty_points (user_id, points, tier)
                VALUES (?, 0, 'bronze')
            ''', (user['id'],))
            conn.commit()
            points = 0
            tier = 'bronze'
            total_earned = 0
        else:
            points = loyalty['points']
            tier = loyalty['tier']
            total_earned = loyalty['total_earned']
        
        # حساب النقاط للمستوى التالي
        tier_thresholds = {'bronze': 1000, 'silver': 5000, 'gold': 15000, 'platinum': 50000}
        next_tier = None
        points_needed = 0
        
        for t, threshold in tier_thresholds.items():
            if total_earned < threshold:
                next_tier = t
                points_needed = threshold - total_earned
                break
        
        # آخر 5 عمليات نقاط
        cursor.execute('''
            SELECT points_change, reason, created_at
            FROM points_history 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        ''', (user['id'],))
        recent_history = cursor.fetchall()
        
        conn.close()
        
        tier_emoji = {'bronze': '🥉', 'silver': '🥈', 'gold': '🥇', 'platinum': '💎'}
        
        text = f"""
🎯 **نظام النقاط والولاء** 🎯

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

🏆 **مستوى الولاء:**
{tier_emoji.get(tier, '🥉')} **{tier.upper()}**
⭐ نقاطك الحالية: **{points:,}** نقطة
📈 إجمالي النقاط المكتسبة: **{total_earned:,}** نقطة

{"🎯 **المستوى التالي:** " + tier_emoji.get(next_tier, '') + f" {next_tier.upper()} ({points_needed:,} نقطة)" if next_tier else "🏆 **وصلت لأعلى مستوى!**"}

💡 **طرق كسب النقاط:**
• شراء الكروت: 10 نقاط لكل 100 ريال
• دعوة الأصدقاء: 500 نقطة لكل صديق
• تقييم الشبكات: 50 نقطة لكل تقييم
• إكمال التحديات: حتى 1000 نقطة

📊 **آخر العمليات:**
"""
        
        if recent_history:
            for history in recent_history:
                change = history[0]
                reason = history[1]
                date = history[2][:10]
                emoji = "➕" if change > 0 else "➖"
                text += f"{emoji} {abs(change)} نقطة - {reason} ({date})\n"
        else:
            text += "لا توجد عمليات بعد"
        
        keyboard = [
            [InlineKeyboardButton('🎁 استبدال النقاط', callback_data='redeem_points'),
             InlineKeyboardButton('🎯 التحديات', callback_data='view_challenges')],
            [InlineKeyboardButton('📊 سجل النقاط', callback_data='points_history'),
             InlineKeyboardButton('🏆 لوحة المتصدرين', callback_data='leaderboard')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in loyalty points handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في نظام النقاط.")

async def smart_notifications_handler(update: Update, context: CallbackContext):
    """🔔 إشعارات ذكية ومخصصة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على الإشعارات
        cursor.execute('''
            SELECT title, message, type, priority, created_at, is_read
            FROM notifications 
            WHERE (user_id = ? OR is_global = 1) AND (expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP)
            ORDER BY priority DESC, created_at DESC
            LIMIT 10
        ''', (user['id'],))
        notifications = cursor.fetchall()
        
        # عدد الإشعارات غير المقروءة
        cursor.execute('''
            SELECT COUNT(*) FROM notifications 
            WHERE (user_id = ? OR is_global = 1) AND is_read = 0
        ''', (user['id'],))
        unread_count = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
🔔 **الإشعارات الذكية** 🔔

👤 **{user['full_name']}**
📬 إشعارات غير مقروءة: **{unread_count}**

📋 **آخر الإشعارات:**

"""
        
        if notifications:
            for notif in notifications:
                title, message, notif_type, priority, created_at, is_read = notif
                
                # أيقونات حسب النوع
                type_emoji = {
                    'info': 'ℹ️', 'warning': '⚠️', 'success': '✅', 
                    'error': '❌', 'promotion': '🎁', 'system': '🔧'
                }
                
                priority_emoji = {1: '🔵', 2: '🟡', 3: '🔴'}
                read_emoji = '👁️' if is_read else '🆕'
                
                text += f"""
{type_emoji.get(notif_type, 'ℹ️')} **{title}**
{message[:100]}{'...' if len(message) > 100 else ''}
{priority_emoji.get(priority, '🔵')} {read_emoji} {created_at[:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text += "📭 لا توجد إشعارات"
        
        keyboard = [
            [InlineKeyboardButton('✅ تحديد الكل كمقروء', callback_data='mark_all_notifications_read'),
             InlineKeyboardButton('🔔 إعدادات الإشعارات', callback_data='notification_settings')],
            [InlineKeyboardButton('🗑️ حذف المقروءة', callback_data='delete_read_notifications'),
             InlineKeyboardButton('📱 إشعارات الدفع', callback_data='push_notification_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in smart notifications handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في الإشعارات.")

async def network_reviews_handler(update: Update, context: CallbackContext):
    """⭐ تقييم ومراجعة الشبكات"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الحصول على الشبكات المتاحة للتقييم
        cursor.execute('''
            SELECT n.id, n.name, n.provider, AVG(r.rating) as avg_rating, COUNT(r.id) as review_count
            FROM networks n
            LEFT JOIN reviews r ON n.id = r.network_id
            WHERE n.is_active = 1
            GROUP BY n.id, n.name, n.provider
            ORDER BY avg_rating DESC, review_count DESC
            LIMIT 10
        ''')
        networks = cursor.fetchall()
        
        # تقييمات المستخدم
        cursor.execute('''
            SELECT COUNT(*) FROM reviews WHERE user_id = ?
        ''', (user['id'],))
        user_reviews_count = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
⭐ **تقييم ومراجعة الشبكات** ⭐

👤 **{user['full_name']}**
📝 تقييماتك: **{user_reviews_count}** تقييم

🌐 **الشبكات المتاحة للتقييم:**

"""
        
        keyboard = []
        
        if networks:
            for network in networks:
                net_id, name, provider, avg_rating, review_count = network
                avg_rating = avg_rating or 0
                stars = "⭐" * int(avg_rating) + "☆" * (5 - int(avg_rating))
                
                text += f"""
🌐 **{name}**
👤 مزود: {provider}
{stars} ({avg_rating:.1f}/5) • {review_count} تقييم
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                keyboard.append([
                    InlineKeyboardButton(f'⭐ قيم {name}', callback_data=f'rate_network_{net_id}'),
                    InlineKeyboardButton(f'📖 المراجعات', callback_data=f'view_reviews_{net_id}')
                ])
        else:
            text += "❌ لا توجد شبكات متاحة للتقييم"
        
        keyboard.extend([
            [InlineKeyboardButton('📝 تقييماتي', callback_data='my_reviews'),
             InlineKeyboardButton('🏆 أفضل الشبكات', callback_data='top_rated_networks')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in network reviews handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في التقييمات.")

async def internal_messaging_handler(update: Update, context: CallbackContext):
    """💬 رسائل داخلية بين المستخدمين"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # عدد الرسائل غير المقروءة
        cursor.execute('''
            SELECT COUNT(*) FROM internal_messages 
            WHERE to_user_id = ? AND is_read = 0
        ''', (user['id'],))
        unread_count = cursor.fetchone()[0]
        
        # آخر الرسائل
        cursor.execute('''
            SELECT im.subject, im.message, u.full_name, im.created_at, im.is_read
            FROM internal_messages im
            JOIN users u ON im.from_user_id = u.id
            WHERE im.to_user_id = ?
            ORDER BY im.created_at DESC
            LIMIT 5
        ''', (user['id'],))
        messages = cursor.fetchall()
        
        conn.close()
        
        text = f"""
💬 **الرسائل الداخلية** 💬

👤 **{user['full_name']}**
📬 رسائل غير مقروءة: **{unread_count}**

📨 **صندوق الوارد:**

"""
        
        if messages:
            for msg in messages:
                subject, message, sender, created_at, is_read = msg
                read_emoji = '👁️' if is_read else '🆕'
                text += f"""
{read_emoji} **{subject or 'بدون عنوان'}**
👤 من: {sender}
📝 {message[:50]}{'...' if len(message) > 50 else ''}
🕐 {created_at[:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text += "📭 لا توجد رسائل"
        
        keyboard = [
            [InlineKeyboardButton('✉️ إنشاء رسالة جديدة', callback_data='compose_message'),
             InlineKeyboardButton('📬 الرسائل المرسلة', callback_data='sent_messages')],
            [InlineKeyboardButton('🗑️ حذف المقروءة', callback_data='delete_read_messages'),
             InlineKeyboardButton('⚙️ إعدادات الرسائل', callback_data='message_settings')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in internal messaging handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في الرسائل.")

async def games_contests_handler(update: Update, context: CallbackContext):
    """🎮 ألعاب ومسابقات تفاعلية"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الألعاب النشطة
        cursor.execute('''
            SELECT id, title, description, prize_pool, entry_fee, current_participants, max_participants, end_date
            FROM games_contests 
            WHERE is_active = 1 AND end_date > CURRENT_TIMESTAMP
            ORDER BY prize_pool DESC
            LIMIT 5
        ''')
        active_games = cursor.fetchall()
        
        # ألعاب المستخدم
        cursor.execute('''
            SELECT COUNT(*) FROM game_participants WHERE user_id = ?
        ''', (user['id'],))
        user_games_count = cursor.fetchone()[0]
        
        # إجمالي الجوائز المكتسبة
        cursor.execute('''
            SELECT COALESCE(SUM(prize_won), 0) FROM game_participants WHERE user_id = ?
        ''', (user['id'],))
        total_prizes = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
🎮 **الألعاب والمسابقات** 🎮

👤 **{user['full_name']}**
🎯 ألعابك: **{user_games_count}** لعبة
🏆 جوائزك: **{total_prizes:,.2f}** ريال

🎪 **المسابقات النشطة:**

"""
        
        keyboard = []
        
        if active_games:
            for game in active_games:
                game_id, title, desc, prize_pool, entry_fee, current, max_p, end_date = game
                
                text += f"""
🎮 **{title}**
📝 {desc[:60]}{'...' if len(desc) > 60 else ''}
💰 جائزة: {prize_pool:,.0f} ريال
🎫 رسم الدخول: {entry_fee:,.0f} ريال
👥 المشاركون: {current}/{max_p or '∞'}
⏰ ينتهي: {end_date[:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                keyboard.append([
                    InlineKeyboardButton(f'🎮 انضم لـ{title}', callback_data=f'join_game_{game_id}')
                ])
        else:
            text += "🎪 لا توجد مسابقات نشطة حالياً"
        
        keyboard.extend([
            [InlineKeyboardButton('🎯 إنشاء مسابقة', callback_data='create_contest'),
             InlineKeyboardButton('🏆 سجل الجوائز', callback_data='my_prizes')],
            [InlineKeyboardButton('📊 الإحصائيات', callback_data='games_stats'),
             InlineKeyboardButton('🎪 الألعاب المنتهية', callback_data='finished_games')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in games contests handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في الألعاب.")

async def educational_content_handler(update: Update, context: CallbackContext):
    """🎓 محتوى تعليمي متقدم"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # المحتوى التعليمي المتاح
        cursor.execute('''
            SELECT id, title, category, difficulty_level, estimated_time, view_count
            FROM educational_content 
            WHERE is_published = 1
            ORDER BY category, difficulty_level
            LIMIT 8
        ''')
        content_list = cursor.fetchall()
        
        # تقدم المستخدم
        cursor.execute('''
            SELECT COUNT(*) as completed, AVG(progress_percentage) as avg_progress
            FROM user_learning_progress 
            WHERE user_id = ?
        ''', (user['id'],))
        progress_data = cursor.fetchone()
        completed_count = progress_data[0] if progress_data else 0
        avg_progress = progress_data[1] if progress_data else 0
        
        conn.close()
        
        text = f"""
🎓 **المحتوى التعليمي** 🎓

👤 **{user['full_name']}**
📚 المحتوى المكتمل: **{completed_count}**
📊 متوسط التقدم: **{avg_progress:.1f}%**

📖 **المحتوى المتاح:**

"""
        
        keyboard = []
        current_category = None
        
        if content_list:
            for content in content_list:
                content_id, title, category, difficulty, time, views = content
                
                if category != current_category:
                    text += f"\n📂 **{category.upper()}:**\n"
                    current_category = category
                
                difficulty_emoji = {'beginner': '🟢', 'intermediate': '🟡', 'advanced': '🔴'}
                
                text += f"""
📖 **{title}**
{difficulty_emoji.get(difficulty, '🟢')} {difficulty} • ⏱️ {time or 15} دقيقة • 👀 {views} مشاهدة
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                keyboard.append([
                    InlineKeyboardButton(f'📖 {title}', callback_data=f'learn_content_{content_id}')
                ])
        else:
            text += "📚 لا يوجد محتوى متاح حالياً"
        
        keyboard.extend([
            [InlineKeyboardButton('📊 تقدمي التعليمي', callback_data='my_learning_progress'),
             InlineKeyboardButton('🏆 شهادات الإنجاز', callback_data='my_certificates')],
            [InlineKeyboardButton('💡 اقتراح محتوى', callback_data='suggest_content'),
             InlineKeyboardButton('❓ مساعدة التعلم', callback_data='learning_help')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in educational content handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في المحتوى التعليمي.")

async def advanced_wallet_security_handler(update: Update, context: CallbackContext):
    """🔐 أمان محفظة متقدم"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إعدادات الأمان
        cursor.execute('SELECT * FROM wallet_advanced WHERE user_id = ?', (user['id'],))
        wallet_security = cursor.fetchone()
        
        if not wallet_security:
            # إنشاء إعدادات أمان افتراضية
            cursor.execute('''
                INSERT INTO wallet_advanced (user_id, wallet_type, daily_limit, monthly_limit, security_level)
                VALUES (?, 'standard', 10000, 100000, 1)
            ''', (user['id'],))
            conn.commit()
            daily_limit = 10000
            monthly_limit = 100000
            security_level = 1
            two_factor = False
        else:
            daily_limit = wallet_security['daily_limit']
            monthly_limit = wallet_security['monthly_limit']
            security_level = wallet_security['security_level']
            two_factor = wallet_security['two_factor_enabled']
        
        # آخر أنشطة الأمان
        cursor.execute('''
            SELECT action_type, success, created_at
            FROM wallet_security_log 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        ''', (user['id'],))
        security_log = cursor.fetchall()
        
        conn.close()
        
        security_level_text = {1: '🟢 أساسي', 2: '🟡 متوسط', 3: '🔴 عالي'}
        
        text = f"""
🔐 **أمان المحفظة المتقدم** 🔐

👤 **{user['full_name']}**
💳 رقم المحفظة: **{user['wallet_number']}**

🛡️ **مستوى الأمان:**
{security_level_text.get(security_level, '🟢 أساسي')}

🔒 **الإعدادات الحالية:**
📱 التحقق الثنائي: **{'✅ مفعل' if two_factor else '❌ غير مفعل'}**
💰 الحد اليومي: **{daily_limit:,.0f}** ريال
📅 الحد الشهري: **{monthly_limit:,.0f}** ريال

📊 **آخر أنشطة الأمان:**
"""
        
        if security_log:
            for log in security_log:
                action, success, created_at = log
                status_emoji = '✅' if success else '❌'
                text += f"{status_emoji} {action} - {created_at[:10]}\n"
        else:
            text += "لا توجد أنشطة مسجلة"
        
        keyboard = [
            [InlineKeyboardButton('🔐 تفعيل التحقق الثنائي', callback_data='enable_2fa'),
             InlineKeyboardButton('🔑 تغيير رقم PIN', callback_data='change_pin')],
            [InlineKeyboardButton('💰 تعديل الحدود', callback_data='edit_limits'),
             InlineKeyboardButton('📱 الأجهزة الموثوقة', callback_data='trusted_devices')],
            [InlineKeyboardButton('🛡️ رفع مستوى الأمان', callback_data='upgrade_security'),
             InlineKeyboardButton('📊 سجل الأمان الكامل', callback_data='full_security_log')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in advanced wallet security handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في أمان المحفظة.")

async def subscription_plans_handler(update: Update, context: CallbackContext):
    """📱 اشتراكات وخطط مميزة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # الخطط المتاحة
        cursor.execute('''
            SELECT id, plan_name, description, price_monthly, price_yearly, features_json
            FROM subscription_plans 
            WHERE is_active = 1
            ORDER BY price_monthly
        ''')
        plans = cursor.fetchall()
        
        # اشتراك المستخدم الحالي
        cursor.execute('''
            SELECT plan_name, expires_at, is_active
            FROM subscriptions 
            WHERE user_id = ? AND is_active = 1
            ORDER BY expires_at DESC
            LIMIT 1
        ''', (user['id'],))
        current_subscription = cursor.fetchone()
        
        conn.close()
        
        text = f"""
📱 **الاشتراكات والخطط المميزة** 📱

👤 **{user['full_name']}**
💰 رصيدك: **{user['balance']:,.2f}** ريال

"""
        
        if current_subscription:
            plan_name, expires_at, is_active = current_subscription
            text += f"""
📋 **اشتراكك الحالي:**
✅ **{plan_name.upper()}**
📅 ينتهي في: {expires_at[:10]}
🔄 حالة التجديد: {'تلقائي' if is_active else 'يدوي'}

"""
        else:
            text += "📋 **لا يوجد اشتراك نشط**\n\n"
        
        text += "💎 **الخطط المتاحة:**\n\n"
        
        keyboard = []
        
        if plans:
            for plan in plans:
                plan_id, name, desc, monthly, yearly, features = plan
                
                try:
                    features_dict = json.loads(features)
                    features_text = " • ".join([f"{k}: {v}" for k, v in features_dict.items()])
                except:
                    features_text = "ميزات متقدمة"
                
                text += f"""
💎 **{name.upper()}**
📝 {desc}
💰 شهري: **{monthly:,.0f}** ريال
💰 سنوي: **{yearly:,.0f}** ريال (وفر {((monthly*12-yearly)/monthly/12*100):,.0f}%)
✨ {features_text}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
                
                keyboard.append([
                    InlineKeyboardButton(f'📱 اشترك {name}', callback_data=f'subscribe_plan_{plan_id}')
                ])
        
        keyboard.extend([
            [InlineKeyboardButton('🔄 تجديد الاشتراك', callback_data='renew_subscription'),
             InlineKeyboardButton('❌ إلغاء الاشتراك', callback_data='cancel_subscription')],
            [InlineKeyboardButton('📊 استخدام الميزات', callback_data='feature_usage'),
             InlineKeyboardButton('💳 سجل المدفوعات', callback_data='payment_history')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in subscription plans handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في الاشتراكات.")

async def ai_recommendations_handler(update: Update, context: CallbackContext):
    """💡 توصيات ذكية مدعومة بالذكاء الاصطناعي"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # توليد توصيات ذكية بناءً على نشاط المستخدم
        
        # تحليل سلوك المستخدم
        cursor.execute('''
            SELECT COUNT(*) as purchase_count, AVG(amount) as avg_amount
            FROM transactions 
            WHERE to_user = ? AND type = 'card_purchase'
        ''', (user['id'],))
        purchase_behavior = cursor.fetchone()
        
        # الشبكات المفضلة
        cursor.execute('''
            SELECT network_id, COUNT(*) as usage_count
            FROM transactions t
            JOIN cards c ON t.description LIKE '%' || c.code || '%'
            JOIN card_categories cc ON c.category_id = cc.id
            WHERE t.to_user = ?
            GROUP BY network_id
            ORDER BY usage_count DESC
            LIMIT 3
        ''', (user['id'],))
        preferred_networks = cursor.fetchall()
        
        # إنشاء توصيات ذكية
        recommendations = []
        
        if purchase_behavior and purchase_behavior[0] > 0:
            avg_amount = purchase_behavior[1] or 0
            
            if avg_amount < 50:
                recommendations.append({
                    'type': 'budget_friendly',
                    'title': '💰 عروض اقتصادية',
                    'description': f'بناءً على متوسط مشترياتك ({avg_amount:.0f} ريال)، هذه عروض مناسبة لميزانيتك',
                    'confidence': 0.8
                })
            elif avg_amount > 200:
                recommendations.append({
                    'type': 'premium_offers',
                    'title': '💎 عروض مميزة',
                    'description': f'كمستخدم مميز (متوسط {avg_amount:.0f} ريال)، هذه عروض حصرية لك',
                    'confidence': 0.9
                })
        
        # توصيات بناءً على الوقت
        current_hour = datetime.datetime.now().hour
        if 9 <= current_hour <= 17:
            recommendations.append({
                'type': 'work_hours',
                'title': '⚡ عروض ساعات العمل',
                'description': 'خصومات خاصة خلال ساعات العمل للمستخدمين النشطين',
                'confidence': 0.7
            })
        
        # توصيات عامة
        recommendations.extend([
            {
                'type': 'loyalty_program',
                'title': '🎯 برنامج الولاء',
                'description': 'اكسب نقاط مع كل عملية شراء واستبدلها بجوائز رائعة',
                'confidence': 0.9
            },
            {
                'type': 'referral_bonus',
                'title': '🎁 مكافآت الإحالة',
                'description': 'ادع أصدقاءك واحصل على مكافآت نقدية لكل صديق ينضم',
                'confidence': 0.8
            }
        ])
        
        conn.close()
        
        text = f"""
💡 **التوصيات الذكية** 💡

👤 **{user['full_name']}**
🤖 مدعوم بالذكاء الاصطناعي

🎯 **توصيات مخصصة لك:**

"""
        
        keyboard = []
        
        for i, rec in enumerate(recommendations[:4], 1):
            confidence_stars = "⭐" * int(rec['confidence'] * 5)
            
            text += f"""
{i}️⃣ **{rec['title']}**
📝 {rec['description']}
🎯 دقة التوصية: {confidence_stars} ({rec['confidence']*100:.0f}%)
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
            
            keyboard.append([
                InlineKeyboardButton(f'✨ {rec["title"]}', callback_data=f'apply_recommendation_{rec["type"]}')
            ])
        
        keyboard.extend([
            [InlineKeyboardButton('🔄 توصيات جديدة', callback_data='refresh_recommendations'),
             InlineKeyboardButton('📊 تحليل سلوكي', callback_data='behavior_analysis')],
            [InlineKeyboardButton('⚙️ إعدادات التوصيات', callback_data='recommendation_settings'),
             InlineKeyboardButton('📈 تقييم التوصيات', callback_data='rate_recommendations')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in AI recommendations handler: {e}")
        await query.edit_message_text("❌ حدث خطأ في التوصيات الذكية.")

# ===== معالجات الميزات المتقدمة للمزودين =====

async def supplier_advanced_dashboard_handler(update: Update, context: CallbackContext):
    """📊 لوحة تحكم المزود المتقدمة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['supplier', 'admin', 'super_admin']:
            await query.edit_message_text("❌ ليس لديك صلاحية لهذه العملية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات المزود
        cursor.execute('''
            SELECT 
                COUNT(DISTINCT n.id) as networks_count,
                COUNT(DISTINCT cc.id) as categories_count,
                COUNT(c.id) as total_cards,
                COUNT(CASE WHEN c.is_used = 1 THEN 1 END) as sold_cards,
                COALESCE(SUM(CASE WHEN c.is_used = 1 THEN cc.price ELSE 0 END), 0) as total_revenue
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.supplier_id = ?
        ''', (user['id'],))
        stats = cursor.fetchone()
        
        # إحصائيات هذا الشهر
        cursor.execute('''
            SELECT 
                COUNT(CASE WHEN c.is_used = 1 AND c.used_at >= date('now', 'start of month') THEN 1 END) as monthly_sales,
                COALESCE(SUM(CASE WHEN c.is_used = 1 AND c.used_at >= date('now', 'start of month') THEN cc.price ELSE 0 END), 0) as monthly_revenue
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.supplier_id = ?
        ''', (user['id'],))
        monthly_stats = cursor.fetchone()
        
        # أفضل الشبكات أداءً
        cursor.execute('''
            SELECT n.name, COUNT(CASE WHEN c.is_used = 1 THEN 1 END) as sales
            FROM networks n
            LEFT JOIN card_categories cc ON n.id = cc.network_id
            LEFT JOIN cards c ON cc.id = c.category_id
            WHERE n.supplier_id = ?
            GROUP BY n.id, n.name
            ORDER BY sales DESC
            LIMIT 3
        ''', (user['id'],))
        top_networks = cursor.fetchall()
        
        conn.close()
        
        networks_count = stats[0] if stats else 0
        categories_count = stats[1] if stats else 0
        total_cards = stats[2] if stats else 0
        sold_cards = stats[3] if stats else 0
        total_revenue = stats[4] if stats else 0
        
        monthly_sales = monthly_stats[0] if monthly_stats else 0
        monthly_revenue = monthly_stats[1] if monthly_stats else 0
        
        text = f"""
📊 **لوحة تحكم المزود المتقدمة** 📊

👤 **{user['full_name']}**
🏷️ **مزود معتمد**

📈 **الإحصائيات العامة:**
🌐 شبكاتك: **{networks_count}** شبكة
📋 فئات الكروت: **{categories_count}** فئة
💳 إجمالي الكروت: **{total_cards:,}** كرت
✅ الكروت المباعة: **{sold_cards:,}** كرت
💰 إجمالي الإيرادات: **{total_revenue:,.2f}** ريال

📅 **هذا الشهر:**
🛒 المبيعات: **{monthly_sales:,}** كرت
💵 الإيرادات: **{monthly_revenue:,.2f}** ريال

🏆 **أفضل الشبكات أداءً:**
"""
        
        if top_networks:
            for i, (network_name, sales) in enumerate(top_networks, 1):
                medal = ['🥇', '🥈', '🥉'][i-1] if i <= 3 else '🏅'
                text += f"{medal} {network_name}: {sales:,} مبيعة\n"
        else:
            text += "لا توجد مبيعات بعد"
        
        keyboard = [
            [InlineKeyboardButton('📈 تحليلات مفصلة', callback_data='detailed_analytics'),
             InlineKeyboardButton('👥 إدارة العملاء', callback_data='customer_management')],
            [InlineKeyboardButton('💰 العمولات والأرباح', callback_data='commission_profits'),
             InlineKeyboardButton('📦 إدارة المخزون الذكية', callback_data='smart_inventory')],
            [InlineKeyboardButton('🔄 أتمتة العمليات', callback_data='business_automation'),
             InlineKeyboardButton('📞 دعم العملاء', callback_data='customer_support_panel')],
            [InlineKeyboardButton('🤝 الشراكات التجارية', callback_data='business_partnerships'),
             InlineKeyboardButton('🎯 أهداف المبيعات', callback_data='sales_targets')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in supplier advanced dashboard: {e}")
        await query.edit_message_text("❌ حدث خطأ في لوحة تحكم المزود.")

# ===== معالجات الميزات المتقدمة للإدارة =====

async def advanced_admin_dashboard_handler(update: Update, context: CallbackContext):
    """🎛️ لوحة تحكم إدارية شاملة"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user or user['role'] not in ['admin', 'super_admin']:
            await query.edit_message_text("❌ ليس لديك صلاحية إدارية.")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # إحصائيات شاملة
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE is_active = 1')
        active_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM transactions WHERE created_at >= date("now", "-7 days")')
        weekly_transactions = cursor.fetchone()[0]
        
        cursor.execute('SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type = "card_purchase" AND created_at >= date("now", "-30 days")')
        monthly_revenue = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM support_tickets WHERE status = "open"')
        open_tickets = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM notifications WHERE is_global = 1 AND created_at >= date("now", "-1 day")')
        recent_announcements = cursor.fetchone()[0]
        
        conn.close()
        
        text = f"""
🎛️ **لوحة التحكم الإدارية الشاملة** 🎛️

👑 **{user['full_name']}**
🔧 **مشرف النظام**

📊 **الإحصائيات السريعة:**
👥 إجمالي المستخدمين: **{total_users:,}**
✅ المستخدمون النشطون: **{active_users:,}**
📈 معاملات الأسبوع: **{weekly_transactions:,}**
💰 إيرادات الشهر: **{monthly_revenue:,.2f}** ريال
🎫 تذاكر مفتوحة: **{open_tickets}**
📢 إعلانات حديثة: **{recent_announcements}**

🎯 **الأدوات المتقدمة:**
"""
        
        keyboard = [
            [InlineKeyboardButton('🔍 مراقبة متقدمة', callback_data='advanced_monitoring'),
             InlineKeyboardButton('🛡️ أمان وحماية', callback_data='security_center')],
            [InlineKeyboardButton('📊 تحليلات ذكية', callback_data='smart_analytics'),
             InlineKeyboardButton('🎫 إدارة التذاكر', callback_data='ticket_management')],
            [InlineKeyboardButton('👥 إدارة المستخدمين المتطورة', callback_data='advanced_user_management'),
             InlineKeyboardButton('💼 إدارة الأعمال', callback_data='business_management')],
            [InlineKeyboardButton('🎮 إدارة الألعاب', callback_data='games_management'),
             InlineKeyboardButton('📚 إدارة المحتوى', callback_data='content_management')],
            [InlineKeyboardButton('🔑 إدارة API', callback_data='api_management'),
             InlineKeyboardButton('🌍 الإعدادات العالمية', callback_data='global_settings')],
            [InlineKeyboardButton('🏠 لوحة المشرف الأعلى', callback_data='super_admin_panel')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in advanced admin dashboard: {e}")
        await query.edit_message_text("❌ حدث خطأ في لوحة التحكم الإدارية.")

# ===== معالجات الدعم المتقدم =====

async def advanced_support_system_handler(update: Update, context: CallbackContext):
    """🎫 نظام التذاكر والدعم المتقدم"""
    try:
        query = update.callback_query
        await query.answer()
        
        user = get_user(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ يرجى التسجيل أولاً /start")
            return
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # تذاكر المستخدم
        cursor.execute('''
            SELECT ticket_number, subject, status, priority, created_at
            FROM support_tickets 
            WHERE user_id = ?
            ORDER BY created_at DESC
            LIMIT 5
        ''', (user['id'],))
        user_tickets = cursor.fetchall()
        
        # إحصائيات الدعم
        cursor.execute('''
            SELECT 
                COUNT(*) as total_tickets,
                COUNT(CASE WHEN status = 'open' THEN 1 END) as open_tickets,
                COUNT(CASE WHEN status = 'resolved' THEN 1 END) as resolved_tickets,
                AVG(CASE WHEN satisfaction_rating IS NOT NULL THEN satisfaction_rating END) as avg_satisfaction
            FROM support_tickets 
            WHERE user_id = ?
        ''', (user['id'],))
        ticket_stats = cursor.fetchone()
        
        conn.close()
        
        total_tickets = ticket_stats[0] if ticket_stats else 0
        open_tickets = ticket_stats[1] if ticket_stats else 0
        resolved_tickets = ticket_stats[2] if ticket_stats else 0
        avg_satisfaction = ticket_stats[3] if ticket_stats else 0
        
        text = f"""
🎫 **نظام الدعم المتقدم** 🎫

👤 **{user['full_name']}**

📊 **إحصائيات الدعم:**
📋 إجمالي التذاكر: **{total_tickets}**
🔓 تذاكر مفتوحة: **{open_tickets}**
✅ تذاكر محلولة: **{resolved_tickets}**
⭐ متوسط الرضا: **{avg_satisfaction:.1f}/5**

🎫 **تذاكرك الأخيرة:**

"""
        
        if user_tickets:
            for ticket in user_tickets:
                ticket_num, subject, status, priority, created_at = ticket
                
                status_emoji = {'open': '🔓', 'in_progress': '🔄', 'resolved': '✅', 'closed': '🔒'}
                priority_emoji = {'low': '🟢', 'medium': '🟡', 'high': '🔴', 'urgent': '🚨'}
                
                text += f"""
🎫 **#{ticket_num}**
📝 {subject}
{status_emoji.get(status, '🔓')} {status} • {priority_emoji.get(priority, '🟡')} {priority}
📅 {created_at[:10]}
━━━━━━━━━━━━━━━━━━━━━━━━━
"""
        else:
            text += "📭 لا توجد تذاكر"
        
        keyboard = [
            [InlineKeyboardButton('🆕 تذكرة جديدة', callback_data='create_support_ticket'),
             InlineKeyboardButton('🔍 البحث في التذاكر', callback_data='search_tickets')],
            [InlineKeyboardButton('📊 تذاكر مفتوحة', callback_data='open_tickets'),
             InlineKeyboardButton('✅ تذاكر محلولة', callback_data='resolved_tickets')],
            [InlineKeyboardButton('💬 دردشة مباشرة', callback_data='live_chat'),
             InlineKeyboardButton('📞 طلب مكالمة', callback_data='request_call')],
            [InlineKeyboardButton('❓ الأسئلة الشائعة', callback_data='faq_advanced'),
             InlineKeyboardButton('📚 مركز المساعدة', callback_data='help_center')],
            [InlineKeyboardButton('🏠 القائمة الرئيسية', callback_data='main_menu')]
        ]
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error in advanced support system: {e}")
        await query.edit_message_text("❌ حدث خطأ في نظام الدعم.")

# ===== قاموس المعالجات المتقدمة =====

ADVANCED_HANDLERS = {
    # ميزات المستخدم
    'loyalty_points': loyalty_points_handler,
    'smart_notifications': smart_notifications_handler,
    'network_reviews': network_reviews_handler,
    'internal_messaging': internal_messaging_handler,
    'games_contests': games_contests_handler,
    'educational_content': educational_content_handler,
    'advanced_wallet_security': advanced_wallet_security_handler,
    'subscription_plans': subscription_plans_handler,
    'ai_recommendations': ai_recommendations_handler,
    
    # ميزات المزود
    'supplier_advanced_dashboard': supplier_advanced_dashboard_handler,
    
    # ميزات الإدارة
    'advanced_admin_dashboard': advanced_admin_dashboard_handler,
    'advanced_support_system': advanced_support_system_handler,
}