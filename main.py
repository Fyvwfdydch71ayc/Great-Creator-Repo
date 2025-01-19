import logging
import asyncio
import os  # Import os module to fetch environment variables
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ChatJoinRequestHandler
from web_server import start_web_server  # Import the web server function
from script1 import generate_unique_code, delete_media_after_1_minute, handle_media, list_links, start # Import the updated functions including ADMIN_ID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")  # Ensure the token is available
    
    app = ApplicationBuilder().token(bot_token).build()  # Use the bot token

   

    app.add_handler(CommandHandler("start", start))

    # Handler for the /list command to send all links with media type
    app.add_handler(CommandHandler("list", list_links))

    # Handler for all messages from the admin (media, text, etc.)
    app.add_handler(MessageHandler(filters.ALL, handle_media))

    await app.run_polling()


async def main() -> None:
    # Run both the bot and the web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == '__main__':
    asyncio.run(main())
