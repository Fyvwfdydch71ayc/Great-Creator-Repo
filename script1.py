import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.ext import ContextTypes
#import nest_asyncio
import re

# Enable asyncio support in Jupyter notebook
#nest_asyncio.apply()

# Enable logging to track issues or errors
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a global dictionary to store user links and a flag for /done state
user_links = {}
user_done = {}

# Define a function to extract links containing "/s/"
def extract_links(text: str):
    # Regular expression to match URLs with "/s/"
    url_pattern = r'https?://(?:www\.)?[a-zA-Z0-9./?=&_-]+/s/[a-zA-Z0-9_-]+'
    return re.findall(url_pattern, text)

# Command handler to start the bot
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Hello! Send me any media or text containing links with "/s/", and I will extract them for you. Type /done to get the final list.')

# Handler to extract links from messages
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    # Check if the user has already done /done and reset their list if so
    if user_id in user_done and user_done[user_id]:
        # If /done has been executed before, start a new list for the user
        user_links[user_id] = []
        user_done[user_id] = False  # Reset the /done state

    # Extract links from text or media caption
    links = []
    if update.message.text:
        links.extend(extract_links(update.message.text))

    # Check for links in media captions (photo, video, document, etc.)
    caption = update.message.caption or ""
    links.extend(extract_links(caption))

    if links:
        if user_id not in user_links:
            user_links[user_id] = []
        
        # Only add the link if it's not already in the user's list
        for link in links:
            if link not in user_links[user_id]:
                user_links[user_id].append(link)

# Command handler to return a numbered list of links
async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id

    if user_id in user_links and user_links[user_id]:
        # Create the response as a numbered list
        response = "\n".join([f"({i+1}) {link}" for i, link in enumerate(user_links[user_id])])

        # Split the response into parts if it's too long, ensuring no links are cut off
        max_message_length = 4096
        current_message = ""
        for link in response.split("\n"):
            # Check if adding this link will exceed the max length
            if len(current_message) + len(link) + 1 <= max_message_length:
                if current_message:
                    current_message += "\n" + link
                else:
                    current_message = link
            else:
                # Send the current message, then start a new one with the next link
                await update.message.reply_text(current_message)
                current_message = link  # Start new message with this link

        # Send the last message part if any remains
        if current_message:
            await update.message.reply_text(current_message)

        user_done[user_id] = True  # Mark that the user has completed /done
    else:
        await update.message.reply_text("You haven't sent me any links yet.")
