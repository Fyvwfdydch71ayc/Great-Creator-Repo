import asyncio
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import CallbackContext
from PIL import Image
from io import BytesIO
import re
import os

# Apply nest_asyncio to enable asyncio in nested environments like Jupyter or multi-threaded apps

# Admin ID and Bot Token
ADMIN_ID = 6773787379

# URL for the logo image
LOGO_URL = "http://ob.saleh-kh.lol:2082/download.php?f=BQACAgQAAxkBAAEE7TZnkiqbuK5-LnDS8zNtrDKkfTSVswACpxkAAsuqQVB1FZV0GOmVGy8E&s=2449394&n=Picsart_25-01-16_09-09-54-162_5783091185375517095.png&m=image%2Fpng&T=MTczNzY0NjgxMw=="

# Path to save the logo
LOGO_PATH = "downloaded_logo.png"

# Download the logo image from the URL
def download_logo(url: str, save_path: str):
    response = requests.get(url)
    if response.status_code == 200:
        with open(save_path, 'wb') as f:
            f.write(response.content)
        print(f"Logo saved to {save_path}")
    else:
        print(f"Failed to download logo. Status code: {response.status_code}")

# Ensure the logo is downloaded once at the start
if not os.path.exists(LOGO_PATH):
    download_logo(LOGO_URL, LOGO_PATH)

# Define the customized caption with title support
def get_custom_caption(links, title):
    caption = f"""
🎃 ᴘᴏᴡᴇʀᴇᴅ ʙʏ↓ Telegram                
                🍯 @HotError      

Title - {title}
⌬ Hot Error
"""

    if len(links) == 1:
        caption += f"╰─➩ {links[0]} \n"
    elif len(links) > 1:
        for idx, link in enumerate(links, 1):
            caption += f"(Part {idx})─➩ {link} \n\n"

    caption += """
Other Categories ↓ 🥵⚡
https://t.me/HotError
"""
    return caption

# Function to add logo to image
def add_logo_to_image(photo: Image.Image, logo_path: str) -> Image.Image:
    logo = Image.open(logo_path)
    logo_width = photo.width // 3  # Resize logo to 1/3rd of the image width
    logo_height = int((logo_width / logo.width) * logo.height)
    logo = logo.resize((logo_width, logo_height), Image.Resampling.LANCZOS)
    position = ((photo.width - logo.width) // 2, 0)
    photo.paste(logo, position, logo.convert("RGBA"))
    return photo

# Function to handle received media and customize the caption
async def handle_media(update: Update, context: CallbackContext):
    if update.effective_user.id == ADMIN_ID:
        media = None
        caption = None
        links = []  # List to store all the links
        title = "No Title"  # Default title if no Title= pattern is found

        # Check for different types of media
        if update.message.photo:
            caption = update.message.caption
            media = update.message.photo[-1]  # Take the highest quality photo
        elif update.message.video:
            caption = update.message.caption
            media = update.message.video
        elif update.message.document:
            caption = update.message.caption
            media = update.message.document
        elif update.message.voice:
            caption = update.message.caption
            media = update.message.voice
        elif update.message.animation:
            caption = update.message.caption
            media = update.message.animation
        elif update.message.sticker:
            caption = update.message.caption
            media = update.message.sticker

        if caption:
            title_match = re.search(r"Title=\s?\{(.*?)\}", caption)  # Regex to extract title inside {}

            if title_match:
                title = title_match.group(1).strip()

            links = re.findall(r"https?://[^\s]+", caption)

            custom_caption = get_custom_caption(links, title)

            thumb = None

            # Check if the media has a thumbnail
            if update.message.video:
                thumb = media.thumb  # Extract thumbnail if available
            elif update.message.document:
                thumb = media.thumb
            elif update.message.animation:
                thumb = media.thumb
            elif update.message.sticker:
                thumb = media.thumb

            if thumb:
                # Download the thumbnail if available
                file = await context.bot.get_file(thumb.file_id)
                thumb_bytes = await file.download_as_bytearray()

                # Open the thumbnail as an image
                thumb_image = Image.open(BytesIO(thumb_bytes))

                # Add the logo to the thumbnail
                thumb_with_logo = add_logo_to_image(thumb_image, LOGO_PATH)

                # Save the modified thumbnail to a BytesIO object
                output = BytesIO()
                thumb_with_logo.save(output, format="PNG")
                output.seek(0)

                # Send the modified thumbnail with the custom caption
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=output, caption=custom_caption)

            else:
                # Handle the case where there's no thumbnail, send only the media with caption
                if update.message.photo:
                    # For photos, we add the logo to the photo and send it with the custom caption
                    photo_file = await media.get_file()  # Await the file download
                    photo_bytes = await photo_file.download_as_bytearray()  # Await the download as bytearray
                    photo_image = Image.open(BytesIO(photo_bytes))  # Open the photo as an image
                    photo_with_logo = add_logo_to_image(photo_image, LOGO_PATH)  # Add the logo

                    # Save the photo with the logo to a BytesIO object
                    output = BytesIO()
                    photo_with_logo.save(output, format="PNG")
                    output.seek(0)

                    # Send the photo with logo and custom caption
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=output, caption=custom_caption)

                elif update.message.video:
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=media.file_id, caption=custom_caption)
                elif update.message.document:
                    await context.bot.send_document(chat_id=update.effective_chat.id, document=media.file_id, caption=custom_caption)
                elif update.message.voice:
                    await context.bot.send_voice(chat_id=update.effective_chat.id, voice=media.file_id, caption=custom_caption)
                elif update.message.animation:
                    await context.bot.send_animation(chat_id=update.effective_chat.id, animation=media.file_id, caption=custom_caption)
                elif update.message.sticker:
                    await context.bot.send_sticker(chat_id=update.effective_chat.id, sticker=media.file_id)


# Function to start the bot and process incoming updates
