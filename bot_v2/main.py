#!/usr/bin/env python3
"""
Yemen Net Bot - Main Entry Point
Advanced Telegram Bot for Network Card Sales

Version: 3.0.0
Author: Yemen Net Bot Development Team
License: MIT
"""

import asyncio
import signal
import sys
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Core imports with specific exception handling
try:
    from telegram import Update, MenuButtonCommands
    from telegram.ext import Application, PicklePersistence
    from telegram.error import NetworkError, InvalidToken, TimedOut
except ImportError as e:
    print(f"Failed to import Telegram libraries: {e}")
    print("Please install python-telegram-bot: pip install python-telegram-bot")
    sys.exit(1)

# Internal imports with specific exception handling
try:
    from bot_v2.core.logger import logger, BotLogger
    from bot_v2.core.exceptions import (
        EmergencyShutdownException, 
        ConfigurationException,
        DatabaseException
    )
    from bot_v2.config.settings import settings, TELEGRAM_CONFIG, BOT_CONFIG
    from bot_v2.services.database_service import db_service
    from bot_v2.services.rate_limiter import rate_limiter
    from bot_v2.handlers.bot_handlers import setup_handlers
    from bot_v2.utils.validators import validate_environment
    from bot_v2.core.monitoring import HealthMonitor
except ImportError as e:
    print(f"Failed to import bot modules: {e}")
    print("Please ensure all bot modules are properly installed")
    sys.exit(1)


class YemenNetBot:
    """Main bot class with comprehensive error handling and monitoring"""
    
    def __init__(self):
        self.application: Optional[Application] = None
        self.health_monitor: Optional[HealthMonitor] = None
        self.shutdown_requested = False
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
        
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown_requested = True
        
    async def initialize(self) -> bool:
        """Initialize bot components with comprehensive error handling"""
        try:
            logger.info("Starting Yemen Net Bot initialization...")
            
            # Validate environment and configuration
            await self._validate_environment()
            
            # Initialize database service
            await self._initialize_database()
            
            # Initialize Telegram application
            await self._initialize_telegram()
            
            # Setup health monitoring
            await self._initialize_monitoring()
            
            logger.info("Bot initialization completed successfully")
            return True
            
        except ConfigurationException as e:
            logger.critical("Configuration error during initialization", e)
            return False
        except DatabaseException as e:
            logger.critical("Database error during initialization", e)
            return False
        except NetworkError as e:
            logger.critical("Network error during initialization", e)
            return False
        except Exception as e:
            logger.critical("Unexpected error during initialization", e)
            return False
            
    async def _validate_environment(self):
        """Validate environment and configuration"""
        try:
            # Validate configuration
            config_summary = settings.get_summary()
            logger.info(f"Configuration loaded: {config_summary}")
            
            if not config_summary.get('telegram_configured'):
                raise ConfigurationException("Telegram bot token not configured")
                
            # Validate environment setup
            validation_result = validate_environment()
            if not validation_result.get('valid', False):
                raise ConfigurationException(f"Environment validation failed: {validation_result.get('errors', [])}")
                
            logger.info("Environment validation passed")
            
        except Exception as e:
            logger.error("Environment validation failed", e)
            raise ConfigurationException(f"Environment validation error: {e}")
            
    async def _initialize_database(self):
        """Initialize database with proper error handling"""
        try:
            logger.info("Initializing database service...")
            
            # Test database connection
            health_check = db_service.health_check()
            if health_check.get('status') != 'healthy':
                raise DatabaseException(f"Database health check failed: {health_check.get('error')}")
                
            logger.info(f"Database initialized successfully: {health_check}")
            
        except Exception as e:
            logger.error("Database initialization failed", e)
            raise DatabaseException(f"Database initialization error: {e}")
            
    async def _initialize_telegram(self):
        """Initialize Telegram application with error handling"""
        try:
            logger.info("Initializing Telegram application...")
            
            # Setup persistence
            persistence = PicklePersistence(filepath="bot_data.pickle")
            
            # Create application
            self.application = (
                Application.builder()
                .token(TELEGRAM_CONFIG.token)
                .persistence(persistence)
                .build()
            )
            
            # Test token validity
            try:
                bot_info = await self.application.bot.get_me()
                logger.info(f"Bot authenticated successfully: @{bot_info.username}")
            except InvalidToken as e:
                raise ConfigurationException("Invalid Telegram bot token")
            except NetworkError as e:
                raise NetworkError("Failed to connect to Telegram API")
                
            # Setup handlers
            setup_handlers(self.application)
            
            # Set bot menu button
            await self.application.bot.set_menu_button(
                menu_button=MenuButtonCommands()
            )
            
            logger.info("Telegram application initialized successfully")
            
        except Exception as e:
            logger.error("Telegram initialization failed", e)
            raise
            
    async def _initialize_monitoring(self):
        """Initialize health monitoring"""
        try:
            if BOT_CONFIG.features_enabled.get('monitoring', True):
                from bot_v2.core.monitoring import HealthMonitor
                self.health_monitor = HealthMonitor(
                    db_service=db_service,
                    rate_limiter=rate_limiter,
                    application=self.application
                )
                await self.health_monitor.start()
                logger.info("Health monitoring initialized")
            else:
                logger.info("Health monitoring disabled in configuration")
                
        except Exception as e:
            logger.warning("Failed to initialize health monitoring", e)
            # Don't fail initialization if monitoring fails
            
    async def start(self):
        """Start the bot with comprehensive error handling"""
        try:
            if not self.application:
                raise RuntimeError("Bot not initialized. Call initialize() first.")
                
            logger.info("Starting Yemen Net Bot...")
            
            # Start polling
            await self.application.initialize()
            await self.application.start()
            
            if BOT_CONFIG.debug:
                logger.info("Bot started in debug mode")
            else:
                logger.info("Bot started in production mode")
                
            # Start polling with error handling
            try:
                await self.application.updater.start_polling(
                    drop_pending_updates=True,
                    allowed_updates=Update.ALL_TYPES
                )
                
                logger.info("Bot is now polling for updates...")
                
                # Keep running until shutdown is requested
                while not self.shutdown_requested:
                    await asyncio.sleep(1)
                    
            except NetworkError as e:
                logger.error("Network error during polling", e)
                await self._handle_network_error(e)
            except TimedOut as e:
                logger.warning("Telegram API timeout", e)
                await self._handle_timeout_error(e)
            except Exception as e:
                logger.error("Unexpected error during polling", e)
                raise
                
        except EmergencyShutdownException as e:
            logger.critical("Emergency shutdown triggered", e)
            await self._emergency_shutdown(str(e))
        except Exception as e:
            logger.critical("Critical error in bot operation", e)
            await self._emergency_shutdown(f"Critical error: {e}")
        finally:
            await self.shutdown()
            
    async def _handle_network_error(self, error: NetworkError):
        """Handle network errors with retry logic"""
        logger.warning(f"Network error occurred: {error}")
        
        # Wait before retrying
        await asyncio.sleep(5)
        
        # Check if we should continue or shutdown
        if self.shutdown_requested:
            return
            
        # Log and continue
        logger.info("Attempting to continue after network error...")
        
    async def _handle_timeout_error(self, error: TimedOut):
        """Handle timeout errors"""
        logger.warning(f"Timeout error: {error}")
        # Timeouts are usually temporary, just continue
        
    async def _emergency_shutdown(self, reason: str):
        """Perform emergency shutdown"""
        logger.critical(f"Performing emergency shutdown: {reason}")
        
        try:
            # Stop all services quickly
            if self.application:
                await self.application.stop()
                
            if self.health_monitor:
                await self.health_monitor.stop()
                
            # Cleanup database
            db_service.cleanup()
            
            logger.critical("Emergency shutdown completed")
            
        except Exception as e:
            logger.critical("Error during emergency shutdown", e)
        finally:
            sys.exit(1)
            
    async def shutdown(self):
        """Graceful shutdown of all bot components"""
        try:
            logger.info("Starting graceful shutdown...")
            
            # Stop Telegram application
            if self.application:
                logger.info("Stopping Telegram application...")
                await self.application.updater.stop()
                await self.application.stop()
                await self.application.shutdown()
                
            # Stop health monitoring
            if self.health_monitor:
                logger.info("Stopping health monitor...")
                await self.health_monitor.stop()
                
            # Cleanup database service
            logger.info("Cleaning up database service...")
            db_service.cleanup()
            
            # Final log flush
            logger.info("Graceful shutdown completed")
            
        except Exception as e:
            logger.error("Error during graceful shutdown", e)
            
    async def restart(self):
        """Restart the bot"""
        logger.info("Restarting bot...")
        await self.shutdown()
        await asyncio.sleep(2)
        await self.initialize()
        await self.start()


async def main():
    """Main entry point"""
    bot = None
    
    try:
        # Create bot instance
        bot = YemenNetBot()
        
        # Initialize bot
        if not await bot.initialize():
            logger.critical("Bot initialization failed")
            sys.exit(1)
            
        # Start bot
        await bot.start()
        
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.critical("Fatal error in main", e)
        sys.exit(1)
    finally:
        if bot:
            await bot.shutdown()


if __name__ == "__main__":
    try:
        # Set event loop policy for Windows compatibility
        if sys.platform == "win32":
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            
        # Run the bot
        asyncio.run(main())
        
    except Exception as e:
        print(f"Failed to start bot: {e}")
        sys.exit(1)