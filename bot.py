import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ContextTypes
)
from datetime import datetime, timedelta
from pymongo import MongoClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API URLs for different AIs
API_URLS = {
    'chatgpt': "https://chatgpt.darkhacker7301.workers.dev/?question={}",
    'horny': "https://evil.darkhacker7301.workers.dev/?question={}&model=horny",
    'zenith': "https://ashlynn.darkhacker7301.workers.dev/?question={}&state=Zenith",
    'business': "https://bjs-tbc.ashlynn.workers.dev/?username=YourTGI'dhere&question={}",
    'developer': "https://bb-ai.ashlynn.workers.dev/?question={}&state=helper",
    'gpt4': "https://telesevapi.vercel.app/chat-gpt?question={}",
    'bing': "https://lord-apis.ashlynn.workers.dev/?question={}&mode=Bing",
    'meta': "https://lord-apis.ashlynn.workers.dev/?question={}&mode=Llama",
    'blackbox': "https://lord-apis.ashlynn.workers.dev/?question={}&mode=Blackbox",
    'qwen': "https://lord-apis.ashlynn.workers.dev/?question={}&mode=Qwen"
}

# Default AI
DEFAULT_AI = 'chatgpt'

# Channel that users need to join to use the bot
REQUIRED_CHANNEL = "@chatgpt4for_free"  # Replace with your channel

# Channel where logs will be sent
LOG_CHANNEL = "@chatgptlogs"  # Replace with your log channel

# Admins and MongoDB setup
ADMINS = ["@Lordsakunaa", "6951715555"]  # Admin usernames and IDs
MONGO_URI = os.getenv('MONGO_URI')  # Replace with your MongoDB URI
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
verification_collection = db['verification_data']

# Scheduler for auto-deletion of messages
scheduler = AsyncIOScheduler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user has joined the required channel
    if not await is_user_member_of_channel(context, update.effective_user.id):
        await send_join_channel_message(update, context)
        return

    # Check if the message contains 'verified' indicating a successful verification
    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < timedelta(hours=12):
        await send_start_message(update, context)
    else:
        await send_verification_message(update, context)

async def send_join_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{REQUIRED_CHANNEL[1:]}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'To use this bot, you need to join our updates channel first.',
        reply_markup=reply_markup
    )

async def send_verification_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    bot_username = context.bot.username
    verification_link = f"https://t.me/{bot_username}?start=verified"

    keyboard = [
        [InlineKeyboardButton(
            "I'm not a robot👨‍💼",  
            url="https://linkshortify.com/st?api=7d706f6d7c95ff3fae2f2f40cff10abdc0e012e9&url=https://t.me/chatgpt490_bot?start=verified"
        )],
        [InlineKeyboardButton(
            "How to open captcha🔗",
            url="https://t.me/disneysworl_d/5"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '♂️ 🅲🅰🅿🆃🅲🅷🅰 ♂️\n\nᴘʟᴇᴀsᴇ ᴠᴇʀɪғʏ ᴛʜᴀᴛ ʏᴏᴜ ᴀʀᴇ ʜᴜᴍᴀɴ 👨‍💼\nᴛᴏ ᴘʀᴇᴠᴇɴᴛ ᴀʙᴜsᴇ ᴡᴇ ᴇɴᴀʙʟᴇᴅ ᴛʜɪs ᴄᴀᴘᴛᴄʜᴀ\n𝗖𝗟𝗜𝗖𝗞 𝗛𝗘𝗥𝗘👇',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("ChatGPT-4👑", callback_data='gpt4'), InlineKeyboardButton("Horny AI🥰", callback_data='horny')],
        [InlineKeyboardButton("Zenith AI😑", callback_data='zenith'), InlineKeyboardButton("Business AI🤑", callback_data='business')],
        [InlineKeyboardButton("Developer AI🧐", callback_data='developer'), InlineKeyboardButton("Bing AI🤩", callback_data='bing')],
        [InlineKeyboardButton("Meta AI😤", callback_data='meta'), InlineKeyboardButton("Blackbox AI🤠", callback_data='blackbox')],
        [InlineKeyboardButton("Qwen AI😋", callback_data='qwen'), InlineKeyboardButton("Default (ChatGPT-3🤡)", callback_data='reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await update.message.reply_text(
        'ᴡᴇʟᴄᴏᴍᴇ👊 ᴄʜᴏᴏsᴇ ᴀɪ ғʀᴏᴍ ʙᴇʟᴏᴡ ʟɪsᴛ👇\nᴅᴇғᴀᴜʟᴛ ɪs ᴄʜᴀᴛɢᴘᴛ-𝟹',
        reply_markup=reply_markup
    )

    # Schedule auto-delete of the message
    scheduler.add_job(
        lambda: context.bot.delete_message(chat_id=update.effective_chat.id, message_id=message.message_id),
        trigger='date',
        run_date=datetime.now() + timedelta(minutes=30)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < timedelta(hours=12):
        user_message = update.message.text
        selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
        api_url = API_URLS.get(selected_ai, API_URLS[DEFAULT_AI])
        try:
            response = requests.get(api_url.format(user_message))
            response_data = response.json()

            if selected_ai == "horny":
                text_response = response_data.get("gpt", "Sorry, I couldn't understand that.")
                image_url = response_data.get("image_url", None)
                if image_url:
                    await update.message.reply_photo(photo=image_url, caption=text_response)
                else:
                    await update.message.reply_text(text_response)
            else:
                answer = response_data.get("message", "Sorry, I couldn't understand that.")
                await update.message.reply_text(answer)
            
            await context.bot.send_message(
                chat_id=LOG_CHANNEL,
                text=f"User: {update.message.from_user.username}\nMessage: {user_message}\nResponse: {answer}"
            )

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            await update.message.reply_text("There was an error retrieving the response. Please try again later.")
        except ValueError as e:
            logger.error(f"JSON decoding error: {e}")
            await update.message.reply_text("Error parsing the response from the API. Please try again later.")
    else:
        await send_verification_message(update, context)

def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))

    # Start scheduler and run bot
    scheduler.start()
    application.run_polling()

if __name__ == "__
