import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, CallbackContext
import os

# Define the asynchronous function that handles incoming media messages
async def handle_media(update: Update, context: CallbackContext) -> None:
    thumb = None
    media = None

    # Check the type of media and handle accordingly
    if update.message.video:
        media = update.message.video
        thumb = media.thumb  # Get the thumbnail of the video if available
    elif update.message.photo:
        # Use the highest resolution photo (last item in the list)
        media = update.message.photo[-1]
        thumb = None  # Photos typically don't have a thumb, but we handle it here
    elif update.message.document:
        media = update.message.document
        # Documents like PDFs or files don't have 'thumb', so we handle accordingly
        thumb = None
    elif update.message.sticker:
        media = update.message.sticker
        thumb = media.thumb  # Stickers might have a thumbnail (preview)
    elif update.message.animation:
        media = update.message.animation
        thumb = media.thumb  # GIFs also might have a thumbnail
    else:
        thumb = None

    # Check if we have a thumb (thumbnail) available
    if thumb:
        # Download the thumbnail if available
        file = await context.bot.get_file(thumb.file_id)
        file_path = "thumbnail.jpg"  # Save the file as thumbnail.jpg
        await file.download_to_drive(file_path)
        
        # Send the thumbnail to the user
        await update.message.reply_photo(photo=open(file_path, 'rb'))
        os.remove(file_path)  # Clean up after sending the thumbnail
    else:
        await update.message.reply_text("No thumbnail or preview available for this media.")

# Define the /start command function
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Hello! I'm your media bot. Send me any media, and I'll try to show you its thumbnail or preview!"
    )

# Define the main function to run the bot
