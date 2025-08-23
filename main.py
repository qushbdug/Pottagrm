#!/usr/bin/env python3
"""
Yemen Net Bot - Main Entry Point
Main bot application with modular structure
"""

import asyncio
import sys
import os
from yemen_net_bot import YemenNetBot

def main():
    """Main function to start the bot"""
    try:
        # Create and start the bot
        bot = YemenNetBot()
        bot.start()
    except KeyboardInterrupt:
        print("\nBot stopped by user")
    except Exception as e:
        print(f"Error starting bot: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()