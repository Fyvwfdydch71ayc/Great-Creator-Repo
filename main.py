import logging
import asyncio
import os  # Import the os module to access environment variables
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,  # Add this import
)
from script1 import (
    load_message_store,
    save_message_store,
    remove_urls_from_caption,
    extract_path_from_caption,
    is_member_of_channels,
    start,
    delete_after_delay,
    help_command,
    handle_message,
    links_command,
    website_command,
    callback_query_handler,
    handle_new_website,
    error,
)
from web_server import start_web_server  # Import the web server function

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from the environment variable
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")  # Ensure the token is available

    app = ApplicationBuilder().token(bot_token).build()  # Use the token

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("website", website_command))
    app.add_handler(CommandHandler("links", links_command))
    app.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(callback_query_handler))  # Add callback query handler

    await app.run_polling()

async def main() -> None:
    # Run both the bot and web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == "__main__":
    asyncio.run(main())
