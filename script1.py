import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, CallbackContext
import os

# Define the asynchronous function that handles incoming media messages
async def handle_media(update: Update, context: CallbackContext) -> None:
    thumb = None
    media = None

    # Handle Video
    if update.message.video:
        media = update.message.video
        if hasattr(media, 'thumb') and media.thumb:  # Check if the video has a thumbnail
            thumb = media.thumb
    # Handle Photo
    elif update.message.photo:
        media = update.message.photo[-1]  # Use the highest resolution photo (last item in the list)
        thumb = None  # Photos typically don't have a thumb, though you could use the photo itself
    # Handle Document (e.g., PDF)
    elif update.message.document:
        media = update.message.document
        if hasattr(media, 'thumb') and media.thumb:  # Check if the document has a thumbnail (e.g., PDF preview)
            thumb = media.thumb
    # Handle Sticker
    elif update.message.sticker:
        media = update.message.sticker
        if hasattr(media, 'thumb') and media.thumb:  # Stickers always have a thumbnail
            thumb = media.thumb
    # Handle Animation (GIF)
    elif update.message.animation:
        media = update.message.animation
        if hasattr(media, 'thumb') and media.thumb:  # GIFs typically have a thumbnail
            thumb = media.thumb
    else:
        thumb = None

    if thumb:
        # Download the thumbnail if available
        file = await context.bot.get_file(thumb.file_id)
        file_path = "thumbnail.jpg"  # Save the file as thumbnail.jpg
        await file.download_to_drive(file_path)
        
        # Send the thumbnail to the user
        await update.message.reply_photo(photo=open(file_path, 'rb'))
    else:
        await update.message.reply_text("No thumbnail or preview available for this media.")
    
# Define the /start command function
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "Hello! I'm your media bot. Send me any media, and I'll try to show you its thumbnail or preview!"
    )

# Define the main function to run the bot
