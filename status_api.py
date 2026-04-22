from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Dict, Any, Optional
import asyncio
import logging
from datetime import datetime, timedelta
import os
import json
import requests

logger = logging.getLogger(__name__)

class BotStatus(BaseModel):
    status: str
    last_check: Optional[str] = None
    total_movies_posted: int
    uptime_seconds: float
    uptime_formatted: str
    telegram_connected: bool
    tmdb_connected: bool
    rss_feed_connected: bool
    next_check_seconds: Optional[int] = None
    check_interval: int

class StatusAPI:
    def __init__(self):
        self.start_time = datetime.now()
        self.last_check_time = None
        self.total_movies_posted = 0
        self.telegram_status = False
        self.tmdb_status = False
        self.rss_status = False
        self.check_interval = 600  # Default, will be updated from config
        self.sent_movies_file = "data/sent_movies.txt"
        
    def update_bot_stats(self, last_check: datetime = None, movies_found: int = 0):
        """Update bot statistics"""
        if last_check:
            self.last_check_time = last_check
        if movies_found > 0:
            self.total_movies_posted += movies_found
            
    def update_connection_status(self, telegram: bool = None, tmdb: bool = None, rss: bool = None):
        """Update connection status for various services"""
        if telegram is not None:
            self.telegram_status = telegram
        if tmdb is not None:
            self.tmdb_status = tmdb
        if rss is not None:
            self.rss_status = rss
            
    def update_check_interval(self, interval: int):
        """Update check interval"""
        self.check_interval = interval
            
    def get_sent_movies_count(self) -> int:
        """Get total number of posted movies from file"""
        try:
            if os.path.exists(self.sent_movies_file):
                with open(self.sent_movies_file, "r") as f:
                    return sum(1 for line in f if line.strip())
            return 0
        except Exception as e:
            logger.error(f"Error reading sent movies count: {e}")
            return 0
    
    def get_uptime_formatted(self, seconds: float) -> str:
        """Format uptime in human readable format"""
        days = int(seconds // 86400)
        hours = int((seconds % 86400) // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds = int(seconds % 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)
    
    def get_status(self) -> BotStatus:
        """Get current bot status"""
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        # Get actual count from file
        actual_count = self.get_sent_movies_count()
        if actual_count > self.total_movies_posted:
            self.total_movies_posted = actual_count
            
        # Calculate next check
        next_check = None
        if self.last_check_time:
            elapsed = (datetime.now() - self.last_check_time).total_seconds()
            if elapsed < self.check_interval:
                next_check = int(self.check_interval - elapsed)
            else:
                next_check = 0
        
        return BotStatus(
            status="running",
            last_check=self.last_check_time.isoformat() if self.last_check_time else None,
            total_movies_posted=self.total_movies_posted,
            uptime_seconds=uptime,
            uptime_formatted=self.get_uptime_formatted(uptime),
            telegram_connected=self.telegram_status,
            tmdb_connected=self.tmdb_status,
            rss_feed_connected=self.rss_status,
            next_check_seconds=next_check,
            check_interval=self.check_interval
        )

# Create FastAPI app
app = FastAPI(title="Movie Bot Status API", version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global status instance
status_api = StatusAPI()

@app.get("/", response_model=Dict[str, str])
async def root():
    """Root endpoint"""
    return {
        "message": "Movie Bot Status API",
        "version": "1.0.0",
        "endpoints": "/status, /health, /metrics"
    }

@app.get("/health", response_model=Dict[str, str])
async def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/status", response_model=BotStatus)
async def get_bot_status():
    """Get detailed bot status"""
    return status_api.get_status()

@app.get("/metrics", response_model=Dict[str, Any])
async def get_metrics():
    """Get metrics for monitoring"""
    status = status_api.get_status()
    return {
        "total_movies_posted": status.total_movies_posted,
        "uptime_seconds": status.uptime_seconds,
        "telegram_connected": status.telegram_connected,
        "tmdb_connected": status.tmdb_connected,
        "rss_feed_connected": status.rss_feed_connected,
        "last_check": status.last_check,
        "next_check_seconds": status.next_check_seconds
    }

def run_status_api(host: str = "0.0.0.0", port: int = 8000):
    """Run the status API server"""
    import uvicorn
    uvicorn.run(app, host=host, port=port, log_level="info")
