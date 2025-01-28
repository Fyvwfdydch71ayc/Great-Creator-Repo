import logging
import asyncio
#import nest_asyncio
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, filters, Application, CallbackContext
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
from io import BytesIO

# Enabling nested event loop
#nest_asyncio.apply()

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot token (use the token you provided here)
#TOKEN = '7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0'

# Constant for the part to remove from the title
TERABOX_SUFFIX = " - Share Files Online & Send Larges Files with TeraBox"

# Function to fetch the title and image URL of a webpage asynchronously using aiohttp
async def get_title_and_image(session, url: str):
    try:
        async with session.get(url) as response:
            response.raise_for_status()
            html_content = await response.text()

        # Parse the HTML using BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')

        # Extract title
        title = soup.title.string if soup.title else "No Title Found"

        # Log the title before any changes
        logger.info(f"Original Title: {title}")

        # Strip the unwanted suffix from the title if it exists
        if title.endswith(TERABOX_SUFFIX):
            title = title[:-len(TERABOX_SUFFIX)]  # Remove the suffix
            logger.info(f"Modified Title: {title}")  # Log the title after modification

        # Try to extract the image from Open Graph meta tag
        image_url = None
        og_image_tag = soup.find('meta', property='og:image')
        if og_image_tag:
            image_url = og_image_tag.get('content')

        if image_url:
            # Fetch the image from the URL asynchronously
            async with session.get(image_url) as img_response:
                img_response.raise_for_status()
                image_data = BytesIO(await img_response.read())
                return title.strip(), image_data
        else:
            return title.strip(), None
    except Exception as e:
        logger.error(f"Error fetching page title or image from URL: {e}")
        return "Error", None

# Function to extract the code from the link
def extract_code_from_url(user_url: str):
    # Extract the part of the URL after "/s/"
    path = urlparse(user_url).path
    if "/s/" in path:
        code = path.split("/s/")[1]
        # Remove the first letter if it is a number
        if code[0].isdigit():
            code = code[1:]
        return code
    return None

# Function to extract all URLs from a given text
def extract_urls(text: str):
    # Ensure text is not None before attempting to split
    if text:
        return [word for word in text.split() if urlparse(word).scheme in ["http", "https"]]
    return []

# Handle messages that contain links
async def handle_message(update: Update, context: CallbackContext) -> None:
    # Extract all URLs from the message text (check if text is not None)
    message_text = update.message.text if update.message.text else ""
    urls = extract_urls(message_text)

    # If message contains URLs, process them concurrently
    if urls:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                # If URL doesn't start with http:// or https://, add https:// by default
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    logger.info(f"Protocol was missing, added https://: {url}")
                
                logger.info(f"Valid URL after adding protocol: {url}")
                
                # Extract code from the URL
                code = extract_code_from_url(url)

                if code:
                    # Construct the new link with the extracted code
                    new_link = f"https://www.1024terabox.com/sharing/embed?surl={code}&resolution=1080&autoplay=true&mute=false&uk=4400105884193&fid=91483455887823&slid="
                    
                    # Create a task for the title and image fetching
                    tasks.append(fetch_title_and_send_image(update, session, url, new_link))
            
            # Run all tasks concurrently
            await asyncio.gather(*tasks)

    else:
        await update.message.reply_text("Please send a valid URL.")

    # Check for URLs in captions of media (ensure caption is not None)
    if update.message.caption:
        caption_urls = extract_urls(update.message.caption)
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in caption_urls:
                # Process the URL the same way as the text URLs
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                logger.info(f"URL from caption: {url}")
                
                # Extract code from the URL
                code = extract_code_from_url(url)

                if code:
                    new_link = f"https://www.1024terabox.com/sharing/embed?surl={code}&resolution=1080&autoplay=true&mute=false&uk=4400105884193&fid=91483455887823&slid="
                    tasks.append(fetch_title_and_send_image(update, session, url, new_link))

            # Run all tasks concurrently
            await asyncio.gather(*tasks)

# Helper function to fetch title, image, and send message
async def fetch_title_and_send_image(update: Update, session, url: str, new_link: str):
    title, image_data = await get_title_and_image(session, url)

    if title.endswith(TERABOX_SUFFIX):
        title = title[:-len(TERABOX_SUFFIX)].strip()

    if image_data:
        await update.message.reply_photo(photo=image_data, caption=f"{title}\n\n{new_link}")
    else:
        await update.message.reply_text(f"{title}\n\n{new_link}")

# Main function to start the bot
