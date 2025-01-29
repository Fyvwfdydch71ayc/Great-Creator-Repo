import logging
import asyncio
import os  # Import the os module to access environment variables
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes, CallbackContext, Application# Add ConversationHandler import
from script1 import extract_links, start, handle_message, done, 
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
    app.add_handler(CommandHandler("done", done))
    app.add_handler(MessageHandler(filters.ALL, handle_message))
    
    await app.run_polling()

async def main() -> None:
    # Run both the bot and web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == '__main__':
    asyncio.run(main())
