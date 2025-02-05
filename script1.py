import asyncio
import csv
import io
import logging
import re
import uuid
import urllib.parse
from datetime import datetime, timedelta

#import nest_asyncio
from motor.motor_asyncio import AsyncIOMotorClient
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, Message, WebAppInfo
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters
)

#nest_asyncio.apply()

# ------------------------------
# MongoDB Connections and Collections
# ------------------------------

# For subscription details and user usage:
subscription_client = AsyncIOMotorClient(
    "mongodb+srv://wenoobhost1:WBOEXfFslsyXY1nN@cluster0.7ioby.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
subscription_db = subscription_client["Cluster0"]
sub_collection = subscription_db["subscriptions"]       # Will store all subscriptions (a single document with _id="subscriptions")
user_usage_collection = subscription_db["user_usage"]     # Will store user usage (document _id="user_usage")

# For all other data:
other_client = AsyncIOMotorClient(
    "mongodb+srv://wenoobhosttest1:lovedogswetest81@cluster0.4lf5x.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"
)
other_db = other_client["Cluster0"]
param_links_collection = other_db["param_links"]                    # document _id="param_links"
website_db_collection = other_db["website_db"]                      # document _id="website_db"
daily_param_links_counter_collection = other_db["daily_param_links_counter"]  # document _id="daily_param_links_counter"
daily_users_set_collection = other_db["daily_users_set"]              # document _id="daily_users_set"

# ------------------------------
# Global Variables (loaded from Mongo)
# ------------------------------
subscriptions = {}        # { user_id (str): { "purchased": datetime, "expiry": datetime, "expired_notified": bool, "plan": "full"|"limited", "upgraded": bool } }
user_usage = {}           # { user_id (str): { "date": "YYYY-MM-DD", "links": [link_id, ...] } }
website_db = {"current": "https://google.com/"}  # Base URL for mini apps.
param_links = {}          # { link_id: {"start": int, "end": int, "created": datetime, "urls": [...], "messages": [...] } }
daily_param_links_counter = {}  # {date_string: int}
daily_users_set = set()         # set of user_id (str)

pending_deletes = []  # List of dicts: {'chat_id': int, 'message_id': int, 'task': Task}
all_users = set()     # set of user_id (int)

# ------------------------------
# Other Settings and State
# ------------------------------
#BOT_TOKEN = "7660007316:AAHis4NuPllVzH-7zsYhXGfgokiBxm_Tml0"
DB_CHANNEL = -1002479661811
ADMIN_ID = 6773787379
SUBS_CHANNEL = -1002278982228         # Full Premium subscription channel
LIMITED_SUBS_CHANNEL = -1002486162221   # Limited Premium subscription channel (3 links/day)
UPGRADE_CHANNEL = -1002429251851        # Channel to upgrade limited to unlimited
BROADCAST_CHANNEL = -1002449407667

# Required channels
REQUIRED_CHANNELS = [-1002434409634, -1002315588145]
INVITE_LINKS = {
    -1002434409634: "https://t.me/+h7ICg0eD7gQxZmE0",
    -1002315588145: "https://t.me/+tCyah29hMTtjNTBk",
}

auto_delete_timer = 3600  # seconds
subscription_function_enabled = True  # when ON, non‑premium users are limited
subscription_off_start = None         # timestamp when subscription function was turned off

# Conversation states
FIRST_POST, LAST_POST = range(2)

# ------------------------------
# Logging
# ------------------------------
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ------------------------------
# MongoDB Persistence Functions
# ------------------------------
async def load_data():
    global subscriptions, user_usage, website_db, param_links, daily_param_links_counter, daily_users_set
    # Load subscriptions:
    doc = await sub_collection.find_one({"_id": "subscriptions"})
    subscriptions = doc.get("data", {}) if doc else {}
    # Load user usage:
    doc = await user_usage_collection.find_one({"_id": "user_usage"})
    user_usage = doc.get("data", {}) if doc else {}

    # Load other data:
    doc = await website_db_collection.find_one({"_id": "website_db"})
    website_db = doc.get("data", {"current": "https://google.com/"}) if doc else {"current": "https://google.com/"}

    doc = await param_links_collection.find_one({"_id": "param_links"})
    param_links = doc.get("data", {}) if doc else {}

    doc = await daily_param_links_counter_collection.find_one({"_id": "daily_param_links_counter"})
    daily_param_links_counter = doc.get("data", {}) if doc else {}

    doc = await daily_users_set_collection.find_one({"_id": "daily_users_set"})
    daily_users_set = set(doc.get("data", [])) if doc else set()

async def save_data():
    # Save subscription data:
    await sub_collection.replace_one({"_id": "subscriptions"}, {"_id": "subscriptions", "data": subscriptions}, upsert=True)
    await user_usage_collection.replace_one({"_id": "user_usage"}, {"_id": "user_usage", "data": user_usage}, upsert=True)
    # Save other data:
    await website_db_collection.replace_one({"_id": "website_db"}, {"_id": "website_db", "data": website_db}, upsert=True)
    await param_links_collection.replace_one({"_id": "param_links"}, {"_id": "param_links", "data": param_links}, upsert=True)
    await daily_param_links_counter_collection.replace_one(
        {"_id": "daily_param_links_counter"}, {"_id": "daily_param_links_counter", "data": daily_param_links_counter}, upsert=True)
    await daily_users_set_collection.replace_one(
        {"_id": "daily_users_set"}, {"_id": "daily_users_set", "data": list(daily_users_set)}, upsert=True)

# ------------------------------
# Helper Functions (unchanged)
# ------------------------------
def get_today_str() -> str:
    return datetime.now().strftime("%Y-%m-%d")

def extract_post_id(message: Message) -> int:
    if message.forward_from_chat and message.forward_from_chat.id == DB_CHANNEL:
        return message.forward_from_message_id
    return None

def split_message(text: str, max_length: int = 4000) -> list:
    lines = text.split("\n")
    parts = []
    current = ""
    for line in lines:
        if len(current) + len(line) + 1 > max_length:
            parts.append(current)
            current = line
        else:
            current = current + "\n" + line if current else line
    if current:
        parts.append(current)
    return parts

def create_url_buttons(text: str) -> InlineKeyboardMarkup:
    urls = re.findall(r'(https?://\S+)', text)
    buttons = []
    for url in urls:
        parsed = urllib.parse.urlparse(url)
        domain = parsed.netloc
        if domain:
            buttons.append([InlineKeyboardButton(domain, url=url)])
    return InlineKeyboardMarkup(buttons) if buttons else None

def create_custom_url_buttons(text: str) -> (str, InlineKeyboardMarkup):
    pattern = re.compile(r'(\S+?)=(https?://\S+)')
    buttons = []
    for label, url in pattern.findall(text):
        buttons.append([InlineKeyboardButton(label, url=url)])
    cleaned_text = pattern.sub('', text).strip()
    inline_markup = InlineKeyboardMarkup(buttons) if buttons else None
    return cleaned_text, inline_markup

# ------------------------------
# Sending Stored Parameter-Link Messages
# ------------------------------
async def send_stored_message(user_id: int, msg_data: dict, context: ContextTypes.DEFAULT_TYPE):
    original_content = msg_data.get("original", "")
    old_base = msg_data.get("website", "https://google.com/").rstrip('/')
    new_base = website_db["current"].rstrip('/')
    inline_buttons = []
    pattern = re.compile(rf"({re.escape(old_base)}/\S*)")
    for match in pattern.finditer(original_content):
        old_url = match.group(1)
        suffix = old_url[len(old_base):]
        new_url = new_base + suffix
        mini_app_button = InlineKeyboardButton("Open Mini App", web_app=WebAppInfo(url=new_url))
        url_button = InlineKeyboardButton("Open Link", url=new_url)
        inline_buttons.append([mini_app_button])
        inline_buttons.append([url_button])
    inline_markup = InlineKeyboardMarkup(inline_buttons) if inline_buttons else None

    if msg_data["type"] == "text":
        cleaned_text = re.sub(r'https?://\S+', '', msg_data["text"]).strip()
        if not cleaned_text:
            cleaned_text = " "
        sent_msg = await context.bot.send_message(
            chat_id=user_id,
            text=cleaned_text,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_markup,
            protect_content=True
        )
    elif msg_data["type"] == "photo":
        cleaned_caption = re.sub(r'https?://\S+', '', msg_data["caption"]).strip()
        if not cleaned_caption:
            cleaned_caption = " "
        sent_msg = await context.bot.send_photo(
            chat_id=user_id,
            photo=msg_data["file_id"],
            caption=cleaned_caption,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_markup,
            protect_content=True
        )
    elif msg_data["type"] == "video":
        cleaned_caption = re.sub(r'https?://\S+', '', msg_data["caption"]).strip()
        if not cleaned_caption:
            cleaned_caption = " "
        sent_msg = await context.bot.send_video(
            chat_id=user_id,
            video=msg_data["file_id"],
            caption=cleaned_caption,
            parse_mode=ParseMode.HTML,
            reply_markup=inline_markup,
            protect_content=True
        )
    else:
        sent_msg = await context.bot.send_message(
            chat_id=user_id,
            text="(Unsupported message type)",
            parse_mode=ParseMode.HTML,
            protect_content=True
        )
    asyncio.create_task(delete_later(context, user_id, sent_msg.message_id))

# ------------------------------
# Parameter Link Handlers and Other Bot Commands
# (Most of these functions remain largely unchanged,
#  except that calls to save_data() are now awaited.)
# ------------------------------

async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    daily_users_set.add(str(user.id))
    args = context.args
    if args:
        await handle_parameter_link(update, context)
        return
    if user.id == ADMIN_ID:
        text = ("🛠 Admin Commands:\n"
                "/betch - Create batch\n"
                "/links - View links\n"
                "/website - Manage website\n"
                "/setting - Manage settings\n"
                "/export - Export data as CSV\n"
                "/users - View user stats\n"
                "/plan - View your subscription plan\n"
                "/user {userid} - View user details")
    else:
        text = "💋 Get more categories 👇"
        keyboard = [[InlineKeyboardButton("Join - HotError", url="https://t.me/HotError")]]
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    await update.message.reply_text(text)

async def betch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    all_users.add(update.effective_user.id)
    await update.message.reply_text("Please forward the FIRST post from the channel:")
    return FIRST_POST

async def process_first_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    all_users.add(update.effective_user.id)
    post_id = extract_post_id(update.message)
    if not post_id:
        await update.message.reply_text("Invalid post. Forward from the database channel only. Try /betch again.")
        return ConversationHandler.END
    context.user_data['first_post'] = post_id
    await update.message.reply_text("Now forward the LAST post:")
    return LAST_POST

async def process_last_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global daily_param_links_counter
    all_users.add(update.effective_user.id)
    post_id = extract_post_id(update.message)
    if not post_id:
        await update.message.reply_text("Invalid post. Forward from the database channel only. Try /betch again.")
        return ConversationHandler.END
    context.user_data['last_post'] = post_id
    first_id = context.user_data['first_post']
    last_id = context.user_data['last_post']
    start_id = min(first_id, last_id)
    end_id = max(first_id, last_id)
    link_id = str(uuid.uuid4())[:8]
    param_links[link_id] = {
        'start': start_id,
        'end': end_id,
        'created': datetime.now(),
        'urls': [],
        'messages': []
    }
    urls_set = set()
    messages_list = []
    for msg_id in range(start_id, end_id + 1):
        try:
            forwarded = await context.bot.forward_message(
                chat_id=ADMIN_ID,
                from_chat_id=DB_CHANNEL,
                message_id=msg_id
            )
            msg_data = None
            if forwarded.text:
                msg_data = {"type": "text", "text": forwarded.text}
            elif forwarded.caption:
                if forwarded.photo:
                    msg_data = {"type": "photo", "file_id": forwarded.photo[-1].file_id, "caption": forwarded.caption}
                elif forwarded.video:
                    msg_data = {"type": "video", "file_id": forwarded.video.file_id, "caption": forwarded.caption}
                else:
                    msg_data = {"type": "text", "text": forwarded.caption}
            if msg_data:
                msg_data["website"] = website_db["current"]
                if msg_data["type"] == "text":
                    msg_data["original"] = msg_data["text"]
                else:
                    msg_data["original"] = msg_data.get("caption", "")
                found_urls = re.findall(r'https?://\S+', msg_data["original"])
                urls_set.update(found_urls)
                messages_list.append(msg_data)
            await context.bot.delete_message(chat_id=ADMIN_ID, message_id=forwarded.message_id)
        except Exception as e:
            logger.error(f"Error fetching message {msg_id}: {e}")
    param_links[link_id]["urls"] = list(urls_set)
    param_links[link_id]["messages"] = messages_list
    today = get_today_str()
    daily_param_links_counter[today] = daily_param_links_counter.get(today, 0) + 1
    await save_data()
    link = f"https://t.me/{context.bot.username}?start={link_id}"
    await update.message.reply_text(
        f"✅ Batch created!\nParameter Link: {link}\nFound {len(urls_set)} URL(s) in {len(messages_list)} message(s)."
    )
    return ConversationHandler.END

async def handle_parameter_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    daily_users_set.add(str(user.id))
    args = context.args
    if not args or args[0] not in param_links:
        await update.message.reply_text("Invalid link!")
        return
    missing = await check_required_channels(user.id, context)
    if missing:
        buttons = []
        for idx, ch in enumerate(missing, start=1):
            buttons.append([InlineKeyboardButton(f"Join Channel {idx}", url=INVITE_LINKS.get(ch, "https://t.me/"))])
        try_again_url = f"https://t.me/{context.bot.username}?start={args[0]}"
        buttons.append([InlineKeyboardButton("Try Again", url=try_again_url)])
        text = "🚫 You must join the following channels to use this bot:"
        await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
        return
    now = datetime.now()
    uid = str(user.id)
    if uid in subscriptions and subscriptions[uid]["expiry"] > now:
        plan = subscriptions[uid].get("plan", "full")
    else:
        plan = "basic"
    if plan == "full":
        allowed_links = None
    elif plan == "limited":
        allowed_links = 3
    else:
        allowed_links = 1
    if allowed_links is not None and user.id != ADMIN_ID:
        current_link_id = args[0]
        today_str = get_today_str()
        usage = user_usage.get(uid)
        if usage and usage.get("date") == today_str:
            links_used = usage.get("links", [])
            if current_link_id not in links_used:
                if len(links_used) >= allowed_links:
                    if plan == "limited":
                        keyboard = [[InlineKeyboardButton("Renew", url="https://t.me/renew")]]
                        message = ("🚫 Your limited subscription limit has exceeded (3/3). "
                                   "You can't convert limited subscription to Unlimited now.")
                        await update.message.reply_text(message, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.HTML)
                        return
                    else:
                        keyboard = [[InlineKeyboardButton("Pay 💸", url="https://t.me/pay")]]
                        message = "🚫 You've exceeded your daily limit of 1 unique link.\nUpgrade to Premium for unlimited access!"
                        mention = f"<a href='tg://user?id={user.id}'>{user.first_name}</a>"
                        await update.message.reply_text(
                            f"⚠️ Attention, {mention}! ⚠️\n\n{message}",
                            reply_markup=InlineKeyboardMarkup(keyboard),
                            parse_mode=ParseMode.HTML
                        )
                        return
                else:
                    links_used.append(current_link_id)
            user_usage[uid] = {"date": today_str, "links": links_used}
        else:
            user_usage[uid] = {"date": today_str, "links": [current_link_id]}
        await save_data()
    link_data = param_links[args[0]]
    for msg_data in link_data.get("messages", []):
        try:
            await send_stored_message(user.id, msg_data, context)
        except Exception as e:
            logger.error(f"Error sending stored message: {e}")

async def list_links(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    all_users.add(update.effective_user.id)
    if not param_links:
        await update.message.reply_text("No links created yet.")
        return
    lines = []
    for idx, (lid, data) in enumerate(param_links.items(), 1):
        link = f"https://t.me/{context.bot.username}?start={lid}"
        lines.append(f"({idx}) {link} | Posts {data['start']}-{data['end']} | URLs: {len(data.get('urls', []))}")
    text = "\n".join(lines)
    for part in split_message(text):
        await update.message.reply_text(part)

async def broadcast_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.channel_post:
        return
    cp = update.channel_post
    if cp.text:
        msg_type = "text"
        content = cp.text
    elif cp.caption:
        if cp.photo:
            msg_type = "photo"
            content = cp.caption
        elif cp.video:
            msg_type = "video"
            content = cp.caption
        else:
            msg_type = "text"
            content = cp.caption
    else:
        return
    cleaned_content, inline_markup = create_custom_url_buttons(content)
    if not cleaned_content:
        cleaned_content = " "
    success_count = 0
    failure_count = 0
    for user_id in list(all_users):
        try:
            if msg_type == "text":
                await context.bot.send_message(
                    chat_id=user_id,
                    text=cleaned_content,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
            elif msg_type == "photo":
                file_id = cp.photo[-1].file_id
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=file_id,
                    caption=cleaned_content,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
            elif msg_type == "video":
                file_id = cp.video.file_id
                await context.bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=cleaned_content,
                    parse_mode=ParseMode.HTML,
                    reply_markup=inline_markup
                )
            success_count += 1
        except Exception as e:
            logger.error(f"Error broadcasting to user {user_id}: {e}")
            failure_count += 1
    summary = (f"Broadcast complete.\nSuccessfully sent: {success_count}\nFailed: {failure_count}")
    await context.bot.send_message(chat_id=ADMIN_ID, text=summary)

async def setting_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    buttons = [
        [InlineKeyboardButton("Auto Timer ⏳", callback_data="setting_auto_timer")],
        [InlineKeyboardButton("Subscriptions Function 💻", callback_data="setting_subscription")],
        [InlineKeyboardButton("Freeze 🥶", callback_data="setting_freeze")]
    ]
    await update.message.reply_text("⚙️ Settings:", reply_markup=InlineKeyboardMarkup(buttons))

async def export_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    files_to_send = []
    subs_io = io.StringIO()
    subs_writer = csv.writer(subs_io)
    subs_writer.writerow(["user_id", "purchased", "expiry", "expired_notified", "plan", "upgraded"])
    for uid, data in subscriptions.items():
        subs_writer.writerow([uid,
                              data["purchased"].strftime("%Y-%m-%d %H:%M:%S"),
                              data["expiry"].strftime("%Y-%m-%d %H:%M:%S"),
                              data.get("expired_notified", False),
                              data.get("plan", "full"),
                              data.get("upgraded", False)])
    subs_io.seek(0)
    subs_bytes = io.BytesIO(subs_io.getvalue().encode('utf-8'))
    subs_bytes.name = "subscriptions.csv"
    files_to_send.append(subs_bytes)
    links_io = io.StringIO()
    links_writer = csv.writer(links_io)
    links_writer.writerow(["link_id", "start", "end", "created", "num_urls", "num_messages"])
    for lid, data in param_links.items():
        links_writer.writerow([lid, data["start"], data["end"],
                               data["created"].strftime("%Y-%m-%d %H:%M:%S"),
                               len(data.get("urls", [])),
                               len(data.get("messages", []))])
    links_io.seek(0)
    links_bytes = io.BytesIO(links_io.getvalue().encode('utf-8'))
    links_bytes.name = "param_links.csv"
    files_to_send.append(links_bytes)
    usage_io = io.StringIO()
    usage_writer = csv.writer(usage_io)
    usage_writer.writerow(["user_id", "usage"])
    for uid, data in user_usage.items():
        usage_writer.writerow([uid, data])
    usage_io.seek(0)
    usage_bytes = io.BytesIO(usage_io.getvalue().encode('utf-8'))
    usage_bytes.name = "user_usage.csv"
    files_to_send.append(usage_bytes)
    for f in files_to_send:
        await context.bot.send_document(chat_id=ADMIN_ID, document=f)
    await update.message.reply_text("✅ Data exported as CSV files.")

async def admin_user_details(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    text = update.message.text.strip()
    parts = text.split()
    if len(parts) < 2:
        await update.message.reply_text("Usage: /user {userid}")
        return
    target_id = parts[1]
    try:
        chat = await context.bot.get_chat(int(target_id))
        first_name = chat.first_name
        mention = f"<a href='tg://user?id={target_id}'>{first_name}</a>"
    except Exception as e:
        logger.error(f"Error mentioning user {target_id}: {e}")
        first_name = target_id
        mention = target_id
    sub_info = ""
    if target_id in subscriptions:
        sub = subscriptions[target_id]
        now = datetime.now()
        active = "Active" if sub["expiry"] > now else "Expired"
        sub_info = (f"Subscription:\n"
                    f"  Plan: {sub.get('plan', 'full')}\n"
                    f"  Purchased: {sub['purchased'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"  Expires: {sub['expiry'].strftime('%Y-%m-%d %H:%M')}\n"
                    f"  Status: {active}\n")
        if sub.get("plan") == "limited":
            today_str = get_today_str()
            usage = user_usage.get(target_id, {})
            used = len(usage.get("links", [])) if usage.get("date") == today_str else 0
            sub_info += f"  Links used today: {used}/3\n"
        if sub.get("upgraded"):
            sub_info += "  (You upgraded your limited subscription to Unlimited!)\n"
    else:
        sub_info = "No active subscription."
    usage_info = ""
    if target_id in user_usage:
        usage_info = f"Usage: {user_usage[target_id]}"
    else:
        usage_info = "No usage history."
    details = (f"User Details for {mention}:\n"
               f"User ID: {target_id}\n"
               f"{sub_info}\n"
               f"{usage_info}")
    buttons = []
    now = datetime.now()
    if target_id in subscriptions and subscriptions[target_id]["expiry"] > now:
        buttons.append([InlineKeyboardButton("Cancel Subscription", callback_data=f"cancel_sub_{target_id}")])
    await update.message.reply_text(details, parse_mode=ParseMode.HTML,
                                    reply_markup=InlineKeyboardMarkup(buttons) if buttons else None)

async def website_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    all_users.add(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("Change Website", callback_data='change_website')]]
    await update.message.reply_text(
        f"🌐 Current Website: {website_db['current']}",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global auto_delete_timer, subscription_function_enabled, pending_deletes, subscription_off_start
    query = update.callback_query
    await query.answer()
    data = query.data
    if data.startswith("cancel_sub_"):
        target_id = data.split("_")[-1]
        text = f"Are you sure you want to cancel the subscription for user {target_id}?"
        buttons = [
            [InlineKeyboardButton("Yes", callback_data=f"confirm_cancel_{target_id}_yes"),
             InlineKeyboardButton("No", callback_data=f"confirm_cancel_{target_id}_no")]
        ]
        await query.message.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("confirm_cancel_"):
        parts = data.split("_")
        target_id = parts[2]
        decision = parts[3]
        if decision == "yes":
            if target_id in subscriptions:
                del subscriptions[target_id]
                await save_data()
                await query.message.edit_text(f"Subscription for user {target_id} has been cancelled.")
            else:
                await query.message.edit_text("User has no active subscription.")
        else:
            await query.message.edit_text("Cancellation process aborted.")
    elif data == 'change_website':
        await query.message.reply_text("Send new website URL (must start with https:// and end with /):")
        context.user_data['awaiting_website'] = True
    elif data == 'setting_auto_timer':
        text = f"Auto-delete timer is currently {auto_delete_timer} seconds."
        buttons = [[InlineKeyboardButton("Change Auto Delete Timer", callback_data="change_auto_timer")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == 'change_auto_timer':
        await query.message.reply_text("Please send the new auto delete timer in seconds:")
        context.user_data['awaiting_auto_timer'] = True
    elif data == 'setting_subscription':
        status_text = "ON 🔛" if subscription_function_enabled else "OFF 📴"
        text = f"Subscription Function is {status_text}.\n(When ON, non‑premium users are limited to 1 unique link per day.)"
        buttons = [[InlineKeyboardButton("Toggle", callback_data="toggle_subscription")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == 'toggle_subscription':
        if subscription_function_enabled:
            subscription_off_start = datetime.now()
        else:
            if subscription_off_start is not None:
                now_time = datetime.now()
                delta = now_time - subscription_off_start
                for uid, sub in subscriptions.items():
                    if sub["expiry"] > subscription_off_start:
                        sub["expiry"] = sub["expiry"] + delta
                subscription_off_start = None
        subscription_function_enabled = not subscription_function_enabled
        status_text = "ON 🔛" if subscription_function_enabled else "OFF 📴"
        text = f"Subscription Function is now {status_text}."
        await query.message.edit_text(text)
        await save_data()
    elif data == 'setting_freeze':
        today = get_today_str()
        links_used = daily_param_links_counter.get(today, 0)
        users_count = len(daily_users_set)
        pending_count = len(pending_deletes)
        text = (f"Freeze Stats for {today}:\n"
                f"- Links used today: {links_used}\n"
                f"- Users today: {users_count}\n"
                f"- Messages pending auto-delete: {pending_count}")
        buttons = [[InlineKeyboardButton("Delete ➖", callback_data="freeze_delete")]]
        await query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(buttons))
    elif data == 'freeze_delete':
        deleted = 0
        failed = 0
        for entry in pending_deletes[:]:
            try:
                entry['task'].cancel()
                await context.bot.delete_message(entry['chat_id'], entry['message_id'])
                deleted += 1
                if entry in pending_deletes:
                    pending_deletes.remove(entry)
            except Exception as e:
                logger.error(f"Error force deleting message {entry['message_id']} in chat {entry['chat_id']}: {e}")
                failed += 1
        text = f"Force deletion complete.\nDeleted: {deleted}\nFailed: {failed}"
        await query.message.edit_text(text)
    elif data == "premium_users":
        now = datetime.now()
        lines = []
        idx = 1
        for uid, sub in subscriptions.items():
            if sub['expiry'] > now:
                try:
                    member = await context.bot.get_chat_member(chat_id=int(uid), user_id=int(uid))
                    name = member.user.first_name
                    mention = f"<a href='tg://user?id={uid}'>{name}</a>"
                except Exception as e:
                    logger.error(f"Error mentioning user {uid}: {e}")
                    mention = uid
                purchased = sub['purchased'].strftime('%Y-%m-%d %H:%M')
                expiry = sub['expiry'].strftime('%Y-%m-%d %H:%M')
                time_left = sub['expiry'] - now
                days = time_left.days
                hours = time_left.seconds // 3600
                lines.append(f"({idx}) {mention} | Purchased: {purchased} | Expires: {expiry} | {days}d {hours}h left")
                idx += 1
        result_text = "\n".join(lines) if lines else "No active premium users."
        for part in split_message(result_text):
            await context.bot.send_message(chat_id=update.effective_user.id, text=part, parse_mode=ParseMode.HTML)
    # (Other cases remain unchanged)

async def handle_website_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_website') and update.effective_user.id == ADMIN_ID:
        new_url = update.message.text.strip()
        if not (new_url.startswith("https://") and new_url.endswith("/")):
            await update.message.reply_text("❌ Invalid website URL format. Try again.")
            context.user_data.pop('awaiting_website', None)
            return
        website_db['current'] = new_url
        await update.message.reply_text(f"✅ Website updated to: {new_url}")
        context.user_data.pop('awaiting_website', None)
        await save_data()
    elif context.user_data.get('awaiting_auto_timer') and update.effective_user.id == ADMIN_ID:
        try:
            new_timer = int(update.message.text.strip())
            global auto_delete_timer
            auto_delete_timer = new_timer
            await update.message.reply_text(f"✅ Auto Delete Timer updated to {new_timer} seconds.")
        except ValueError:
            await update.message.reply_text("❌ Please send a valid number in seconds.")
        context.user_data.pop('awaiting_auto_timer', None)

async def subscription_listener(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.channel_post and update.channel_post.chat.id in [SUBS_CHANNEL, LIMITED_SUBS_CHANNEL, UPGRADE_CHANNEL]:
        try:
            uid = update.channel_post.text.strip()
            user_id = str(int(uid))
            purchase_date = datetime.now()
            expiry_date = purchase_date + timedelta(days=30)
            if update.channel_post.chat.id == LIMITED_SUBS_CHANNEL:
                plan_type = "limited"
            elif update.channel_post.chat.id == UPGRADE_CHANNEL:
                if user_id in subscriptions and subscriptions[user_id].get("plan") == "limited":
                    subscriptions[user_id]["plan"] = "full"
                    subscriptions[user_id]["upgraded"] = True
                    await context.bot.send_message(chat_id=int(user_id), text="You upgraded your limited subscription to Unlimited!")
                    await save_data()
                return
            else:
                plan_type = "full"
            subscriptions[user_id] = {
                "purchased": purchase_date,
                "expiry": expiry_date,
                "expired_notified": False,
                "plan": plan_type
            }
            all_users.add(int(user_id))
            if plan_type == "limited":
                subscription_text = (
                    "🎉 <b>Limited Premium Subscription Activated!</b> 🎉\n\n"
                    "Thank you for upgrading! Your Limited Premium subscription is now active.\n\n"
                    f"📥 <b>Purchased on:</b> {purchase_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"⏳ <b>Expires on:</b> {expiry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                    "You can access up to 3 unique links per day.\n"
                    "Use /plan to view your subscription plan and available commands.\n"
                    "🙏 Thank you for choosing our service!"
                )
            else:
                subscription_text = (
                    "🎉 <b>Premium Subscription Activated!</b> 🎉\n\n"
                    "Thank you for upgrading! Your Premium subscription is now active.\n\n"
                    f"📥 <b>Purchased on:</b> {purchase_date.strftime('%Y-%m-%d %H:%M')}\n"
                    f"⏳ <b>Expires on:</b> {expiry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                    "Use /plan to view your subscription plan and available commands.\n"
                    "🙏 Thank you for choosing our service!"
                )
            await context.bot.send_message(chat_id=int(user_id), text=subscription_text, parse_mode=ParseMode.HTML)
            await save_data()
        except Exception as e:
            logger.error(f"Error processing subscription: {e}")

async def plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    now = datetime.now()
    buy_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Buy 💸", url="https://t.me/pay")]])
    uid = str(user.id)
    if uid in subscriptions:
        sub = subscriptions[uid]
        if sub['expiry'] > now:
            purchased = sub['purchased']
            effective_expiry = sub['expiry']
            if not subscription_function_enabled and subscription_off_start is not None:
                effective_expiry = sub["expiry"] + (datetime.now() - subscription_off_start)
            time_left = effective_expiry - now
            days = time_left.days
            hours = time_left.seconds // 3600
            extra = ""
            if sub.get("plan") == "limited":
                today_str = get_today_str()
                usage = user_usage.get(uid, {})
                used = len(usage.get("links", [])) if usage.get("date") == today_str else 0
                extra = f"\nLinks used today: {used}/3"
            if sub.get("upgraded"):
                extra += "\n(You upgraded your limited subscription to Unlimited!)"
            text = (
                "🌟 <b>Premium Plan</b> 🌟\n\n"
                f"📥 <b>Purchased on:</b> {purchased.strftime('%Y-%m-%d %H:%M')}\n"
                f"⏳ <b>Expires on:</b> {effective_expiry.strftime('%Y-%m-%d %H:%M')}\n"
                f"⌛ <b>Time remaining:</b> {days}d {hours}h{extra}\n\n"
                "Thank you for choosing our Premium service!"
            )
            await update.message.reply_text(text, parse_mode=ParseMode.HTML)
        else:
            text = (
                "💎 <b>Basic Plan</b> 💎\n\n"
                "✅ Currently Free\n"
                "🔗 Daily limit: 1 unique link\n\n"
                "Upgrade to Premium for unlimited access.\nTap the button below."
            )
            await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=buy_keyboard)
    else:
        text = (
            "💎 <b>Basic Plan</b> 💎\n\n"
            "✅ Currently Free\n"
            "🔗 Daily limit: 1 unique link\n\n"
            "Upgrade to Premium for unlimited access.\nTap the button below."
        )
        await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=buy_keyboard)

async def pay_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    text = (
        "💳 <b>Upgrade to Premium</b> 💳\n\n"
        "Unlock all premium features:\n"
        "• Unlimited exclusive content\n"
        "• No daily link limits (if Full Premium)\n"
        "• Priority support\n\n"
        "Tap below to proceed with payment."
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Pay", url="https://t.me/pay")]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def users_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    all_users.add(update.effective_user.id)
    now = datetime.now()
    premium_count = sum(1 for sub in subscriptions.values() if sub['expiry'] > now)
    total_users = len(all_users)
    non_premium_count = total_users - premium_count
    text = (
        f"📊 <b>User Statistics</b> 📊\n\n"
        f"Premium Users: {premium_count}\n"
        f"Non-Premium Users: {non_premium_count}\n"
        f"Total Users: {total_users}"
    )
    keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Premium Users", callback_data="premium_users")]])
    await update.message.reply_text(text, parse_mode=ParseMode.HTML, reply_markup=keyboard)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    all_users.add(user.id)
    if user.id == ADMIN_ID:
        text = (
            "🛠 <b>Admin Commands</b> 🛠\n\n"
            "/betch - Create new batch links\n"
            "/links - List all links\n"
            "/website - Manage website URL\n"
            "/setting - Manage settings\n"
            "/export - Export data as CSV\n"
            "/users - View user stats\n"
            "/plan - View your subscription plan\n"
            "/user {userid} - View user details\n"
            "/help - Display this help message"
        )
    else:
        text = (
            "📚 <b>Help & Commands</b> 📚\n\n"
            "/start - Start the bot\n"
            "/plan - View your subscription plan\n"
            "/pay - Upgrade to Premium\n"
            "/help - Display help message\n\n"
            "Basic users: 1 unique link per day.\n"
            "Limited Premium: 3 unique links per day.\n"
            "Full Premium: Unlimited access.\n"
            "Thank you for using our service!"
        )
    await update.message.reply_text(text, parse_mode=ParseMode.HTML)

# ------------------------------
# Automatic Expiry Checker
# ------------------------------
async def check_expired_subscriptions(context: ContextTypes.DEFAULT_TYPE):
    if not subscription_function_enabled:
        return
    now = datetime.now()
    for uid, sub in subscriptions.items():
        if sub['expiry'] <= now and not sub.get('expired_notified', False):
            buy_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Buy 💸", url="https://t.me/pay")]])
            text = (
                "⚠️ <b>Premium Plan Expired</b> ⚠️\n\n"
                "Your Premium subscription has expired.\n"
                "Please renew your subscription to continue enjoying unlimited access.\n\n"
                "Thank you for using our service!"
            )
            try:
                await context.bot.send_message(
                    chat_id=int(uid),
                    text=text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=buy_keyboard
                )
                sub['expired_notified'] = True
            except Exception as e:
                logger.error(f"Failed to send expiry notification to user {uid}: {e}")
    await save_data()

# ------------------------------
# Main Function
# ------------------------------
