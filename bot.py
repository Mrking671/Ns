import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes
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

# API URL
API_URL = "https://BJ-Devs.serv00.net/gpt4-o.php?text={}"

# Verification settings
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification

# Required channel for users to join
REQUIRED_CHANNEL = "@chatgpt4for_free"  # Replace with your channel

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

    # Check verification status
    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
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
    verification_link = f"https://t.me/{context.bot.username}?start=verified"

    keyboard = [
        [InlineKeyboardButton("I'm not a robot👨‍💼", url=verification_link)],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Please verify that you are human to continue using the bot.',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Welcome! You are now chatting with the default AI. Type your message to begin.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check verification status
    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
        user_message = update.message.text
        try:
            response = requests.get(API_URL.format(user_message))
            response_data = response.json()

            reply = response_data.get("reply", "Sorry, no response was received.")
            join_channel = response_data.get("join", "N/A")
            support_info = response_data.get("support", "N/A")

            message_text = f"{reply}\n\n🌟 Join: {join_channel}\n📞 Support: {support_info}"
            await update.message.reply_text(message_text)

        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            await update.message.reply_text("There was an error retrieving the response. Please try again later.")
        except ValueError as e:
            logger.error(f"JSON decoding error: {e}")
            await update.message.reply_text("Error parsing the response from the API. Please try again later.")
    else:
        # User needs to verify again
        await send_verification_message(update, context)

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

def main() -> None:
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers for commands and messages
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Use webhook setup for deployment
    webhook_url = os.getenv("WEBHOOK_URL")  # Replace with your webhook URL
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8443")),
        url_path=os.getenv("TELEGRAM_TOKEN"),
        webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_TOKEN')}"
    )

if __name__ == "__main__":
    main()
