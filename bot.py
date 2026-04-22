import asyncio
import logging
import re
from datetime import datetime
from typing import Optional, Dict, Any
import threading

import feedparser
import requests
from telegram import Bot
from telegram.constants import ParseMode
from telegram.error import TelegramError
from tenacity import retry, stop_after_attempt, wait_exponential

from config import (
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHANNEL_ID,
    TMDB_API_KEY,
    WEBSITE_FEED_URL,
    CHECK_INTERVAL,
    SENT_MOVIES_FILE,
    MAX_RETRIES,
    REQUEST_TIMEOUT
)

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

class MovieBot:
    def __init__(self, status_api=None):
        self.bot = Bot(token=TELEGRAM_BOT_TOKEN)
        self.sent_movies = self.load_sent_movies()
        self.status_api = status_api
        
    def load_sent_movies(self) -> set:
        """Load already posted movie URLs from file"""
        try:
            with open(SENT_MOVIES_FILE, "r") as f:
                return set(line.strip() for line in f if line.strip())
        except FileNotFoundError:
            logger.info(f"Created new sent movies file: {SENT_MOVIES_FILE}")
            return set()
        except Exception as e:
            logger.error(f"Error loading sent movies: {e}")
            return set()
    
    def save_sent_movie(self, movie_url: str):
        """Save posted movie URL to file"""
        try:
            with open(SENT_MOVIES_FILE, "a") as f:
                f.write(f"{movie_url}\n")
            self.sent_movies.add(movie_url)
        except Exception as e:
            logger.error(f"Error saving sent movie: {e}")
    
    def clean_title(self, title: str) -> str:
        """Clean movie title for better TMDB search"""
        # Remove common suffixes
        title = title.split("(")[0]
        title = title.split("[")[0]
        title = re.sub(r'(Download|Watch|Free|4K|HD|BluRay|WEB-DL|HDRip|BRRip)', '', title, flags=re.IGNORECASE)
        title = re.sub(r'[\(\{\[].*?[\)\}\]]', '', title)
        title = ' '.join(title.split())
        return title.strip()
    
    def test_telegram_connection(self) -> bool:
        """Test Telegram connection"""
        try:
            # Try to get bot info
            bot_info = self.bot.get_me()
            logger.info(f"Telegram connection successful: @{bot_info.username}")
            return True
        except Exception as e:
            logger.error(f"Telegram connection failed: {e}")
            return False
    
    def test_tmdb_connection(self) -> bool:
        """Test TMDB connection"""
        try:
            test_url = "https://api.themoviedb.org/3/configuration"
            params = {"api_key": TMDB_API_KEY}
            response = requests.get(test_url, params=params, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                logger.info("TMDB connection successful")
                return True
            else:
                logger.error(f"TMDB connection failed with status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"TMDB connection failed: {e}")
            return False
    
    def test_rss_connection(self) -> bool:
        """Test RSS feed connection"""
        try:
            feed = feedparser.parse(WEBSITE_FEED_URL)
            if feed.entries:
                logger.info(f"RSS feed connection successful, found {len(feed.entries)} entries")
                return True
            else:
                logger.warning("RSS feed connection successful but no entries found")
                return True  # Still consider it connected
        except Exception as e:
            logger.error(f"RSS feed connection failed: {e}")
            return False
    
    def update_status_api(self, movies_found: int = 0):
        """Update status API with current statistics"""
        if self.status_api:
            self.status_api.update_bot_stats(
                last_check=datetime.now(),
                movies_found=movies_found
            )
            
            # Test connections periodically
            telegram_ok = self.test_telegram_connection()
            tmdb_ok = self.test_tmdb_connection()
            rss_ok = self.test_rss_connection()
            
            self.status_api.update_connection_status(
                telegram=telegram_ok,
                tmdb=tmdb_ok,
                rss=rss_ok
            )
            
            self.status_api.update_check_interval(CHECK_INTERVAL)
    
    @retry(stop=stop_after_attempt(MAX_RETRIES), wait=wait_exponential(multiplier=1, min=2, max=10))
    def fetch_tmdb_details(self, title: str) -> Optional[Dict[str, Any]]:
        """Fetch movie/TV show details from TMDB API"""
        clean_title = self.clean_title(title)
        logger.info(f"Searching TMDB for: {clean_title}")
        
        # Search for movie or TV show
        search_url = "https://api.themoviedb.org/3/search/multi"
        params = {
            "api_key": TMDB_API_KEY,
            "query": clean_title,
            "language": "en-US",
            "page": 1
        }
        
        try:
            response = requests.get(search_url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            
            if not data.get("results"):
                logger.warning(f"No results found for: {clean_title}")
                return None
            
            # Get the first result
            result = data["results"][0]
            media_type = result.get("media_type", "movie")
            item_id = result["id"]
            
            # Fetch detailed information
            details_url = f"https://api.themoviedb.org/3/{media_type}/{item_id}"
            params_details = {
                "api_key": TMDB_API_KEY,
                "language": "en-US",
                "append_to_response": "credits,videos"
            }
            
            details = requests.get(details_url, params=params_details, timeout=REQUEST_TIMEOUT)
            details.raise_for_status()
            details_data = details.json()
            
            # Extract video trailer if available
            trailer_key = None
            if details_data.get("videos", {}).get("results"):
                for video in details_data["videos"]["results"]:
                    if video.get("type") == "Trailer" and video.get("site") == "YouTube":
                        trailer_key = video.get("key")
                        break
            
            # Extract director
            director = "Unknown"
            if details_data.get("credits", {}).get("crew"):
                for crew in details_data["credits"]["crew"]:
                    if crew.get("job") == "Director":
                        director = crew.get("name")
                        break
            
            # Prepare movie data
            movie_data = {
                "title": details_data.get("title") or details_data.get("name"),
                "overview": details_data.get("overview", "No description available."),
                "rating": details_data.get("vote_average", 0),
                "vote_count": details_data.get("vote_count", 0),
                "poster_path": f"https://image.tmdb.org/t/p/w500{details_data.get('poster_path')}" if details_data.get('poster_path') else None,
                "backdrop_path": f"https://image.tmdb.org/t/p/original{details_data.get('backdrop_path')}" if details_data.get('backdrop_path') else None,
                "release_date": details_data.get("release_date") or details_data.get("first_air_date"),
                "genres": ", ".join([g["name"] for g in details_data.get("genres", [])]),
                "runtime": details_data.get("runtime") or details_data.get("episode_run_time", [0])[0],
                "director": director,
                "trailer_key": trailer_key,
                "media_type": media_type,
                "imdb_id": details_data.get("imdb_id"),
                "homepage": details_data.get("homepage")
            }
            
            logger.info(f"Successfully fetched TMDB data for: {movie_data['title']}")
            return movie_data
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching TMDB data for: {clean_title}")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error fetching TMDB data: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error fetching TMDB data: {e}")
            return None
    
    def format_telegram_message(self, movie_data: Dict[str, Any], original_url: str) -> str:
        """Format the message for Telegram"""
        media_icon = "🎬" if movie_data["media_type"] == "movie" else "📺"
        
        # Rating stars
        rating = movie_data["rating"]
        stars = "⭐" * min(5, int(rating / 2)) if rating > 0 else "Not rated"
        
        # Runtime formatting
        runtime = ""
        if movie_data.get("runtime") and movie_data["runtime"] > 0:
            hours = movie_data["runtime"] // 60
            minutes = movie_data["runtime"] % 60
            runtime = f"⏱️ *Duration:* {hours}h {minutes}m\n"
        
        # Trailer link
        trailer = ""
        if movie_data.get("trailer_key"):
            trailer = f"🎥 [Watch Trailer](https://youtube.com/watch?v={movie_data['trailer_key']})\n"
        
        # Format message
        message = f"""
{media_icon} *{movie_data['title']}* 

{stars} *Rating:* {rating}/10 ({movie_data['vote_count']} votes)

📅 *Released:* {movie_data['release_date'] or 'Unknown'}
🎭 *Genres:* {movie_data['genres'] or 'N/A'}
{runtime}👨 *Director:* {movie_data['director']}

📖 *Storyline:*
{movie_data['overview'][:400]}{'...' if len(movie_data['overview']) > 400 else ''}

{trailer}🔗 [Source]({original_url})
        """
        
        return message.strip()
    
    async def send_to_telegram(self, movie_data: Dict[str, Any], original_url: str):
        """Send movie information to Telegram channel"""
        try:
            message = self.format_telegram_message(movie_data, original_url)
            
            # Send with photo if available
            if movie_data.get('poster_path'):
                await self.bot.send_photo(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    photo=movie_data['poster_path'],
                    caption=message,
                    parse_mode=ParseMode.MARKDOWN,
                    timeout=30
                )
            else:
                # Send without photo
                await self.bot.send_message(
                    chat_id=TELEGRAM_CHANNEL_ID,
                    text=message,
                    parse_mode=ParseMode.MARKDOWN,
                    timeout=30,
                    disable_web_page_preview=False
                )
            
            logger.info(f"Successfully posted: {movie_data['title']}")
            
        except TelegramError as e:
            logger.error(f"Telegram API error: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            raise
    
    async def check_new_movies(self):
        """Check website RSS feed for new movies"""
        movies_found = 0
        try:
            logger.info("Checking for new movies...")
            feed = feedparser.parse(WEBSITE_FEED_URL)
            
            if feed.bozo:  # Check for parsing errors
                logger.warning(f"RSS feed parsing warning: {feed.bozo_exception}")
            
            # Process entries from newest to oldest
            for entry in reversed(feed.entries[:10]):  # Check last 10 entries
                post_url = entry.link
                
                if post_url not in self.sent_movies:
                    logger.info(f"New movie detected: {entry.title}")
                    
                    # Fetch TMDB details
                    movie_data = self.fetch_tmdb_details(entry.title)
                    
                    if movie_data and movie_data.get('title'):
                        # Send to Telegram
                        await self.send_to_telegram(movie_data, post_url)
                        
                        # Mark as sent
                        self.save_sent_movie(post_url)
                        movies_found += 1
                        
                        # Rate limiting delay
                        await asyncio.sleep(3)
                    else:
                        logger.warning(f"Could not fetch TMDB data for: {entry.title}")
                        # Still mark as sent to avoid retrying
                        self.save_sent_movie(post_url)
            
            # Update status API
            self.update_status_api(movies_found)
            
            if movies_found == 0:
                logger.info("No new movies found")
            else:
                logger.info(f"Posted {movies_found} new movie(s)")
                
        except Exception as e:
            logger.error(f"Error checking new movies: {e}", exc_info=True)
            # Still update status API with error state
            self.update_status_api(0)
    
    async def run(self):
        """Main bot loop"""
        logger.info("=" * 50)
        logger.info("Starting Movie Bot...")
        logger.info(f"Channel: {TELEGRAM_CHANNEL_ID}")
        logger.info(f"Feed URL: {WEBSITE_FEED_URL}")
        logger.info(f"Check interval: {CHECK_INTERVAL} seconds")
        logger.info("=" * 50)
        
        # Initial connection tests
        logger.info("Testing connections...")
        telegram_ok = self.test_telegram_connection()
        tmdb_ok = self.test_tmdb_connection()
        rss_ok = self.test_rss_connection()
        
        if self.status_api:
            self.status_api.update_connection_status(
                telegram=telegram_ok,
                tmdb=tmdb_ok,
                rss=rss_ok
            )
            self.status_api.update_check_interval(CHECK_INTERVAL)
            self.update_status_api(0)
        
        if not telegram_ok:
            logger.error("Telegram connection failed! Please check your bot token.")
        if not tmdb_ok:
            logger.error("TMDB connection failed! Please check your API key.")
        if not rss_ok:
            logger.error("RSS feed connection failed! Please check the feed URL.")
        
        while True:
            try:
                await self.check_new_movies()
            except Exception as e:
                logger.error(f"Unexpected error in main loop: {e}", exc_info=True)
            
            logger.info(f"Waiting {CHECK_INTERVAL} seconds until next check...")
            await asyncio.sleep(CHECK_INTERVAL)

async def main():
    """Entry point"""
    # Import status API module
    from status_api import status_api
    
    bot = MovieBot(status_api=status_api)
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
