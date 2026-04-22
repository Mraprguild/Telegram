#!/usr/bin/env python3
"""
Entry point to run both the bot and status API server
"""
import asyncio
import threading
import logging
import sys
from status_api import run_status_api, status_api
from bot import MovieBot

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def run_bot():
    """Run the bot in a separate thread"""
    asyncio.run(run_bot_async())

async def run_bot_async():
    """Async bot runner"""
    bot = MovieBot(status_api=status_api)
    await bot.run()

def main():
    """Main entry point"""
    logger.info("Starting Movie Bot with Status API...")
    
    # Start status API in a separate thread
    api_thread = threading.Thread(
        target=run_status_api,
        kwargs={"host": "0.0.0.0", "port": 8000},
        daemon=True
    )
    api_thread.start()
    logger.info("Status API started on port 8000")
    
    # Run the bot in the main thread
    try:
        run_bot()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        sys.exit(0)

if __name__ == "__main__":
    main()
