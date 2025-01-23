import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext


# Define the asynchronous function that handles incoming media messages
async def handle_media(update: Update, context: CallbackContext) -> None:
    thumb = None
    media = None

    # Check the type of media and handle accordingly
    if update.message.video:
        media = update.message.video
        if hasattr(media, 'thumb'):
            thumb = media.thumb  # Get the thumbnail of the video
    elif update.message.photo:
        media = update.message.photo[-1]  # Use the highest resolution photo
        if hasattr(media, 'thumb'):
            thumb = media.thumb  # Photos don't have a 'thumb', this is just an empty check
    elif update.message.document:
        media = update.message.document
        if hasattr(media, 'thumb'):
            thumb = media.thumb  # Documents might have a thumbnail (e.g., PDFs)
    elif update.message.sticker:
        media = update.message.sticker
        if hasattr(media, 'thumb'):
            thumb = media.thumb  # Stickers might have a thumbnail (preview)
    elif update.message.animation:
        media = update.message.animation
        if hasattr(media, 'thumb'):
            thumb = media.thumb  # GIFs might have a thumbnail
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
