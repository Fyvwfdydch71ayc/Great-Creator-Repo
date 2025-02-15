import asyncio
import csv
import io
import logging
import os
import re
import uuid
import urllib.parse
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters
)

# Import everything from script1 (ensure these are defined in script1)
from script1 import (
    download_gif,
    track_user,
    send_welcome_message,
    approve,
    start,
    more_spicy,
    admin_users,
    admin_grp,
    track_user_handler,
    forward_private_message,
    broadcast_channel_message,
    # Import required constants if any
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
    
    await download_gif()

    app = (
        ApplicationBuilder()
        .token(bot_token)
        .concurrent_updates(True)
        .build()
    )

    # Global tracker for all updates.
    app.add_handler(MessageHandler(filters.ALL, track_user_handler), group=-1)

    # Join request handling in groups/supergroups.
    app.add_handler(ChatJoinRequestHandler(approve))

    # Command handlers.
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", admin_users))
    app.add_handler(CommandHandler("grp", admin_grp))

    # For non-command text messages in private chat, reply with spicy fun.
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, more_spicy)
    )

    # Copy user messages in private chat to channel -1002399068205.
    app.add_handler(MessageHandler(
        filters.ChatType.PRIVATE, forward_private_message), group=1)

    # Broadcast: Copy messages from channel -1002374713796 to all tracked users.
    app.add_handler(MessageHandler(
        filters.Chat(-1002374713796), broadcast_channel_message), group=2)

    await app.run_polling()

async def main() -> None:
    # Run both the bot and the web server concurrently.
    await asyncio.gather(
        run_bot(),
        start_web_server()
    )

if __name__ == '__main__':
    asyncio.run(main())
