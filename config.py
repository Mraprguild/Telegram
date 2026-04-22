import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Telegram Configuration
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHANNEL_ID = os.getenv("TELEGRAM_CHANNEL_ID")

# TMDB Configuration
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

# Website Configuration
WEBSITE_FEED_URL = os.getenv("WEBSITE_FEED_URL", "https://ottguild.online/feed/")

# Bot Configuration
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", "600"))  # 10 minutes
SENT_MOVIES_FILE = os.getenv("SENT_MOVIES_FILE", "data/sent_movies.txt")
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "3"))
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "15"))

# Status API Configuration
STATUS_API_HOST = os.getenv("STATUS_API_HOST", "0.0.0.0")
STATUS_API_PORT = int(os.getenv("STATUS_API_PORT", "8000"))
ENABLE_STATUS_API = os.getenv("ENABLE_STATUS_API", "true").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
LOG_FILE = os.getenv("LOG_FILE", "logs/bot.log")

# Validation
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables")
if not TELEGRAM_CHANNEL_ID:
    raise ValueError("TELEGRAM_CHANNEL_ID is not set in environment variables")
if not TMDB_API_KEY:
    raise ValueError("TMDB_API_KEY is not set in environment variables")

# Create necessary directories
def create_directories():
    """Create required directories if they don't exist"""
    directories = [
        os.path.dirname(SENT_MOVIES_FILE) if os.path.dirname(SENT_MOVIES_FILE) else "data",
        "logs",
        "data"
    ]
    
    for directory in directories:
        if directory and not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
            print(f"Created directory: {directory}")

# Create directories on import
create_directories()

# Optional: Configure logging based on LOG_LEVEL
import logging

logging_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)

# Additional helper functions
def get_config_summary() -> dict:
    """Return a summary of current configuration (excluding sensitive data)"""
    return {
        "telegram_channel": TELEGRAM_CHANNEL_ID,
        "feed_url": WEBSITE_FEED_URL,
        "check_interval": CHECK_INTERVAL,
        "sent_movies_file": SENT_MOVIES_FILE,
        "max_retries": MAX_RETRIES,
        "request_timeout": REQUEST_TIMEOUT,
        "status_api_enabled": ENABLE_STATUS_API,
        "status_api_host": STATUS_API_HOST,
        "status_api_port": STATUS_API_PORT,
        "log_level": LOG_LEVEL,
        "log_file": LOG_FILE
    }

def validate_config():
    """Validate all configuration settings"""
    errors = []
    
    # Validate CHECK_INTERVAL
    if CHECK_INTERVAL < 60:
        errors.append("CHECK_INTERVAL should be at least 60 seconds")
    
    # Validate MAX_RETRIES
    if MAX_RETRIES < 1 or MAX_RETRIES > 10:
        errors.append("MAX_RETRIES should be between 1 and 10")
    
    # Validate REQUEST_TIMEOUT
    if REQUEST_TIMEOUT < 5 or REQUEST_TIMEOUT > 60:
        errors.append("REQUEST_TIMEOUT should be between 5 and 60 seconds")
    
    # Validate STATUS_API_PORT
    if STATUS_API_PORT < 1024 or STATUS_API_PORT > 65535:
        errors.append("STATUS_API_PORT should be between 1024 and 65535")
    
    # Validate TELEGRAM_CHANNEL_ID format
    if TELEGRAM_CHANNEL_ID and not TELEGRAM_CHANNEL_ID.startswith("@"):
        errors.append("TELEGRAM_CHANNEL_ID should start with '@'")
    
    if errors:
        error_message = "Configuration errors:\n" + "\n".join(errors)
        raise ValueError(error_message)
    
    return True

# Run validation
if __name__ != "__main__":
    try:
        validate_config()
    except ValueError as e:
        print(f"Configuration warning: {e}")

# Export all variables
__all__ = [
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHANNEL_ID",
    "TMDB_API_KEY",
    "WEBSITE_FEED_URL",
    "CHECK_INTERVAL",
    "SENT_MOVIES_FILE",
    "MAX_RETRIES",
    "REQUEST_TIMEOUT",
    "STATUS_API_HOST",
    "STATUS_API_PORT",
    "ENABLE_STATUS_API",
    "LOG_LEVEL",
    "LOG_FORMAT",
    "LOG_FILE",
    "get_config_summary",
    "validate_config"
]
