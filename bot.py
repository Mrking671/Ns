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

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user is verified
    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < timedelta(hours=12):
        user_message = update.message.text
        selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
        api_url = API_URLS.get(selected_ai, API_URLS[DEFAULT_AI])
        try:
            response = requests.get(api_url.format(user_message))
            response_data = response.json()

            # Special handling for 'horny' AI
            if selected_ai == "horny":
                text_response = response_data.get("gpt", "Sorry, I couldn't understand that.")
                image_url = response_data.get("gpt", None)
                if image_url:
                    media = InputMediaPhoto(image_url, caption=text_response)
                    await update.message.reply_photo(photo=image_url, caption=text_response)
                else:
                    await update.message.reply_text(text_response)
            else:
                answer = response_data.get("message", "Sorry, I couldn't understand that.")
                await update.message.reply_text(answer)
            
            # Log the message and response to the log channel
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
        # User needs to verify again
        await send_verification_message(update, context)

async def handle_verification_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Update user verification status
    verification_collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_verified': current_time}},
        upsert=True
    )
    await update.message.reply_text('ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴠᴇʀғɪᴇᴅ!🥰')
    await send_start_message(update, context)  # Directly send the start message after verification

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking user membership status: {e}")
        return False

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMINS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    users = verification_collection.find({})
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=message_text)
        except Exception as e:
            logger.error(f"Error sending broadcast to {user['user_id']}: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMINS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    user_count = verification_collection.count_documents({})
    await update.message.reply_text(f"Number of verified users: {user_count}")

def main():
    # Create the application with the provided bot token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'.*verified.*'), handle_verification_redirect))
    application.add_handler(CommandHandler("broadcast", broadcast, filters=filters.User(username=ADMINS)))
    application.add_handler(CommandHandler("stats", stats, filters=filters.User(username=ADMINS)))

    # Add error handler
    application.add_error_handler(error)

    # Start the webhook to listen for updates
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Make sure to set this environment variable in your Render settings
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=os.getenv("TELEGRAM_TOKEN"),
        webhook_url=f"{WEBHOOK_URL}/{os.getenv('TELEGRAM_TOKEN')}"
    )

if __name__ == '__main__':
    main()
