import os
import logging
import requests
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater, CommandHandler, MessageHandler, Filters, CallbackContext,
    CallbackQueryHandler, JobQueue
)
from datetime import datetime, timedelta

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Constants for API URLs and file paths
API_URLS = {
    'chatgpt': "https://chatgpt.darkhacker7301.workers.dev/?question={}"
}
DEFAULT_AI = 'chatgpt'
CHANNEL_USERNAME = "purplebotz"
LOG_CHANNEL_ID = "@yourlogchannel"  # Replace with your log channel username or ID
VERIFICATION_FILE = 'verification_data.json'

def load_data(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}

def save_data(data, file_path):
    with open(file_path, 'w') as f:
        json.dump(data, f)

verification_data = load_data(VERIFICATION_FILE)

def is_user_member_of_channel(user_id: int, bot) -> bool:
    try:
        member = bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking user membership: {e}")
        return False

def start(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    
    if not is_user_member_of_channel(update.message.from_user.id, context.bot):
        send_join_channel_message(update, context)
        return
    
    update.message.reply_text('Welcome! Send me a message and I’ll respond using the default AI.')

def send_join_channel_message(update: Update, context: CallbackContext) -> None:
    keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'To use this bot, you must join our channel. Please click the button below to join:',
        reply_markup=reply_markup
    )

def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = str(update.message.from_user.id)
    user_message = update.message.text
    api_url = API_URLS.get(DEFAULT_AI, API_URLS[DEFAULT_AI])

    try:
        response = requests.get(api_url.format(user_message))
        response_data = response.json()
        answer = response_data.get("answer", "Sorry, I couldn't understand that.")
        update.message.reply_text(answer)

        # Log user interaction
        log_message = (
            f"User ID: {user_id}\n"
            f"Message: {user_message}\n"
            f"Response: {answer}\n"
            f"Timestamp: {datetime.now().isoformat()}"
        )
        context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_message)

    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        update.message.reply_text("There was an error retrieving the response. Please try again later.")
    except ValueError as e:
        logger.error(f"JSON decoding error: {e}")
        update.message.reply_text("Error parsing the response from the API. Please try again later.")

def schedule_broadcast(update: Update, context: CallbackContext) -> None:
    try:
        delay = int(context.args[0])
        message = ' '.join(context.args[1:])
        chat_id = update.effective_chat.id
        context.job_queue.run_once(send_broadcast, delay * 60, context=(chat_id, message))
        update.message.reply_text(f'Broadcast scheduled in {delay} minutes.')
    except (IndexError, ValueError):
        update.message.reply_text('Usage: /schedule_broadcast <delay_in_minutes> <message>')

def send_broadcast(context: CallbackContext) -> None:
    chat_id, message = context.job.context
    context.bot.send_message(chat_id=chat_id, text=message)

def main() -> None:
    updater = Updater("YOUR_BOT_TOKEN", use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dispatcher.add_handler(CommandHandler("schedule_broadcast", schedule_broadcast, pass_args=True, pass_job_queue=True))

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
