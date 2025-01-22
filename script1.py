import asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Channel ID or username to forward messages to
CHANNEL_ID = "-1002437038123"  # Replace with the correct channel ID or username

# Define the asynchronous function that handles incoming media messages and forwards them to the channel
async def handle_media(update: Update, context: CallbackContext) -> None:
    # Forward the message to the channel first
    await context.bot.forward_message(chat_id=CHANNEL_ID, from_chat_id=update.message.chat_id, message_id=update.message.message_id)
    
    # Check the type of media and handle accordingly
    media = None
    thumb = None
    
    if update.message.video:
        media = update.message.video
        thumb = getattr(media, 'thumb', None)  # Safely access 'thumb' if it exists
    elif update.message.photo:
        # Use the highest resolution photo (last item in the list)
        media = update.message.photo[-1]
        thumb = getattr(media, 'thumb', None)  # Safely access 'thumb' if it exists
    elif update.message.document:
        media = update.message.document
        thumb = getattr(media, 'thumb', None)  # Safely access 'thumb' if it exists
    elif update.message.sticker:
        media = update.message.sticker
        thumb = getattr(media, 'thumb', None)  # Safely access 'thumb' if it exists
    elif update.message.animation:
        media = update.message.animation
        thumb = getattr(media, 'thumb', None)  # Safely access 'thumb' if it exists

    # If a thumbnail is available, download and send it
    if thumb:
        file = await context.bot.get_file(thumb.file_id)
        file_path = "thumbnail.jpg"  # Save the file as thumbnail.jpg
        await file.download_to_drive(file_path)
        
        # Send the thumbnail to the user
        await update.message.reply_photo(photo=open(file_path, 'rb'))
    elif media:
        # If no thumbnail, send the main media file
        file = await context.bot.get_file(media.file_id)
        file_path = "media_file.jpg"  # Save the file as media_file.jpg (generic name)
        await file.download_to_drive(file_path)
        
        # Send the file to the user
        await update.message.reply_document(document=open(file_path, 'rb'))
    else:
        await update.message.reply_text("No thumbnail or preview available for this media.")
