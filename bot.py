import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, CallbackQueryHandler, ContextTypes
)
from datetime import datetime, timedelta
from pymongo import MongoClient

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API URLs for different AIs
API_URLS = {
    'chatgpt': "https://chatgpt.darkhacker7301.workers.dev/?question={}",
    'girlfriend': "https://chatgpt.darkhacker7301.workers.dev/?question={}&state=girlfriend",
    'jarvis': "https://jarvis.darkhacker7301.workers.dev/?question={}&state=jarvis",
    'zenith': "https://ashlynn.darkhacker7301.workers.dev/?question={}&state=Zenith",
    'evil': "https://white-evilgpt.ashlynn.workers.dev/?username=Yourtgusername&question={}",
    'lord': "https://lord.ashlynn.workers.dev/?question={}&state=Poet",
    'business': "https://bjs-tbc.ashlynn.workers.dev/?username=YourTGI'dhere&question={}",
    'developer': "https://bb-ai.ashlynn.workers.dev/?question={}&state=helper",
    'gpt4': "https://telesevapi.vercel.app/chat-gpt?question={}"
}

# Default AI
DEFAULT_AI = 'gpt4'

# Verification settings
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification

# Channel that users need to join to use the bot
REQUIRED_CHANNEL = "@purplebotz"  # Replace with your channel

# Channel where logs will be sent
LOG_CHANNEL = "@chatgptlogs"  # Replace with your log channel

# Admin users
ADMINS = ["@Lordsakunaa", "6951715555"]  # Add your admin usernames or IDs

# MongoDB setup
MONGO_URI = os.getenv('MONGO_URI')  # Replace with your MongoDB URI
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
verification_collection = db['verification']

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user has joined the required channel
    if not await is_user_member_of_channel(context, update.effective_user.id):
        await send_join_channel_message(update, context)
        return

    # Check if the message contains 'verified' indicating a successful verification
    if 'verified' in context.args:
        await handle_verification_redirect(update, context)
    else:
        # Regular start command logic
        last_verified = get_last_verified(user_id)
        if last_verified and current_time - datetime.fromisoformat(last_verified) < VERIFICATION_INTERVAL:
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
    bot_username = "chatgpt490_bot"  # Your bot username
    verification_link = f"https://t.me/{bot_username}?start=verified"

    keyboard = [[InlineKeyboardButton("I'm not a robot", url="https://chatgptgiminiai.blogspot.com/2024/08/verification-page-body-font-family.html")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Please verify yourself that you are not a robot by clicking the link below. You need to verify every 12 hours to use the bot.\n'
        'Once verified, you will be redirected back to the bot.',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Talk to GirlfriendAI", callback_data='girlfriend')],
        [InlineKeyboardButton("Talk to JarvisAI", callback_data='jarvis')],
        [InlineKeyboardButton("Talk to ZenithAI", callback_data='zenith')],
        [InlineKeyboardButton("Talk to EvilAI", callback_data='evil')],
        [InlineKeyboardButton("Talk to LordAI", callback_data='lord')],
        [InlineKeyboardButton("Talk to BusinessAI", callback_data='business')],
        [InlineKeyboardButton("Talk to DeveloperAI", callback_data='developer')],
        [InlineKeyboardButton("Talk to ChatGPT-4", callback_data='gpt4')],
        [InlineKeyboardButton("Reset to ChatGPT-3", callback_data='reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Welcome! Choose an AI to talk to by clicking a button. Available options are: GirlfriendAI, JarvisAI, ZenithAI, EvilAI, LordAI, BusinessAI, DeveloperAI, ChatGPT-4.\nDefault is ChatGPT-3'
        'To reset to ChatGPT-3, click the button below.',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data in API_URLS:
        context.user_data['selected_ai'] = data
        await query.answer()
        await query.edit_message_text(text=f'You are now chatting with {data.capitalize()}_AI.\n To change AI use /start command')
    elif data == 'reset':
        context.user_data['selected_ai'] = DEFAULT_AI
        await query.answer()
        await query.edit_message_text(text='You are now reset to ChatGPT.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user is verified
    last_verified = get_last_verified(user_id)
    if last_verified and current_time - datetime.fromisoformat(last_verified) < VERIFICATION_INTERVAL:
        user_message = update.message.text
        selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
        api_url = API_URLS.get(selected_ai, API_URLS[DEFAULT_AI])
        try:
            if selected_ai == 'gpt4':
                response = requests.get(api_url.format(user_message))
                response_data = response.json()
                answer = response_data.get("message", "Sorry, I couldn't understand that.")
            else:
                response = requests.get(api_url.format(user_message))
                response_data = response.json()
                answer = response_data.get("answer", "Sorry, I couldn't understand that.")
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
    set_last_verified(user_id, current_time.isoformat())
    await update.message.reply_text('You are now verified! You can use the bot normally.')
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

def get_last_verified(user_id: str) -> str:
    user_data = verification_collection.find_one({'user_id': user_id})
    if user_data:
        return user_data.get('last_verified', None)
    return None

def set_last_verified(user_id: str, timestamp: str) -> None:
    verification_collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_verified': timestamp}},
        upsert=True
    )

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)

    # Check if the user is an admin
    if user_id not in ADMINS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    # Get the broadcast message from the command text
    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    # Broadcast the message to all users
    job_queue = context.application.job_queue
    job_queue.run_repeating(broadcast_message, interval=0, first=0, context={'message_text': message_text})
    await update.message.reply_text("Broadcast message sent.")

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = context.job.context.get('message_text', 'This is a broadcast message')
    users = verification_collection.find()
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=message_text)
        except Exception as e:
            logger.error(f"Error sending broadcast to {user['user_id']}: {e}")

def main():
    # Create the application with the provided bot token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("broadcast", broadcast))  # Added broadcast command handler
    application.add_handler(CommandHandler("stats", st_last))  # Added stats command handler
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'.*verified.*'), handle_verification_redirect))

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
