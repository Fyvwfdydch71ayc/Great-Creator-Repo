import asyncio
import csv
import io
import logging
import os
import re
import uuid
import urllib.parse
from datetime import datetime, timedelta

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    Message,
    WebAppInfo
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    ApplicationBuilder,  # <-- Import ApplicationBuilder here
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters
)

# Import everything from script1 (ensure these are defined in script1)
from script1 import (
    load_data_from_mongo, save_data, delete_later, check_required_channels, send_stored_message, 
    start_cmd, betch, process_first_post, process_last_post, broadcast_handler, setting_cmd, 
    export_data, list_links, website_handler, button_handler, handle_website_update, 
    subscription_listener, plan, pay_command, users_command, help_command, mongodb_info, 
    check_expired_subscriptions, on_startup,
    FIRST_POST, LAST_POST, ADMIN_ID, SUBS_CHANNEL, BROADCAST_CHANNEL  # Import required constants
)

from web_server import start_web_server  # Import the web server function

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_bot() -> None:
    # Get the bot token from the environment variable
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')  # Fetch the bot token from the environment

    if not bot_token:
        raise ValueError("No TELEGRAM_BOT_TOKEN environment variable found")

    app = ApplicationBuilder().token(bot_token).build()  # Use the token

    # Conversation handler for the "betch" command
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('betch', betch)],
        states={
            FIRST_POST: [MessageHandler(filters.FORWARDED & filters.Chat(ADMIN_ID), process_first_post)],
            LAST_POST: [MessageHandler(filters.FORWARDED & filters.Chat(ADMIN_ID), process_last_post)]
        },
        fallbacks=[]
    )

    # Register handlers
    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('start', start_cmd))
    app.add_handler(CommandHandler('links', list_links))
    app.add_handler(CommandHandler('website', website_handler))
    app.add_handler(CommandHandler('setting', setting_cmd))
    app.add_handler(CommandHandler('export', export_data))
    app.add_handler(CommandHandler('plan', plan))
    app.add_handler(CommandHandler('pay', pay_command))
    app.add_handler(CommandHandler('users', users_command))
    app.add_handler(CommandHandler('help', help_command))
    app.add_handler(CommandHandler('MongoDB', mongodb_info))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_website_update))
    app.add_handler(MessageHandler(filters.Chat(SUBS_CHANNEL), subscription_listener))
    app.add_handler(MessageHandler(filters.Chat(BROADCAST_CHANNEL), broadcast_handler))
    
    await app.run_polling()

async def main() -> None:
    # Run both the bot and the web server concurrently
    await asyncio.gather(
        run_bot(),
        start_web_server()
    )

if __name__ == '__main__':
    asyncio.run(main())
