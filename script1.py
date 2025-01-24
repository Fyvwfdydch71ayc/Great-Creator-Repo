import asyncio
#import nest_asyncio
from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, CallbackContext

# Apply nest_asyncio to allow running the bot in Jupyter or other nested asyncio environments
#nest_asyncio.apply()

# Bot token
#TOKEN = "7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0"

# Define the asynchronous function that handles incoming media messages
async def handle_media(update: Update, context: CallbackContext) -> None:
    thumb = None
    media = None

    # Check the type of media and handle accordingly
    if update.message.video:
        media = update.message.video
        thumb = media.thumb  # Get the thumbnail of the video
    elif update.message.photo:
        # Use the highest resolution photo (last item in the list)
        media = update.message.photo[-1]
        thumb = media.thumb  # Photos don't have a 'thumb', this is just an empty check
    elif update.message.document:
        media = update.message.document
        thumb = media.thumb  # Documents might have a thumbnail (e.g., PDFs)
    elif update.message.sticker:
        media = update.message.sticker
        thumb = media.thumb  # Stickers might have a thumbnail (preview)
    elif update.message.animation:
        media = update.message.animation
        thumb = media.thumb  # GIFs also might have a thumbnail
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
