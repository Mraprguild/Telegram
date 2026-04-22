# OTT Guild Movie Bot

A Telegram bot that monitors OTT Guild website and automatically posts new movies/TV shows with TMDB details.

## Features

- Monitors RSS feed for new content
- Fetches detailed movie/TV show information from TMDB
- Posts formatted messages with posters to Telegram channel
- Prevents duplicate posts
- Docker support for easy deployment
- Automatic retry on failures
- Comprehensive logging
- **Status API on port 8000** for monitoring

## Status API Endpoints

Once the bot is running, you can access the status API:

- `GET http://localhost:8000/` - API information
- `GET http://localhost:8000/health` - Simple health check
- `GET http://localhost:8000/status` - Detailed bot status including:
  - Total movies posted
  - Uptime
  - Connection status for Telegram, TMDB, and RSS feed
  - Last check time
  - Next check in seconds
- `GET http://localhost:8000/metrics` - Metrics for monitoring systems

## Prerequisites

- Python 3.11+
- Telegram Bot Token (from @BotFather)
- TMDB API Key (from themoviedb.org)
- Docker (optional)

## Installation

### Local Setup

1. Clone the repository:
```bash
git clone <your-repo-url>
cd telegram-bot
