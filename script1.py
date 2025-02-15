import os
import time
import asyncio
import nest_asyncio
import aiohttp
import motor.motor_asyncio
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.constants import ParseMode
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    ChatJoinRequestHandler,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    filters,
)

# ---------------- MongoDB Setup ----------------

MONGODB_URL = "mongodb+srv://wenoobhosttest1:lovedogswetest81@cluster0.4lf5x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGODB_URL)
db = mongo_client["Cluster0"]
invite_links_collection = db["invite_links"]
admin_invite_links_collection = db["admin_invite_links"]
tracked_users_collection = db["tracked_users"]

# ---------------- Global Variables ----------------

ADMIN_ID = 6773787379  # Bot admin ID
first_dev_date = datetime.now()  # Record first development date

#BOT_TOKEN = "7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0"

# File path and URL for the welcome video (our "GIF")
GIF_FILE_PATH = "welcome_video.mp4"
GIF_DOWNLOAD_URL = (
    "https://api.telegram.org/file/bot7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0/animations/file_157.mp4"
)

# ---------------- Helper Functions ----------------

async def download_gif():
    """Download the video file once and save it locally."""
    if not os.path.exists(GIF_FILE_PATH):
        print("Downloading GIF file...")
        async with aiohttp.ClientSession() as session:
            async with session.get(GIF_DOWNLOAD_URL) as response:
                if response.status == 200:
                    content = await response.read()
                    with open(GIF_FILE_PATH, "wb") as f:
                        f.write(content)
                    print("GIF downloaded and saved.")
                else:
                    print("Failed to download GIF, status:", response.status)
    else:
        print("GIF file already exists. Skipping download.")

async def track_user(user, timestamp: datetime):
    """Record the user in MongoDB if not already tracked."""
    if user and user.id:
        existing = await tracked_users_collection.find_one({"user_id": user.id})
        if not existing:
            await tracked_users_collection.insert_one({
                "user_id": user.id,
                "first_interaction": timestamp
            })

async def send_welcome_message(context: CallbackContext, user, chat):
    """
    For the given chat, create (or retrieve) two invite links:
      - The admin approval invite link (creates_join_request=True) used in the welcome message.
      - The non-admin approval invite link (creates_join_request=False) stored for the admin /grp command.
    Then send a welcome video with an inline button using the admin approval link.
    """
    # Retrieve or create the admin approval invite link.
    admin_invite = await invite_links_collection.find_one({"chat_id": chat.id})
    if not admin_invite:
        try:
            admin_invite_link_obj = await context.bot.create_chat_invite_link(
                chat.id,
                creates_join_request=True,
                expire_date=None,
                member_limit=0
            )
            admin_invite = {
                "chat_id": chat.id,
                "invite_link": admin_invite_link_obj.invite_link,
                "chat_title": chat.title
            }
            await invite_links_collection.insert_one(admin_invite)
            print(f"Created admin approval invite link for chat {chat.id}: {admin_invite_link_obj.invite_link}")
        except TelegramError as e:
            print(f"Error creating admin approval invite link: {e}")
            return
    admin_approval_invite_url = admin_invite["invite_link"]

    # Retrieve or create the non-admin approval invite link.
    non_admin_invite = await admin_invite_links_collection.find_one({"chat_id": chat.id})
    if not non_admin_invite:
        try:
            non_admin_invite_link_obj = await context.bot.create_chat_invite_link(
                chat.id,
                creates_join_request=False,
                expire_date=None,
                member_limit=0
            )
            non_admin_invite = {
                "chat_id": chat.id,
                "invite_link": non_admin_invite_link_obj.invite_link,
                "chat_title": chat.title
            }
            await admin_invite_links_collection.insert_one(non_admin_invite)
            print(f"Created non-admin approval invite link for chat {chat.id}: {non_admin_invite_link_obj.invite_link}")
        except TelegramError as e:
            print(f"Error creating non-admin approval invite link: {e}")
            return

    caption = (
        f"Hello <b><a href='tg://user?id={user.id}'>{user.first_name}</a></b>!\n"
        f"Welcome To <b><a href='{admin_approval_invite_url}'>{chat.title}</a></b>\n\n"
        "👇More Spicy Content 🥵🔥\n"
        "<b>@HotError</b>\n"
        "<b>@HotError</b>\n"
        "<b>@HotError</b>"
    )

    inline_button = InlineKeyboardMarkup([
        [InlineKeyboardButton(chat.title, url=admin_approval_invite_url)]
    ])

    with open(GIF_FILE_PATH, "rb") as video_file:
        await context.bot.send_video(
            chat_id=user.id,
            video=video_file,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_button
        )

# ---------------- Handlers ----------------

async def approve(update: Update, context: CallbackContext):
    """
    Approve join requests and send a welcome message.
    Approves the join request immediately, then sends the welcome video as a background task.
    Also records the user interaction.
    """
    chat = update.chat_join_request.chat
    user = update.chat_join_request.from_user
    await track_user(user, datetime.now())
    try:
        await context.bot.approve_chat_join_request(chat.id, user.id)
    except TelegramError as e:
        print(f"Error approving join request: {e}")
        return

    asyncio.create_task(send_welcome_message(context, user, chat))

async def start(update: Update, context: CallbackContext):
    """Send a start message with inline buttons for group/channel installation."""
    await track_user(update.effective_user, datetime.now())
    text = (
        "Hi, I'm a group/channel join request accepter bot!\n\n"
        "Just add me to your group or channel, and I'll accept any join requests instantly.\n"
        "I'll process your group/channel join requests in just 0.1 second!"
    )
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                "Add to Group",
                url="https://t.me/HotErrorJoinBot?startgroup&admin=change_info+delete_messages+invite_users+restrict_members+pin_messages+promote_members+manage_voice_chats+manage_video_chats"
            ),
            InlineKeyboardButton(
                "Add to Channel",
                url="https://t.me/HotErrorJoinBot?startchannel&admin=change_info+post_messages+edit_messages+delete_messages+invite_users+restrict_members+pin_messages+promote_members+manage_voice_chats+manage_video_chats+manage_live_stream+manage_stories"
            )
        ]
    ])
    await update.message.reply_text(text, reply_markup=keyboard)

async def more_spicy(update: Update, context: CallbackContext):
    """Reply to any non-command text message with a spicy fun message."""
    await track_user(update.effective_user, datetime.now())
    text = "Get More Spicy Fun Here😍🌶️👇"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Spicy Links", url="https://t.me/hoterrorlinks")]
    ])
    await update.message.reply_text(text, reply_markup=keyboard)

async def admin_users(update: Update, context: CallbackContext):
    """Show user statistics (admin-only)."""
    if update.effective_user.id != ADMIN_ID:
        return  # Ignore non-admin requests.
    
    await track_user(update.effective_user, datetime.now())
    now = datetime.now()
    total_users = await tracked_users_collection.count_documents({})
    # Count today's users starting from midnight.
    start_of_day = datetime(now.year, now.month, now.day)
    today_users = await tracked_users_collection.count_documents({"first_interaction": {"$gte": start_of_day}})
    last_week_users = await tracked_users_collection.count_documents({"first_interaction": {"$gte": now - timedelta(days=7)}})
    last_month_users = await tracked_users_collection.count_documents({"first_interaction": {"$gte": now - timedelta(days=30)}})
    first_dev = first_dev_date.strftime("%Y-%m-%d %H:%M:%S")

    stats = (
        f"Total Users: {total_users}\n"
        f"Today's Users: {today_users}\n"
        f"Last 7 Days: {last_week_users}\n"
        f"Last 30 Days: {last_month_users}\n"
        f"First Development Date: {first_dev}"
    )
    await update.message.reply_text(stats)

async def admin_grp(update: Update, context: CallbackContext):
    """Send a numbered list of groups/channels with non-admin approval invite links (admin-only)."""
    if update.effective_user.id != ADMIN_ID:
        return  # Ignore non-admin requests.

    await track_user(update.effective_user, datetime.now())
    cursor = admin_invite_links_collection.find({})
    lines = []
    i = 1
    async for doc in cursor:
        invite_url = doc.get("invite_link", "")
        chat_title = doc.get("chat_title", "")
        lines.append(f"({i}) {chat_title} - {invite_url}")
        i += 1
    if not lines:
        await update.message.reply_text("No groups or channels available yet.")
        return

    message_text = "\n".join(lines)
    MAX_LENGTH = 4000
    if len(message_text) <= MAX_LENGTH:
        await update.message.reply_text(message_text)
    else:
        chunk = ""
        for line in lines:
            if len(chunk) + len(line) + 1 > MAX_LENGTH:
                await update.message.reply_text(chunk)
                chunk = line + "\n"
            else:
                chunk += line + "\n"
        if chunk:
            await update.message.reply_text(chunk)

async def track_user_handler(update: Update, context: CallbackContext):
    """A global pre-processor to record every user's first interaction."""
    if update.effective_user:
        await track_user(update.effective_user, datetime.now())

# ---------- Forward Private Chat Messages ----------

async def forward_private_message(update: Update, context: CallbackContext):
    """
    For messages sent in private chat:
      - Copy the message to channel -1002399068205,
      - But ignore pure command messages (e.g. "/start" with no extra text).
    """
    msg = update.effective_message
    if not msg or update.effective_chat.type != "private":
        return

    if msg.text:
        text = msg.text.strip()
        if text.startswith("/") and (" " not in text):
            return

    try:
        await context.bot.copy_message(
            chat_id=-1002399068205,
            from_chat_id=msg.chat.id,
            message_id=msg.message_id
        )
    except Exception as e:
        print(f"Error copying user message: {e}")

# ---------- Broadcast Channel Messages to All Users with Summary ----------

async def broadcast_channel_message(update: Update, context: CallbackContext):
    """
    When a new message is posted in channel -1002374713796,
    copy that message (including any inline URL buttons if present) to every tracked user.
    After broadcasting, send a summary to the admin.
    """
    msg = update.effective_message
    if not msg or update.effective_chat.id != -1002374713796:
        return

    reply_markup = msg.reply_markup if msg.reply_markup else None
    start_time = time.perf_counter()
    tasks = []
    
    # Retrieve all tracked users from MongoDB.
    cursor = tracked_users_collection.find({})
    async for user_doc in cursor:
        user_id = user_doc.get("user_id")
        tasks.append(
            context.bot.copy_message(
                chat_id=user_id,
                from_chat_id=msg.chat.id,
                message_id=msg.message_id,
                reply_markup=reply_markup
            )
        )
    if tasks:
        results = await asyncio.gather(*tasks, return_exceptions=True)
        end_time = time.perf_counter()
        duration = end_time - start_time
        successful = sum(1 for result in results if not isinstance(result, Exception))
        unsuccessful = sum(1 for result in results if isinstance(result, Exception))
        total_users = await tracked_users_collection.count_documents({})
        summary = (
            f"Broadcast Summary:\n"
            f"Total Users: {total_users}\n"
            f"Successful: {successful}\n"
            f"Unsuccessful: {unsuccessful}\n"
            f"Total Time: {duration:.2f} seconds"
        )
        try:
            await context.bot.send_message(chat_id=ADMIN_ID, text=summary)
        except Exception as e:
            print(f"Error sending broadcast summary: {e}")

# ---------------- Main Function ----------------

