#!/usr/bin/env python3
"""
Main entry point for Yemen Net Bot v2
Enhanced version with modern architecture and improved performance
"""

import asyncio
import logging
import sys
import os
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Import bot components
from bot_v2.core.bot_core import create_bot
from bot_v2.config.settings import BOT_TOKEN, ENVIRONMENT, DEBUG
from bot_v2.core.exceptions import BotError, ConfigurationError

# Setup logging
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot_v2.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Main bot function"""
    try:
        logger.info("🚀 Starting Yemen Net Bot v2...")
        logger.info(f"🌍 Environment: {ENVIRONMENT}")
        logger.info(f"🐛 Debug mode: {DEBUG}")
        
        # Validate bot token
        if not BOT_TOKEN:
            logger.error("❌ BOT_TOKEN is not set. Please set it in environment variables or config.")
            sys.exit(1)
        
        # Create bot instance
        logger.info("🔧 Creating bot instance...")
        bot = create_bot(BOT_TOKEN)
        
        # Start bot
        logger.info("▶️ Starting bot...")
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Received interrupt signal, shutting down...")
    except BotError as e:
        logger.error(f"❌ Bot error: {e}")
        sys.exit(1)
    except ConfigurationError as e:
        logger.error(f"❌ Configuration error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)
    finally:
        logger.info("🔄 Bot shutdown completed")

def run_bot():
    """Run bot with proper error handling"""
    try:
        # Check Python version
        if sys.version_info < (3, 8):
            logger.error("❌ Python 3.8 or higher is required")
            sys.exit(1)
        
        # Check if running in virtual environment (recommended)
        if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
            logger.warning("⚠️  Running outside virtual environment. Consider using a virtual environment.")
        
        # Run bot
        asyncio.run(main())
        
    except KeyboardInterrupt:
        logger.info("⏹️ Interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"❌ Failed to run bot: {e}")
        logger.exception("Full traceback:")
        sys.exit(1)

if __name__ == "__main__":
    run_bot()