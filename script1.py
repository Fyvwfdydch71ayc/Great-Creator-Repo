import logging
import asyncio
#import nest_asyncio
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
    CallbackQueryHandler,
)
from pymongo import MongoClient

# Apply nest_asyncio to allow nested event loops
#nest_asyncio.apply()

# Bot token and admin ID
#BOT_TOKEN = "7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0"
ADMIN_ID = 6773787379
CHANNEL_ID = -1002479661811  # Replace with your channel ID

# Required channels and invite links
REQUIRED_CHANNELS = [-1002434409634, -1002315588145]
INVITE_LINKS = {
    -1002434409634: "https://t.me/+h7ICg0eD7gQxZmE0",
    -1002315588145: "https://t.me/+tCyah29hMTtjNTBk",
}

# MongoDB connection
MONGO_URI = "mongodb+srv://kunalrepowala1:ILPVxpADb0FK7Raa@cluster0.evumw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
DB_NAME = "Cluster0"
COLLECTION_NAME = "message_store"

# Initialize MongoDB client
client = MongoClient(MONGO_URI)
db = client[DB_NAME]
collection = db[COLLECTION_NAME]

# Global variable to store the current website URL
CURRENT_WEBSITE_URL = "https://google.com/"

# Global variable to track if the admin is changing the website URL
CHANGING_WEBSITE = False

# Load message store from MongoDB
def load_message_store():
    message_store = {}
    for doc in collection.find():
        message_store[doc["message_id"]] = (doc["channel_message_id"], doc["path"], doc["type"])
    return message_store

# Save message store to MongoDB
def save_message_store(message_store):
    # Clear existing documents in the collection
    collection.delete_many({})
    # Insert new documents
    for key, value in message_store.items():
        collection.insert_one({
            "message_id": key,
            "channel_message_id": value[0],
            "path": value[1],
            "type": value[2],
        })

# Remove https:// URLs from caption while preserving gaps
def remove_urls_from_caption(caption):
    if not caption:
        return caption
    # Remove all https:// URLs and preserve gaps
    return re.sub(r"\s*https?://\S+\s*", "\n", caption).strip()

# Extract path from URLs matching the current website
def extract_path_from_caption(caption):
    if not caption:
        return None
    # Find all URLs in the caption
    urls = re.findall(r"https?://\S+", caption)
    for url in urls:
        if url.lower().startswith(CURRENT_WEBSITE_URL.lower()):
            # Extract the path from the matching URL
            path = url[len(CURRENT_WEBSITE_URL) :]
            return path if path else None
    return None

# Check if the user is a member of the required channels
async def is_member_of_channels(user_id, bot):
    member_statuses = []
    for channel_id in REQUIRED_CHANNELS:
        try:
            chat_member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
            member_statuses.append(
                chat_member.status in ["member", "administrator", "creator"]
            )
        except Exception as e:
            logging.error(
                f"Error checking membership for user {user_id} in channel {channel_id}: {e}"
            )
            member_statuses.append(False)
    return member_statuses

# Start command handler

# Move delete_after_delay outside of the start function
async def delete_after_delay(context: ContextTypes.DEFAULT_TYPE, user_id: int, message_id: int):
    await asyncio.sleep(60)  # Wait for 1 minute
    try:
        await context.bot.delete_message(
            chat_id=user_id,
            message_id=message_id,
        )
    except Exception as e:
        logging.error(f"Failed to delete message: {e}")

# Start command handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    start_param = context.args[0] if context.args else None

    # Check if the user is a member of the required channels
    member_statuses = await is_member_of_channels(user_id, context.bot)
    not_joined_channels = [
        REQUIRED_CHANNELS[i] for i, is_member in enumerate(member_statuses) if not is_member
    ]

    if not_joined_channels:
        # Prepare the invite buttons only for channels the user hasn't joined
        invite_buttons = [
            [InlineKeyboardButton(f"Join Channel {i+1}", url=INVITE_LINKS[channel_id])]
            for i, channel_id in enumerate(not_joined_channels)
        ]

        # Add a button to retry with the same start link
        if start_param:
            retry_button = InlineKeyboardButton(
                "Joined🧩 (restart)",
                url=f"https://t.me/{(await context.bot.get_me()).username}?start={start_param}",
            )
            invite_buttons.append([retry_button])

        inline_keyboard = InlineKeyboardMarkup(invite_buttons)
        await update.message.reply_text(
            "Please join the following channels to use this bot:",
            reply_markup=inline_keyboard,
        )
    else:
        if start_param:
            message_store = load_message_store()
            if start_param in message_store:
                channel_message_id, path, message_type = message_store[start_param]
                try:
                    # Forward the message from the channel to the bot itself
                    forwarded_message = await context.bot.forward_message(
                        chat_id=ADMIN_ID,  # Forward to the admin (bot itself)
                        from_chat_id=CHANNEL_ID,
                        message_id=int(channel_message_id),
                    )

                    # Remove links from the caption
                    new_caption = remove_urls_from_caption(forwarded_message.caption)

                    # Prepare the inline keyboard if a path exists
                    inline_keyboard = None
                    if path:
                        full_url = f"{CURRENT_WEBSITE_URL}{path}"
                        inline_keyboard = InlineKeyboardMarkup(
                            [
                                [InlineKeyboardButton("Open Mini App", web_app={"url": full_url})],
                                [InlineKeyboardButton("Open Inline Link", url=full_url)],
                            ]
                        )

                    # Send the message to the user with the modified caption
                    if forwarded_message.text:
                        sent_message = await context.bot.send_message(
                            chat_id=user_id,
                            text=new_caption if new_caption else forwarded_message.text,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    elif forwarded_message.photo:
                        sent_message = await context.bot.send_photo(
                            chat_id=user_id,
                            photo=forwarded_message.photo[-1].file_id,
                            caption=new_caption,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    elif forwarded_message.video:
                        sent_message = await context.bot.send_video(
                            chat_id=user_id,
                            video=forwarded_message.video.file_id,
                            caption=new_caption,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    elif forwarded_message.audio:
                        sent_message = await context.bot.send_audio(
                            chat_id=user_id,
                            audio=forwarded_message.audio.file_id,
                            caption=new_caption,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    elif forwarded_message.document:
                        sent_message = await context.bot.send_document(
                            chat_id=user_id,
                            document=forwarded_message.document.file_id,
                            caption=new_caption,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    elif forwarded_message.sticker:
                        sent_message = await context.bot.send_sticker(
                            chat_id=user_id,
                            sticker=forwarded_message.sticker.file_id,
                            reply_markup=inline_keyboard,
                            protect_content=True,
                        )
                    else:
                        await update.message.reply_text("Unsupported message type.")
                        return

                    # Delete the forwarded message from the bot's chat
                    await context.bot.delete_message(
                        chat_id=ADMIN_ID,
                        message_id=forwarded_message.message_id,
                    )

                    # Delete the message after 1 minute (run in background)
                    asyncio.create_task(delete_after_delay(context, user_id, sent_message.message_id))

                except Exception as e:
                    await update.message.reply_text(f"Failed to retrieve the message. Error: {e}")
            else:
                await update.message.reply_text("Message not found.")
        else:
            await update.message.reply_text("Welcome! Use /help to see available commands.")
# Help command handler
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        await update.message.reply_text("Send any message to the bot, and it will generate a link for you.")
    else:
        # Send a message with an inline button for non-admin users
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join - HotError", url="https://t.me/HotError")]
        ])
        await update.message.reply_text(
            "Get more categories 👇",
            reply_markup=inline_keyboard,
        )

# Handle all types of messages from admin
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        # Check if the admin is in the process of changing the website URL
        if context.user_data.get("changing_website", False):
            await handle_new_website(update, context)
            return

        message = update.message
        try:
            # Extract the path from the caption (only for the current website)
            path = extract_path_from_caption(message.caption)

            # Determine the message type (text, photo, video, etc.)
            if message.text:
                message_type = "text"
            elif message.photo:
                message_type = "photo"
            elif message.video:
                message_type = "video"
            elif message.audio:
                message_type = "audio"
            elif message.document:
                message_type = "document"
            elif message.sticker:
                message_type = "sticker"
            else:
                message_type = "unknown"

            # Forward the message to the channel with the ORIGINAL caption (do not remove links)
            channel_message = await message.copy(
                chat_id=CHANNEL_ID,
                caption=message.caption,  # Keep the original caption
            )

            # Store the channel message ID, path, and type in MongoDB
            message_id = str(message.message_id)
            message_store = load_message_store()
            message_store[message_id] = (str(channel_message.message_id), path, message_type)
            save_message_store(message_store)

            # Generate the parameter link
            bot_username = context.bot.username
            link = f"https://t.me/{bot_username}?start={message_id}"

            # Send the parameter link to the admin
            await update.message.reply_text(f"Here is your link: {link}")
        except Exception as e:
            await update.message.reply_text(f"Failed to forward the message to the channel. Error: {e}")
    else:
        # Send a message with an inline button for non-admin users
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join - HotError", url="https://t.me/HotError")]
        ])
        await update.message.reply_text(
            "Get more categories 👇",
            reply_markup=inline_keyboard,
        )

# /links command handler (admin-only)
async def links_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        message_store = load_message_store()
        if not message_store:
            await update.message.reply_text("No parameter links have been created yet.")
            return

        # Prepare the list of links
        links_list = []
        for i, (message_id, (channel_message_id, path, message_type)) in enumerate(message_store.items(), start=1):
            bot_username = context.bot.username
            link = f"https://t.me/{bot_username}?start={message_id}"
            mini_inline_status = "Yes" if path else "No"
            links_list.append(f"({i}) {link} {message_type} mini-inline({mini_inline_status})")

        # Send the list of links
        await update.message.reply_text("\n".join(links_list))
    else:
        # Send a message with an inline button for non-admin users
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join - HotError", url="https://t.me/HotError")]
        ])
        await update.message.reply_text(
            "Get more categories 👇",
            reply_markup=inline_keyboard,
        )

# /website command handler
async def website_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        inline_keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Change Website", callback_data="change_website")]]
        )
        await update.message.reply_text(
            f"Current website URL: {CURRENT_WEBSITE_URL}",
            reply_markup=inline_keyboard,
        )
    else:
        # Send a message with an inline button for non-admin users
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("Join - HotError", url="https://t.me/HotError")]
        ])
        await update.message.reply_text(
            "Get more categories 👇",
            reply_markup=inline_keyboard,
        )

# Callback query handler for changing website
async def callback_query_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "change_website":
        # Set the state to indicate that the admin is changing the website URL
        context.user_data["changing_website"] = True
        await query.edit_message_text("Please send the new website URL (e.g., https://men.com/).")

# Handle new website URL from admin
async def handle_new_website(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    if user_id == ADMIN_ID:
        global CURRENT_WEBSITE_URL
        new_website_url = update.message.text

        # Validate the new website URL
        if new_website_url.startswith("https://"):
            CURRENT_WEBSITE_URL = (
                new_website_url if new_website_url.endswith("/") else new_website_url + "/"
            )
            await update.message.reply_text(f"Website URL updated to: {CURRENT_WEBSITE_URL}")
        else:
            await update.message.reply_text("Invalid website URL. Please send a valid https:// URL.")

        # Reset the state
        context.user_data["changing_website"] = False

# Error handler
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.error(f"Update {update} caused error {context.error}")
