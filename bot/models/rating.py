"""
نظام التقييم
"""

import logging
from dataclasses import dataclass
from typing import Optional, List, Dict
from datetime import datetime
from bot.database.connection import db_manager
from bot.config import MAX_RATING_STARS, MIN_RATING_STARS

logger = logging.getLogger(__name__)

@dataclass
class Rating:
    """نموذج التقييم"""
    id: Optional[int] = None
    user_id: int = 0
    rating: int = 5
    comment: Optional[str] = None
    service_type: str = "general"
    created_at: Optional[datetime] = None

class RatingSystem:
    """نظام إدارة التقييمات"""
    
    @staticmethod
    def add_rating(user_id: int, stars: int, comment: str = None, service_type: str = "general") -> dict:
        """إضافة تقييم جديد"""
        
        # التحقق من صحة التقييم
        if stars < MIN_RATING_STARS or stars > MAX_RATING_STARS:
            return {
                'success': False,
                'message': f'التقييم يجب أن يكون بين {MIN_RATING_STARS} و {MAX_RATING_STARS} نجوم'
            }
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                # التحقق من وجود المستخدم
                cursor.execute('SELECT id FROM users WHERE id = ?', (user_id,))
                if not cursor.fetchone():
                    return {'success': False, 'message': 'المستخدم غير موجود'}
                
                # إضافة التقييم
                cursor.execute('''
                    INSERT INTO ratings (user_id, rating, comment, service_type)
                    VALUES (?, ?, ?, ?)
                ''', (user_id, stars, comment, service_type))
                
                rating_id = cursor.lastrowid
                
                # تسجيل النشاط
                cursor.execute('''
                    INSERT INTO activity_log (user_id, action, details)
                    VALUES (?, ?, ?)
                ''', (user_id, 'تقييم الخدمة', f'تقييم {stars} نجوم - {service_type}'))
                
                return {
                    'success': True,
                    'message': 'تم إرسال التقييم بنجاح',
                    'rating_id': rating_id
                }
                
        except Exception as e:
            logger.error(f"خطأ في إضافة التقييم: {e}")
            return {'success': False, 'message': 'حدث خطأ أثناء إرسال التقييم'}
    
    @staticmethod
    def get_average_rating(service_type: str = None) -> float:
        """حساب متوسط التقييم"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                if service_type:
                    cursor.execute('SELECT AVG(rating) FROM ratings WHERE service_type = ?', (service_type,))
                else:
                    cursor.execute('SELECT AVG(rating) FROM ratings')
                
                result = cursor.fetchone()
                return round(result[0] if result[0] else 0.0, 2)
                
        except Exception as e:
            logger.error(f"خطأ في حساب متوسط التقييم: {e}")
            return 0.0
    
    @staticmethod
    def get_rating_stats(service_type: str = None) -> Dict:
        """إحصائيات التقييم التفصيلية"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                base_query = 'FROM ratings'
                where_clause = ''
                params = ()
                
                if service_type:
                    where_clause = ' WHERE service_type = ?'
                    params = (service_type,)
                
                # إجمالي التقييمات
                cursor.execute(f'SELECT COUNT(*) {base_query}{where_clause}', params)
                total_ratings = cursor.fetchone()[0]
                
                # متوسط التقييم
                cursor.execute(f'SELECT AVG(rating) {base_query}{where_clause}', params)
                avg_rating = cursor.fetchone()[0] or 0.0
                
                # توزيع النجوم
                stars_distribution = {}
                for stars in range(MIN_RATING_STARS, MAX_RATING_STARS + 1):
                    cursor.execute(f'SELECT COUNT(*) {base_query}{where_clause} AND rating = ?', 
                                 params + (stars,) if service_type else (stars,))
                    stars_distribution[stars] = cursor.fetchone()[0]
                
                # أحدث التقييمات
                cursor.execute(f'''
                    SELECT r.rating, r.comment, r.created_at, u.full_name
                    {base_query} r
                    JOIN users u ON r.user_id = u.id
                    {where_clause}
                    ORDER BY r.created_at DESC
                    LIMIT 10
                ''', params)
                
                latest_ratings = []
                for row in cursor.fetchall():
                    latest_ratings.append({
                        'rating': row[0],
                        'comment': row[1],
                        'created_at': row[2],
                        'user_name': row[3]
                    })
                
                return {
                    'total_ratings': total_ratings,
                    'average_rating': round(avg_rating, 2),
                    'stars_distribution': stars_distribution,
                    'latest_ratings': latest_ratings
                }
                
        except Exception as e:
            logger.error(f"خطأ في جلب إحصائيات التقييم: {e}")
            return {
                'total_ratings': 0,
                'average_rating': 0.0,
                'stars_distribution': {},
                'latest_ratings': []
            }
    
    @staticmethod
    def get_user_ratings(user_id: int, limit: int = 20) -> List[Dict]:
        """جلب تقييمات مستخدم معين"""
        
        try:
            with db_manager.get_cursor() as (conn, cursor):
                cursor.execute('''
                    SELECT rating, comment, service_type, created_at
                    FROM ratings
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                ''', (user_id, limit))
                
                ratings = []
                for row in cursor.fetchall():
                    ratings.append({
                        'rating': row[0],
                        'comment': row[1],
                        'service_type': row[2],
                        'created_at': row[3]
                    })
                
                return ratings
                
        except Exception as e:
            logger.error(f"خطأ في جلب تقييمات المستخدم: {e}")
            return []
    
    @staticmethod
    def generate_rating_report() -> str:
        """إنشاء تقرير التقييمات"""
        
        stats = RatingSystem.get_rating_stats()
        
        if stats['total_ratings'] == 0:
            return "📊 تقرير التقييمات\n\nلا توجد تقييمات حتى الآن."
        
        report = f"""📊 تقرير التقييمات

إجمالي التقييمات: {stats['total_ratings']}
متوسط التقييم: {stats['average_rating']} / {MAX_RATING_STARS} ⭐

توزيع النجوم:"""
        
        for stars in range(MAX_RATING_STARS, MIN_RATING_STARS - 1, -1):
            count = stats['stars_distribution'].get(stars, 0)
            percentage = (count / stats['total_ratings'] * 100) if stats['total_ratings'] > 0 else 0
            stars_emoji = "⭐" * stars
            report += f"\n{stars_emoji} ({stars}): {count} ({percentage:.1f}%)"
        
        if stats['latest_ratings']:
            report += "\n\nآخر التقييمات:"
            for rating in stats['latest_ratings'][:5]:
                stars_emoji = "⭐" * rating['rating']
                comment = rating['comment'][:50] + "..." if rating['comment'] and len(rating['comment']) > 50 else rating['comment']
                report += f"\n• {stars_emoji} - {comment or 'بدون تعليق'}"
        
        return report