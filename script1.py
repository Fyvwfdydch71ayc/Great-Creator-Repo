import csv
import asyncio
import nest_asyncio
import os  # Import the os module to access environment variables
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ChatJoinRequestHandler
from telegram.error import TelegramError
from telegram.ext import CallbackContext

# Enable nested event loop for Jupyter notebook or other asynchronous environments
nest_asyncio.apply()

# Fetch the ADMIN_ID here
ADMIN_ID = 7464687297  # Replace this with the actual admin user ID (6773787379 as requested)

# GIF URL
gif_url = "https://file-to-link-bot-nx-a4a8eaae5135.herokuapp.com/dl/67289d99cafd64d09ea6d2c0"

# List to store user IDs who interacted with the bot
user_ids = set()  # Using a set to ensure unique user IDs

# Dictionary to store invite links for each chat
invite_links = {}

# Function to save user IDs to CSV
def save_user_ids_to_csv():
    with open('user_ids.csv', mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["User ID"])  # Only User ID in the CSV
        for user_id in user_ids:
            writer.writerow([user_id])

# Define the start command handler
async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    start_message = (
        f"Hi, I'm a group/channel join request accepter bot!\n\n"
        f"Just add me to your group or channel, and I'll accept any join requests instantly.\n"
        f"I'll process your group/channel join requests in just 0.1 second!"
    )
    
    inline_buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("Add Group", url="https://t.me/HotErrorJoinBot?startgroup&admin=invite_users+delete_messages+restrict_members"),
            InlineKeyboardButton("Add Channel", url="https://t.me/HotErrorJoinBot?startchannel&admin=invite_users+delete_messages+restrict_members")
        ]
    ])
    
    await update.message.reply_text(start_message, reply_markup=inline_buttons)

    # Add user ID to the set if not already present
    user_ids.add(user.id)

# Define the chat join request handler
async def approve(update: Update, context: CallbackContext):
    chat = update.chat_join_request.chat  # Correct way to access chat info in chat join requests
    user = update.chat_join_request.from_user  # Access the user who requested to join
    
    try:
        # Approve the join request and send message in parallel
        tasks = [
            context.bot.approve_chat_join_request(chat.id, user.id),
            send_welcome_message(context, user, chat)
        ]
        await asyncio.gather(*tasks)  # Run both tasks concurrently
        
    except TelegramError as e:
        print(f"Error while approving join request: {e}")
    except Exception as err:
        print(str(err))

# Function to send the welcome message
async def send_welcome_message(context: CallbackContext, user, chat):
    # If the invite link for the chat is not already stored, create and store it
    if chat.id not in invite_links:
        invite_url = await context.bot.export_chat_invite_link(chat.id)
        invite_links[chat.id] = invite_url
    else:
        invite_url = invite_links[chat.id]

    # Updated caption with HTML formatting for bold text and mentions
    caption = (
        f"Hello <b><a href='tg://user?id={user.id}'>{user.first_name}</a></b>!\n"
        f"Welcome To <b>{chat.title}</b>\n\n"
        "👇More Spicy Content 🥵🔥\n"
        "<b>@HotError</b>\n"
        "<b>@HotError</b>\n"
        "<b>@HotError</b>"
    )
    
    inline_button = InlineKeyboardMarkup([
        [InlineKeyboardButton(chat.title, url=invite_url)]
    ])
    
    # Send video message with inline button and caption
    await context.bot.send_video(user.id, gif_url, caption=caption, parse_mode="HTML", reply_markup=inline_button)

# Define the detail command handler
async def detail(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        if not invite_links:
            await update.message.reply_text("No groups or channels joined yet.")
        else:
            details_message = "Here are all the groups/channels the bot has joined:\n\n"
            for chat_id, invite_url in invite_links.items():
                chat = await context.bot.get_chat(chat_id)
                details_message += f"**{chat.title}**\nInvite URL: {invite_url}\n\n"
            
            await update.message.reply_text(details_message)
    else:
        await update.message.reply_text("You do not have permission to view this information.")

# Define the id command handler to send CSV
async def send_cv(update: Update, context: CallbackContext):
    user = update.message.from_user
    if user.id == ADMIN_ID:
        save_user_ids_to_csv()  # Save user IDs to CSV
        
        # Send the CSV file to the admin
        with open('user_ids.csv', 'rb') as file:
            await update.message.reply_document(file, caption="Here is the CV file with user IDs.")
    else:
        await update.message.reply_text("You do not have permission to access this data.")

# Define the handle_message function in script1.py
async def handle_message(update: Update, context: CallbackContext):
    user = update.message.from_user
    message_text = update.message.text
    # You can add logic to handle different types of messages
    # For now, let's just reply with the message content
    await update.message.reply_text(f"Hello {user.first_name}, you sent: {message_text}")
