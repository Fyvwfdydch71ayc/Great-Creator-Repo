import logging
import asyncio
import os  # Import os module to fetch environment variables
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ChatJoinRequestHandler
from web_server import start_web_server  # Import the web server function
from script1 import download_logo, get_custom_caption, add_logo_to_image, handle_media, start  # Import the updated functions including ADMIN_ID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")  # Ensure the token is available
    
    app = ApplicationBuilder().token(bot_token).build()  # Use the bot token

    # Add handlers
    app.add_handler(CommandHandler("start", start))

    # Use filters.ALL to capture all types of messages
    app.add_handler(MessageHandler(filters.ALL, handle_media))

    await app.run_polling()


async def main() -> None:
    # Run both the bot and the web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == '__main__':
    asyncio.run(main())
