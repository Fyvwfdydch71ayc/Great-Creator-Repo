import logging
import asyncio
import os  # Import the os module to access environment variables
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackContext, Application# Add ConversationHandler import
from script1 import generate_unique_code, extract_link_from_text, update_urls_for_all_links, start, delete_media_after_1_minute, handle_media, list_links, website, change_website, handle_new_website # Corrected import statement
from web_server import start_web_server  # Import the web server function



# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from the environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")  # Ensure the token is available

    app = ApplicationBuilder().token(bot_token).build()  # Use the token


  #  app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("start", start))

    # Handler for the /list command to send all links with media type
    app.add_handler(CommandHandler("list", list_links))

    # Handler for the /website command to show and change the website
    app.add_handler(CommandHandler("website", website))

    # Handler for callback query to change the website
    app.add_handler(CallbackQueryHandler(change_website, pattern="change_website"))

    # Handler for receiving and setting the new website URL from admin
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_website))

    # Handler for all messages from the admin (media, text, etc.)
    app.add_handler(MessageHandler(filters.ALL, handle_media))
    
    await app.run_polling()

async def main() -> None:
    # Run both the bot and web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == '__main__':
    asyncio.run(main())
