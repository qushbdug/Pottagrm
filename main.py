#!/usr/bin/env python3
"""
Yemen Net Bot - Main Entry Point
بوت شبكات اليمن - نقطة الدخول الرئيسية

A professional Telegram bot for network card sales in Yemen
بوت تيليجرام احترافي لبيع كروت الشبكات في اليمن

Author: Professional Development Team
المؤلف: فريق التطوير المحترف
Version: 3.0.0
License: MIT
"""

import asyncio
import logging
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from bot import YemenNetBot


async def main():
    """
    Main entry point for the Yemen Net Bot.
    نقطة الدخول الرئيسية لبوت شبكات اليمن.
    """
    try:
        # Create and start the bot
        bot = YemenNetBot()
        
        logging.info("🚀 Starting Yemen Net Bot...")
        logging.info("🌟 Professional Edition v3.0.0")
        logging.info("🇾🇪 Made with ❤️ for Yemen")
        
        await bot.start()
        
    except KeyboardInterrupt:
        logging.info("⚠️ Bot stopped by user (Ctrl+C)")
        await bot.stop()
        
    except Exception as e:
        logging.error(f"❌ Fatal error: {e}")
        if 'bot' in locals():
            await bot.stop()
        sys.exit(1)


if __name__ == "__main__":
    # Configure basic logging for startup
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('startup.log', encoding='utf-8')
        ]
    )
    
    try:
        # Run the bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logging.info("👋 Bot stopped by user")
        
    except Exception as e:
        logging.error(f"💥 Unexpected error: {e}")
        sys.exit(1)