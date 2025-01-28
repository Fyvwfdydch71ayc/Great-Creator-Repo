import logging
import random
import string
#import nest_asyncio
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from pymongo import MongoClient
import re


#chal ja randi ke
# Apply nest_asyncio to enable running asyncio in Jupyter or similar environments
#nest_asyncio.apply()

# MongoDB Connection URL
MONGO_URI = "mongodb+srv://kunalrepowala1:ILPVxpADb0FK7Raa@cluster0.evumw.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
client = MongoClient(MONGO_URI)

# Select the database and collection
db = client.Cluster0
media_collection = db.media_links

# Admin ID and bot token
ADMIN_ID = 6773787379
#TOKEN = "7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0"

# Current website for mini app and inline button
current_website = "https://google.com"

# Set up logging
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to generate a unique code for each link
def generate_unique_code():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=8))

# Function to extract links from a text
def extract_link_from_text(text):
    url_pattern = r'(https?://[^\s]+)'
    return re.findall(url_pattern, text)

# New function to update URLs for all existing links when the website changes
def update_urls_for_all_links():
    global current_website
    
    # Update the links by replacing the old domain with the new one
    media_collection.update_many(
        {},
        {"$set": {"web_app_url": f"{current_website}/{code}" for code in media_collection.find()}},
    )

# Command handler to start the bot and handle the start parameter
async def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    start_param = update.message.text.split()[1] if len(update.message.text.split()) > 1 else None

    if start_param:
        media_data = media_collection.find_one({"code": start_param})
        
        if media_data:
            media_type = media_data['type']
            media = media_data['media']
            caption = media_data.get('caption', None)  # Get the caption if it exists
            web_app_url = media_data.get('web_app_url', None)  # Use the updated URL
            
            # Extract the link from the caption if available
            if caption:
                extracted_links = extract_link_from_text(caption)
                if extracted_links:
                    # Check if the link starts with the current website (case-insensitive)
                    for url in extracted_links:
                        if url.lower().startswith(current_website.lower()):
                            web_app_url = url
                            break  # Only pick the first valid URL and ignore others
                # Remove any old website URL from the caption after extracting it
                caption = re.sub(r'(https?://[^\s]+)', '', caption)

            # Send the warning message
            warning_message = await update.message.reply_text("⚠️ This file will be deleted within 1 minute. Please take note.")

            # Create the web app button if a valid URL exists
            if web_app_url:
                web_app_info = WebAppInfo(url=web_app_url)
                keyboard = InlineKeyboardMarkup([
                    [InlineKeyboardButton(text="Open Web App", web_app=web_app_info)],
                    [InlineKeyboardButton(text="Open URL", url=web_app_url)]  # Inline button for the URL
                ])
            else:
                keyboard = None  # No button if there's no valid URL

            # Send the media along with the inline keyboard for the mini app and URL button
            if media_type == "photo":
                sent_media = await update.message.reply_photo(media, caption=caption, reply_markup=keyboard, protect_content=True)
            elif media_type == "video":
                sent_media = await update.message.reply_video(media, caption=caption, reply_markup=keyboard, protect_content=True)
            elif media_type == "document":
                sent_media = await update.message.reply_document(media, caption=caption, reply_markup=keyboard, protect_content=True)
            elif media_type == "audio":
                sent_media = await update.message.reply_audio(media, caption=caption, reply_markup=keyboard, protect_content=True)
            elif media_type == "sticker":
                sent_media = await update.message.reply_sticker(media, reply_markup=keyboard, protect_content=True)
            elif media_type == "text":
                sent_media = await update.message.reply_text(media, reply_markup=keyboard, protect_content=True)

            # Schedule the deletion in the background without blocking the bot
            asyncio.create_task(delete_media_after_1_minute(sent_media, update, warning_message))
        else:
            await update.message.reply_text("This link does not correspond to any media.")
    else:
        await update.message.reply_text("Invalid start parameter.")

# New function to delete the media and warning message after 1 minute
async def delete_media_after_1_minute(sent_media, update: Update, warning_message):
    await asyncio.sleep(60)  # Wait for 1 minute

    # Delete the warning message and the media
    try:
        await warning_message.delete()  # Delete the warning message
        await sent_media.delete()  # Delete the sent media
    except Exception as e:
        logger.error(f"Error deleting message: {e}")

# Message handler to process media from the admin
async def handle_media(update: Update, context: CallbackContext):
    # Check if the update contains a message
    if update.message is None:
        return  # Ignore updates without messages
    
    # Ignore messages from non-admins
    if update.message.from_user.id != ADMIN_ID:
        return
    
    media_type = None
    media = None
    caption = None
    
    if update.message.photo:
        media_type = "photo"
        media = update.message.photo[-1].file_id
        caption = update.message.caption  # Get the caption of the photo
    elif update.message.video:
        media_type = "video"
        media = update.message.video.file_id
        caption = update.message.caption  # Get the caption of the video
    elif update.message.document:
        media_type = "document"
        media = update.message.document.file_id
        caption = update.message.caption  # Get the caption of the document
    elif update.message.audio:
        media_type = "audio"
        media = update.message.audio.file_id
        caption = update.message.caption  # Get the caption of the audio if available
    elif update.message.voice:
        media_type = "audio"
        media = update.message.voice.file_id
        caption = update.message.caption  # Get the caption of the voice message, if available
    elif update.message.sticker:
        media_type = "sticker"
        media = update.message.sticker.file_id
    elif update.message.text:
        media_type = "text"
        media = update.message.text
    elif update.message.animation:
        media_type = "video"
        media = update.message.animation.file_id
        caption = update.message.caption  # Get the caption of the animation

    if media_type:
        unique_code = generate_unique_code()
        
        # Store the media in MongoDB
        media_data = {
            "code": unique_code,
            "type": media_type,
            "media": media,
            "caption": caption
        }
        
        media_collection.insert_one(media_data)
        
        # Create the unique start link
        bot_username = (await context.bot.get_me()).username
        start_link = f"https://t.me/{bot_username}?start={unique_code}"
        
        # Send the generated link to the admin
        await update.message.reply_text(f"Here is the unique link: {start_link}")

# Command handler for /list to send all created parameter links with media type
async def list_links(update: Update, context: CallbackContext):
    # Only respond if the message is from the admin
    if update.message.from_user.id != ADMIN_ID:
        return
    
    # Check if there are any links
    media_data_list = media_collection.find()
    if not media_data_list:
        await update.message.reply_text("No media links have been created yet.")
        return
    
    # Create the list of links with media type
    links = []
    for idx, media_data in enumerate(media_data_list, 1):
        media_type = media_data['type']
        start_link = f"https://t.me/{(await context.bot.get_me()).username}?start={media_data['code']}"
        links.append(f"({idx}) {start_link} {media_type.capitalize()}")

    # Split the list into chunks of 4096 characters or less
    chunk_size = 4096
    message_parts = [links[i:i + chunk_size] for i in range(0, len(links), chunk_size)]
    
    # Send the list in multiple parts
    for part in message_parts:
        await update.message.reply_text("\n".join(part))

# Command handler to show and change the default website
async def website(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return

    # Show the current website and provide the change option
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(text="Change Website", callback_data="change_website")]
    ])
    
    await update.message.reply_text(f"Current website: {current_website}", reply_markup=keyboard)

# Callback query handler for changing the website
async def change_website(update: Update, context: CallbackContext):
    if update.callback_query.from_user.id != ADMIN_ID:
        return

    # Ask admin to provide a new website URL
    await update.callback_query.message.reply_text("Please send the new website URL (e.g., https://example.com).")
    await update.callback_query.answer()

# Message handler for the admin to receive and set the new website URL
async def handle_new_website(update: Update, context: CallbackContext):
    global current_website
    
    if update.message.from_user.id != ADMIN_ID:
        return
    
    # Validate the URL to ensure it's in the correct format
    url_pattern = r"https?://[^\s]+"
    if re.match(url_pattern, update.message.text):
        current_website = update.message.text.strip()  # Update the website
        
        # Update the existing links with the new website
        update_urls_for_all_links()
        
        await update.message.reply_text(f"Website has been updated to: {current_website}")
    else:
        await update.message.reply_text("Invalid URL. Please send a valid website URL.")
