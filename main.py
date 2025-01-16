import logging
import asyncio
import os  # Import os module to fetch environment variables
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, ChatJoinRequestHandler
from web_server import start_web_server  # Import the web server function
from script1 import start, approve, detail, send_cv, handle_message, ADMIN_ID  # Import the updated functions including ADMIN_ID

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from environment variables
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")  # Ensure the token is available
    
    app = ApplicationBuilder().token(bot_token).build()  # Use the bot token

    # Add command and message handlers
    start_handler = CommandHandler("start", start)
    app.add_handler(start_handler)

    # Add handler for detailed information about joined chats (only for the admin)
    detail_handler = CommandHandler("detail", detail)
    app.add_handler(detail_handler)

    # Add handler for sending CSV file of user IDs (only for the admin)
    id_handler = CommandHandler("id", send_cv)
    app.add_handler(id_handler)

    # MessageHandler for all types (video, sticker, gif, etc.)
    all_handler = MessageHandler(filters.ALL, handle_message)
    app.add_handler(all_handler)

    # Handle chat join requests
    app.add_handler(ChatJoinRequestHandler(approve))

    await app.run_polling()

async def main() -> None:
    # Run both the bot and the web server concurrently
    await asyncio.gather(run_bot(), start_web_server())

if __name__ == '__main__':
    asyncio.run(main())
