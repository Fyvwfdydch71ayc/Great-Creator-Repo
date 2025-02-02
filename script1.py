import logging
import asyncio
from telegram import Update
from telegram.ext import CallbackContext
from urllib.parse import urlparse
import aiohttp
from bs4 import BeautifulSoup
from io import BytesIO

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Constant for the part to remove from the title
TERABOX_SUFFIX = " - Share Files Online & Send Larges Files with TeraBox"

# Function to fetch the title, image, and text of a webpage asynchronously
async def get_title_and_image_and_text(session, url: str):
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

        # Extract text from the page (just the main content)
        text_content = ''
        for p_tag in soup.find_all('p'):  # This is a simple way to extract paragraphs
            text_content += p_tag.get_text() + "\n"

        if image_url:
            # Fetch the image from the URL asynchronously
            async with session.get(image_url) as img_response:
                img_response.raise_for_status()
                image_data = BytesIO(await img_response.read())
                return title.strip(), image_data, text_content.strip()
        else:
            return title.strip(), None, text_content.strip()
    except Exception as e:
        logger.error(f"Error fetching page title, image or text from URL: {e}")
        return "Error", None, ""

# Function to extract the code from the link
def extract_code_from_url(user_url: str):
    path = urlparse(user_url).path
    if "/s/" in path:
        code = path.split("/s/")[1]
        if code[0].isdigit():
            code = code[1:]
        return code
    return None

# Function to extract all URLs from a given text
def extract_urls(text: str):
    if text:
        return [word for word in text.split() if urlparse(word).scheme in ["http", "https"]]
    return []

# Handle messages that contain links
async def handle_message(update: Update, context: CallbackContext) -> None:
    message_text = update.message.text if update.message.text else ""
    urls = extract_urls(message_text)

    if urls:
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in urls:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                    logger.info(f"Protocol was missing, added https://: {url}")
                
                logger.info(f"Valid URL after adding protocol: {url}")
                
                code = extract_code_from_url(url)
                if code:
                    new_link = f"https://www.1024terabox.com/sharing/embed?surl={code}&resolution=1080&autoplay=true&mute=false&uk=4400105884193&fid=91483455887823&slid="
                    tasks.append(fetch_title_and_send_image(update, session, url, new_link))

            await asyncio.gather(*tasks)
    else:
        await update.message.reply_text("Please send a valid URL.")

    if update.message.caption:
        caption_urls = extract_urls(update.message.caption)
        tasks = []
        async with aiohttp.ClientSession() as session:
            for url in caption_urls:
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                logger.info(f"URL from caption: {url}")
                
                code = extract_code_from_url(url)
                if code:
                    new_link = f"https://www.1024terabox.com/sharing/embed?surl={code}&resolution=1080&autoplay=true&mute=false&uk=4400105884193&fid=91483455887823&slid="
                    tasks.append(fetch_title_and_send_image(update, session, url, new_link))

            await asyncio.gather(*tasks)

# Helper function to fetch title, image, text, and send the message
async def fetch_title_and_send_image(update: Update, session, url: str, new_link: str):
    title, image_data, text_content = await get_title_and_image_and_text(session, url)

    if title.endswith(TERABOX_SUFFIX):
        title = title[:-len(TERABOX_SUFFIX)].strip()

    # Prepare the message with the original link and the new link
    message = f"{title}\n\n{new_link}\n\n{url}\n\n{text_content}"

    if image_data:
        await update.message.reply_photo(photo=image_data, caption=message)
    else:
        await update.message.reply_text(message)
