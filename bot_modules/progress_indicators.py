#!/usr/bin/env python3
"""
Progress Indicators - مؤشرات التقدم
يعرض مؤشرات تقدم للعمليات الطويلة لتحسين تجربة المستخدم
"""

import logging
import asyncio
import time
from typing import Dict, Any, Optional, Callable, List
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext

logger = logging.getLogger(__name__)

class ProgressIndicator:
    """مؤشر التقدم للعمليات الطويلة"""
    
    def __init__(self):
        self.active_operations = {}
        self.progress_symbols = ['⏳', '🔄', '⚙️', '🔧', '⚡', '✅']
    
    async def show_progress(self, update: Update, context: CallbackContext,
                          operation_name: str, total_steps: int = 5,
                          initial_message: str = "جاري المعالجة...") -> str:
        """عرض مؤشر تقدم أولي"""
        operation_id = f"{update.effective_user.id}_{operation_name}_{int(time.time())}"
        
        # إنشاء رسالة التقدم الأولية
        progress_text = f"{self.progress_symbols[0]} **{initial_message}**\n\n"
        progress_text += self._create_progress_bar(0, total_steps)
        progress_text += f"\n📊 الخطوة 1 من {total_steps}"
        
        # إرسال أو تحديث الرسالة
        try:
            if hasattr(update, 'callback_query') and update.callback_query:
                message = await update.callback_query.edit_message_text(
                    progress_text,
                    parse_mode='Markdown'
                )
            else:
                message = await update.message.reply_text(
                    progress_text,
                    parse_mode='Markdown'
                )
            
            # تسجيل العملية النشطة
            self.active_operations[operation_id] = {
                'message': message,
                'total_steps': total_steps,
                'current_step': 1,
                'start_time': time.time(),
                'operation_name': operation_name
            }
            
            return operation_id
            
        except Exception as e:
            logger.error(f"Failed to show initial progress: {e}")
            return None
    
    async def update_progress(self, operation_id: str, step: int, 
                            step_description: str = "", 
                            show_time: bool = True) -> bool:
        """تحديث مؤشر التقدم"""
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        
        try:
            # حساب النسبة المئوية
            progress_percentage = min((step / operation['total_steps']) * 100, 100)
            symbol_index = min(step, len(self.progress_symbols) - 1)
            
            # إنشاء نص التقدم
            progress_text = f"{self.progress_symbols[symbol_index]} **{operation['operation_name']}**\n\n"
            progress_text += self._create_progress_bar(step, operation['total_steps'])
            progress_text += f"\n📊 الخطوة {step} من {operation['total_steps']} ({progress_percentage:.0f}%)"
            
            if step_description:
                progress_text += f"\n🔄 {step_description}"
            
            if show_time:
                elapsed_time = time.time() - operation['start_time']
                progress_text += f"\n⏱️ الوقت المنقضي: {elapsed_time:.1f} ثانية"
                
                # تقدير الوقت المتبقي
                if step > 1:
                    estimated_total = (elapsed_time / (step - 1)) * operation['total_steps']
                    remaining_time = max(0, estimated_total - elapsed_time)
                    progress_text += f"\n⏰ الوقت المتوقع: {remaining_time:.1f} ثانية"
            
            # تحديث الرسالة
            await operation['message'].edit_text(
                progress_text,
                parse_mode='Markdown'
            )
            
            # تحديث الخطوة الحالية
            operation['current_step'] = step
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update progress for {operation_id}: {e}")
            return False
    
    async def complete_progress(self, operation_id: str, 
                              success_message: str = "تمت العملية بنجاح! ✅",
                              show_summary: bool = True,
                              final_keyboard: InlineKeyboardMarkup = None) -> bool:
        """إكمال مؤشر التقدم"""
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        
        try:
            total_time = time.time() - operation['start_time']
            
            # إنشاء رسالة الإكمال
            completion_text = f"✅ **{success_message}**\n\n"
            
            if show_summary:
                completion_text += f"📊 **ملخص العملية:**\n"
                completion_text += f"• العملية: {operation['operation_name']}\n"
                completion_text += f"• إجمالي الخطوات: {operation['total_steps']}\n"
                completion_text += f"• الوقت المستغرق: {total_time:.1f} ثانية\n"
                completion_text += f"• متوسط الوقت لكل خطوة: {total_time/operation['total_steps']:.1f} ثانية"
            
            # تحديث الرسالة النهائية
            await operation['message'].edit_text(
                completion_text,
                parse_mode='Markdown',
                reply_markup=final_keyboard
            )
            
            # إزالة العملية من القائمة النشطة
            del self.active_operations[operation_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to complete progress for {operation_id}: {e}")
            return False
    
    async def fail_progress(self, operation_id: str, 
                          error_message: str = "فشلت العملية ❌",
                          retry_keyboard: InlineKeyboardMarkup = None) -> bool:
        """إظهار فشل العملية"""
        if operation_id not in self.active_operations:
            return False
        
        operation = self.active_operations[operation_id]
        
        try:
            total_time = time.time() - operation['start_time']
            
            # إنشاء رسالة الفشل
            failure_text = f"❌ **{error_message}**\n\n"
            failure_text += f"📊 **تفاصيل العملية:**\n"
            failure_text += f"• العملية: {operation['operation_name']}\n"
            failure_text += f"• توقفت في الخطوة: {operation['current_step']} من {operation['total_steps']}\n"
            failure_text += f"• الوقت المستغرق: {total_time:.1f} ثانية\n\n"
            failure_text += "💡 يمكنك المحاولة مرة أخرى أو التواصل مع الدعم الفني."
            
            # تحديث الرسالة
            await operation['message'].edit_text(
                failure_text,
                parse_mode='Markdown',
                reply_markup=retry_keyboard
            )
            
            # إزالة العملية من القائمة النشطة
            del self.active_operations[operation_id]
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to show failure for {operation_id}: {e}")
            return False
    
    def _create_progress_bar(self, current: int, total: int, length: int = 10) -> str:
        """إنشاء شريط تقدم نصي"""
        if total == 0:
            return "▓" * length
        
        filled_length = int(length * current / total)
        bar = "▓" * filled_length + "░" * (length - filled_length)
        return f"[{bar}]"
    
    def get_active_operations_count(self) -> int:
        """الحصول على عدد العمليات النشطة"""
        return len(self.active_operations)
    
    def get_active_operations(self) -> Dict[str, Dict]:
        """الحصول على قائمة العمليات النشطة"""
        return {
            op_id: {
                'operation_name': op['operation_name'],
                'current_step': op['current_step'],
                'total_steps': op['total_steps'],
                'elapsed_time': time.time() - op['start_time']
            }
            for op_id, op in self.active_operations.items()
        }

class AsyncProgressManager:
    """مدير التقدم للعمليات غير المتزامنة"""
    
    def __init__(self):
        self.progress_indicator = ProgressIndicator()
    
    async def run_with_progress(self, update: Update, context: CallbackContext,
                              operation_func: Callable, operation_name: str,
                              steps: List[str], *args, **kwargs) -> Any:
        """تشغيل دالة مع مؤشر تقدم"""
        total_steps = len(steps)
        
        # بدء مؤشر التقدم
        operation_id = await self.progress_indicator.show_progress(
            update, context, operation_name, total_steps,
            f"بدء {operation_name}..."
        )
        
        if not operation_id:
            # فشل في إنشاء مؤشر التقدم، تشغيل العملية بدونه
            return await operation_func(*args, **kwargs)
        
        try:
            result = None
            
            # تنفيذ كل خطوة
            for i, step_description in enumerate(steps, 1):
                await self.progress_indicator.update_progress(
                    operation_id, i, step_description
                )
                
                # إعطاء وقت للمستخدم لرؤية التحديث
                await asyncio.sleep(0.5)
                
                # تنفيذ جزء من العملية (إذا كانت قابلة للتقسيم)
                if i == total_steps:
                    # الخطوة الأخيرة - تنفيذ العملية الفعلية
                    result = await operation_func(*args, **kwargs)
            
            # إكمال مؤشر التقدم
            await self.progress_indicator.complete_progress(
                operation_id, f"تم إكمال {operation_name} بنجاح!"
            )
            
            return result
            
        except Exception as e:
            # إظهار فشل العملية
            await self.progress_indicator.fail_progress(
                operation_id, f"فشل في {operation_name}: {str(e)}"
            )
            raise
    
    async def file_upload_progress(self, update: Update, context: CallbackContext,
                                 file_size: int, operation_name: str = "رفع الملف") -> str:
        """مؤشر تقدم خاص برفع الملفات"""
        steps = [
            "التحقق من الملف...",
            "بدء الرفع...",
            "رفع البيانات...",
            "التحقق من سلامة البيانات...",
            "حفظ الملف..."
        ]
        
        operation_id = await self.progress_indicator.show_progress(
            update, context, operation_name, len(steps)
        )
        
        return operation_id
    
    async def database_operation_progress(self, update: Update, context: CallbackContext,
                                        operation_count: int, 
                                        operation_name: str = "معالجة البيانات") -> str:
        """مؤشر تقدم لعمليات قاعدة البيانات"""
        steps = [
            "الاتصال بقاعدة البيانات...",
            "التحقق من البيانات...",
            "تنفيذ العمليات...",
            "التحقق من النتائج...",
            "حفظ التغييرات..."
        ]
        
        if operation_count > 100:
            steps.insert(3, "معالجة البيانات الكبيرة...")
        
        operation_id = await self.progress_indicator.show_progress(
            update, context, operation_name, len(steps)
        )
        
        return operation_id

# إنشاء مثيل عام للاستخدام
progress_manager = AsyncProgressManager()
progress_indicator = ProgressIndicator()

# دوال مساعدة للاستخدام السريع
async def show_processing_message(update: Update, context: CallbackContext,
                                message: str = "جاري المعالجة...") -> Optional[Any]:
    """عرض رسالة معالجة بسيطة"""
    try:
        if hasattr(update, 'callback_query') and update.callback_query:
            return await update.callback_query.edit_message_text(
                f"⏳ {message}",
                parse_mode='Markdown'
            )
        else:
            return await update.message.reply_text(
                f"⏳ {message}",
                parse_mode='Markdown'
            )
    except Exception as e:
        logger.error(f"Failed to show processing message: {e}")
        return None

async def show_success_message(message_obj, success_text: str = "تمت العملية بنجاح!",
                             keyboard: InlineKeyboardMarkup = None):
    """عرض رسالة نجاح"""
    try:
        await message_obj.edit_text(
            f"✅ {success_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Failed to show success message: {e}")

async def show_error_message(message_obj, error_text: str = "حدث خطأ أثناء المعالجة",
                           keyboard: InlineKeyboardMarkup = None):
    """عرض رسالة خطأ"""
    try:
        await message_obj.edit_text(
            f"❌ {error_text}",
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except Exception as e:
        logger.error(f"Failed to show error message: {e}")