#!/usr/bin/env python3
"""
Simple Bot Runner - تشغيل البوت بطريقة مبسطة
"""

import sys
import os
import asyncio
import logging
from datetime import datetime

# Add bot_modules to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'bot_modules'))

def setup_logging():
    """إعداد نظام السجلات"""
    logging.basicConfig(
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level=logging.INFO,
        handlers=[
            logging.FileHandler(f'bot_simple_{datetime.now().strftime("%Y%m%d")}.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

async def main():
    """الدالة الرئيسية"""
    logger = setup_logging()
    
    print("🤖 تشغيل البوت - Yemen Net Bot")
    print("=" * 40)
    
    try:
        # Test imports
        logger.info("Testing imports...")
        from config import BOT_TOKEN
        from database import init_db
        from yemen_net_bot_new import main as bot_main
        
        # Verify token
        if not BOT_TOKEN or len(BOT_TOKEN) < 40:
            raise ValueError("Invalid bot token")
        
        logger.info(f"Token verified: {BOT_TOKEN[:10]}...{BOT_TOKEN[-10:]}")
        
        # Initialize database
        logger.info("Initializing database...")
        init_db()
        
        # Start bot
        logger.info("🚀 Starting bot...")
        print("✅ البوت يعمل الآن...")
        print("اضغط Ctrl+C لإيقاف البوت")
        
        await bot_main()
        
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        print("\n👋 تم إيقاف البوت")
    except Exception as e:
        logger.error(f"Bot error: {e}")
        print(f"❌ خطأ في البوت: {e}")
        raise

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 تم إيقاف البوت")
    except Exception as e:
        print(f"❌ خطأ فادح: {e}")
        sys.exit(1)