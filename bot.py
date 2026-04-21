import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

# Import our settings
import config

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /start command."""
    await update.message.reply_text(config.START_MSG, parse_mode='Markdown')

async def search_movie(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Searches TMDB for movies based on user text."""
    query = update.message.text
    url = f"https://api.themoviedb.org/3/search/movie"
    params = {"api_key": config.TMDB_API_KEY, "query": query, "language": "en-US"}
    
    try:
        response = requests.get(url, params=params).json()
        results = response.get('results', [])

        if not results:
            await update.message.reply_text("🔎 *No movies found.* Try a different name!", parse_mode='Markdown')
            return

        # Create buttons for the top 6 results
        keyboard = []
        for movie in results[:6]:
            title = movie.get('title')
            year = (movie.get('release_date') or "N/A")[:4]
            m_id = str(movie.get('id'))
            keyboard.append([InlineKeyboardButton(f"🎬 {title} ({year})", callback_data=f"mv_{m_id}")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("🎯 *Select the movie you want:*", reply_markup=reply_markup, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Search Error: {e}")
        await update.message.reply_text("⚠️ Connection error. Check your API Key in config.py")

async def movie_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Shows full movie info and the OTTGuild watch link."""
    query = update.callback_query
    await query.answer()
    
    movie_id = query.data.replace("mv_", "")
    url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {"api_key": config.TMDB_API_KEY, "language": "en-US"}
    
    try:
        movie = requests.get(url, params=params).json()
        title = movie.get('title')
        rating = movie.get('vote_average', 'N/A')
        runtime = movie.get('runtime', 'N/A')
        genres = ", ".join([g['name'] for g in movie.get('genres', [])])
        plot = movie.get('overview', 'No description available.')
        
        # Link construction for OTTGuild
        watch_link = f"{config.WATCH_BASE_URL}{movie_id}"
        
        caption = (
            f"🌟 *{title.upper()}*\n\n"
            f"⭐ *Rating:* {rating}/10\n"
            f"⏳ *Runtime:* {runtime} mins\n"
            f"🎭 *Genres:* {genres}\n\n"
            f"📖 *Plot:* {plot[:550]}..."
        )
        
        btns = [
            [InlineKeyboardButton("🚀 Watch Online (OTTGuild)", url=watch_link)],
            [InlineKeyboardButton("🔙 New Search", callback_data="reset")]
        ]
        
        poster = movie.get('poster_path')
        if poster:
            await query.message.reply_photo(
                photo=f"{config.TMDB_IMAGE_BASE}{poster}",
                caption=caption,
                reply_markup=InlineKeyboardMarkup(btns),
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text(caption, reply_markup=InlineKeyboardMarkup(btns), parse_mode='Markdown')
            
    except Exception as e:
        logger.error(f"Details Error: {e}")

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("💬 Send me a new movie name!")

def main():
    app = Application.builder().token(config.TELEGRAM_BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_movie))
    app.add_handler(CallbackQueryHandler(movie_details, pattern="^mv_"))
    app.add_handler(CallbackQueryHandler(reset, pattern="reset"))

    print("--- Bot is Live! ---")
    app.run_polling()

if __name__ == '__main__':
    main()
