import logging
import qrcode
from PIL import Image
import io
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import random
import string
import pymongo
from pymongo import MongoClient

# MongoDB configuration
MONGO_URI = 'mongodb+srv://hookmehostwork3:HlvPrmjiXJzkMG2E@cluster0.5a6y2.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0'
client = MongoClient(MONGO_URI)
db = client['Cluster0']
user_messages_collection = db['user_messages']
qr_codes_collection = db['qr_codes']
user_tn_codes_collection = db['user_tn_codes']

# Replace with your bot token
#BOT_TOKEN = '7428000146:AAFefWJkaar0oKjeea2-u8THm0Vx3epaew0'
# Replace with your channel ID
CHANNEL_ID = -1002301680804
# User ID allowed to issue the /delete command
ADMIN_USER_ID = 7144181041

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def generate_unique_code(length=10):
    return 'IT' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

def download_logo_from_telegram(file_id):
    bot_url = f'https://api.telegram.org/file/bot{BOT_TOKEN}/'
    file_info = requests.get(f'https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}').json()
    file_path = file_info['result']['file_path']
    response = requests.get(bot_url + file_path)
    return response.content

def generate_qr_code(data, logo_file_id=None):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')

    if logo_file_id:
        try:
            logo_content = download_logo_from_telegram(logo_file_id)
            logo = Image.open(io.BytesIO(logo_content)).convert("RGBA")
            logo.thumbnail((50, 50))
            img = img.convert("RGBA")
            logo_position = ((img.size[0] - logo.size[0]) // 2, (img.size[1] - logo.size[1]) // 2)
            img.paste(logo, logo_position, mask=logo)
        except Exception as e:
            logging.error(f"Error adding logo to QR code: {e}")

    return img

async def start(update: Update, context):
    user_id = update.message.from_user.id
    args = context.args

    if args and args[0] in ['s', 'S']:
        amount = '200' if args[0] == 'S' else '180'

        # Generate or retrieve the TN code for the user
        tn_code_entry = user_tn_codes_collection.find_one({'user_id': user_id})
        if tn_code_entry:
            unique_code = tn_code_entry['tn_code']
        else:
            unique_code = generate_unique_code()
            user_tn_codes_collection.insert_one({'user_id': user_id, 'tn_code': unique_code})

        qr_data = f'upi://pay?pa=Q682714937@ybl&pn=V-TECH&am={amount}&tn={unique_code}'

        # Generate or retrieve the QR code
        qr_code_entry = qr_codes_collection.find_one({'tn_code': unique_code, 'amount': amount})
        if qr_code_entry:
            qr_image_data = qr_code_entry['qr_code_data']
        else:
            logo_file_id = 'BQACAgUAAxkBAAOFZuXv8SPbZelS-gE53dNnyPZxxoEAAv8OAAKAe1lWvt2DsZHCldQ2BA'
            qr_image = generate_qr_code(qr_data, logo_file_id=logo_file_id)
            qr_stream = io.BytesIO()
            qr_image.save(qr_stream, format='PNG')
            qr_stream.seek(0)

            qr_image_data = qr_stream.getvalue()
            qr_codes_collection.insert_one({'tn_code': unique_code, 'amount': amount, 'qr_code_data': qr_image_data})

        await delete_old_messages(user_id, context)

        messages_to_send = [
            ("✨YOU PURCHASING✨", None, None),
            (None, 'AgACAgUAAxkBAAMDZuLGJEbWoqAogU2QF5yO45ByPwgAAim_MRukShlXvJeP2v8lCGEBAAMCAAN3AAM2BA', f"• {amount}₹ ~ Fᴜʟʟ Cᴏʟʟᴇᴄᴛɪᴏɴ 🥳\n• Qᴜɪᴄᴋ Dᴇʟɪᴇᴠᴇʀʏ Sʏsᴛᴇᴍ 🏎️💨\n• Nᴏ Lɪɴᴋ❗, Dɪʀᴇᴄᴛ 🍃\n• Oʀɢɪɴᴀʟ Qᴜᴀʟɪᴛʏ ☄️\n• Pʟᴜs Bᴏɴᴜs⚜"),
            ("🔱Qʀ ᴄᴏᴅᴇ ᴀɴᴅ ᴘᴀʏ Lɪɴᴋ👇", None, None),
            (None, qr_image_data, None),
            ("☄Qᴜɪᴄᴋ ᴘᴀʏ sʏsᴛᴇᴍ🎗", None, None),
            ("Tᴜᴛᴏʀɪᴀʟ : ʜᴏᴡ ᴛᴏ ᴘᴀʏ 👇", None, None),
            (None, 'BAACAgUAAxkBAAMFZuLGKmB4d5walYerbRzaTrpAQdoAAh0VAAKkShlX7fOyuIXrOyk2BA', None),
        ]

        message_ids = []
        for text, content, caption in messages_to_send:
            if content is None:
                message = await context.bot.send_message(chat_id=user_id, text=text)
            elif isinstance(content, bytes):
                message = await context.bot.send_photo(chat_id=user_id, photo=io.BytesIO(content), caption=text)
            elif caption and isinstance(content, str):
                if content.startswith('BAACAgUAAxk'):
                    message = await context.bot.send_video(chat_id=user_id, video=content, caption=caption)
                else:
                    message = await context.bot.send_photo(chat_id=user_id, photo=content, caption=caption)
            else:
                if content.startswith('BAACAgUAAxk'):
                    message = await context.bot.send_video(chat_id=user_id, video=content)
                else:
                    message = await context.bot.send_photo(chat_id=user_id, photo=content)

            message_ids.append(message.message_id)

        user_messages_collection.insert_one({
            'unique_code': unique_code,
            'user_id': user_id,
            'amount': amount,
            'messages_to_send': messages_to_send,
            'message_ids': message_ids
        })
    else:
        # Send message with inline button when no parameters are provided
        inline_keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("IINKPROVIDER", url="https://t.me/Iinkproviderbot")]
        ])
        await context.bot.send_message(
            chat_id=user_id,
            text="👇Sᴛᴀʀᴛ ғʀᴏᴍ ᴛʜɪs ʙᴏᴛ ᴛᴏ ʙᴜʏ",
            reply_markup=inline_keyboard
        )

async def delete_old_messages(user_id, context):
    messages_to_delete = user_messages_collection.find({'user_id': user_id})

    for message_data in messages_to_delete:
        for message_id in message_data['message_ids']:
            try:
                await context.bot.delete_message(chat_id=user_id, message_id=message_id)
                logging.info(f"Deleted message {message_id} for user {user_id}")
            except Exception as e:
                logging.error(f"Error deleting message {message_id} for user {user_id}: {e}")

    user_messages_collection.delete_many({'user_id': user_id})

async def delete_all_messages(update: Update, context):
    user_id = update.message.from_user.id

    # Check if the user is authorized to issue the command
    if user_id != ADMIN_USER_ID:
        await context.bot.send_message(chat_id=user_id, text="You are not authorized to use this command.")
        return

    # Collect all messages that need to be deleted
    all_message_ids = []
    all_chat_ids = set()

    for message_data in user_messages_collection.find():
        all_message_ids.extend(message_data['message_ids'])
        all_chat_ids.add(message_data['user_id'])

    for chat_id in all_chat_ids:
        messages_to_delete = [message_id for message_data in user_messages_collection.find({'user_id': chat_id}) for message_id in message_data['message_ids']]
        for message_id in messages_to_delete:
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
                logging.info(f"Deleted message {message_id} from user {chat_id}.")
            except Exception as e:
                logging.error(f"Error deleting message {message_id} from user {chat_id}: {e}")

    user_messages_collection.delete_many({})
    await context.bot.send_message(chat_id=user_id, text="All messages have been deleted.")

async def handle_payment_update(update: Update, context):
    try:
        message = update.channel_post.text
        if message.startswith('IT'):
            unique_code = message
            user_message = user_messages_collection.find_one({'unique_code': unique_code})

            if user_message:
                user_id = user_message['user_id']

                # Send the confirmation message to the user
                await context.bot.send_message(
                    chat_id=user_id,
                    text="✨Payment Confirm✨"
                )

                # Send the user ID to the specified channel with a button
                button_text = "User ID"
                button_url = f"tg://user?id={user_id}"
                keyboard = InlineKeyboardMarkup([[InlineKeyboardButton(button_text, url=button_url)]])
                
                await context.bot.send_message(
                    chat_id=-1002315192547,  # New Channel ID where the button is to be sent
                    text=f"User ID: {user_id}",
                    reply_markup=keyboard
                )

                # Delete old messages related to the user's QR codes
                await delete_old_messages(user_id, context)

                # Send the video with caption to the user
                file_id = 'BAACAgUAAxkBAAMHZuLGLkRq4Ej1PekdoULAdoyIeMUAAnEVAALsLxBXCdaESjhVUag2BA'
                caption = (
                    "⚡️𝐒𝐔𝐁𝐇𝐀𝐒𝐇𝐑𝐄𝐄 𝐒𝐀𝐇𝐔 𝐅𝐮𝐥𝐥 𝐂𝐨𝐥𝐥𝐞𝐜𝐭𝐢𝐨𝐧 𝐔𝐧𝐥𝐨𝐜𝐤𝐞𝐝 🔓\n\n"
                    "👇Sᴇɴᴅ A Mᴇssᴀɢᴇ Tᴏ Aᴅᴍɪɴ\n"
                    "t.me/iinkproviderr\n"
                    "t.me/iinkproviderr\n"
                    "t.me/iinkproviderr\n\n"
                    "Aᴅᴍɪɴ Sᴇɴᴅ Yᴏᴜ Dɪʀᴇᴄᴛʟʏ Aʟʟ Sᴜʙʜᴀsʜʀᴇᴇ Sᴀʜᴜ Cᴏʟʟᴇᴄᴛɪᴏɴ 😊\n\n"
                    "⚠️- if you can't able to send message to admin then start this bot and send a message admin reach out👇 @iinkproviderrbot"
                )
                await context.bot.send_video(
                    chat_id=user_id,
                    video=file_id,
                    caption=caption
                )

                # Add a button with a link to the message
                keyboard = [
                    [InlineKeyboardButton("CONTACT: ADMIN", url="https://t.me/iinkproviderr")]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await context.bot.send_message(
                    chat_id=user_id,
                    text="click the button below to send message to admin. 📥𝗚𝗘𝗧 𝗖𝗢𝗟𝗟𝗘𝗖𝗧𝗜𝗢𝗡👇",
                    reply_markup=reply_markup
                )

                # Remove the entry from `user_messages` and keep the TN code for the user
                user_messages_collection.delete_one({'unique_code': unique_code})
    except Exception as e:
        logging.error(f"Error handling payment update: {e}")

