import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, CallbackQueryHandler
from datetime import datetime, timedelta

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
    'zenith': "https://ashlynn.darkhacker7301.workers.dev/?question={}&state=Zenith"
}

# Default AI
DEFAULT_AI = 'chatgpt'

# Verification settings
VERIFICATION_DURATION = timedelta(minutes=1)  # 1 minute for verification
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification
verification_data = {}  # Store user verification info

# Command to start the bot
def start(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    current_time = datetime.now()

    # Check verification status
    last_verified = verification_data.get(user_id, {}).get('last_verified', None)
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
        # User is verified or verification is still valid
        send_start_message(update, context)
    else:
        # User is not verified or verification expired
        send_verification_message(update, context)

def send_verification_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    verification_link = "https://your-blogspot-page-url"  # Replace with your Blogspot page URL

    # Send verification message with link
    keyboard = [[InlineKeyboardButton("Verify Now", url=verification_link)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'Please verify yourself by clicking the link below. You need to stay on the page for at least 1 minute.\n'
        'Once verified, you will be able to use the bot.',
        reply_markup=reply_markup
    )

def send_start_message(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [InlineKeyboardButton("Talk to GirlfriendAI", callback_data='girlfriend')],
        [InlineKeyboardButton("Talk to JarvisAI", callback_data='jarvis')],
        [InlineKeyboardButton("Talk to ZenithAI", callback_data='zenith')],
        [InlineKeyboardButton("Reset to ChatGPT", callback_data='reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        'Welcome! Choose an AI to talk to by clicking a button. Available options are: GirlfriendAI, JarvisAI, ZenithAI.\n'
        'To reset to ChatGPT, click the button below.',
        reply_markup=reply_markup
    )

# Handle button presses
def button_handler(update: Update, context: CallbackContext) -> None:
    query = update.callback_query
    data = query.data

    if data in API_URLS:
        context.user_data['selected_ai'] = data
        query.answer()
        query.edit_message_text(text=f'You are now chatting with {data.capitalize()}AI.')
    elif data == 'reset':
        context.user_data['selected_ai'] = DEFAULT_AI
        query.answer()
        query.edit_message_text(text='You are now reset to ChatGPT.')

# Handle all messages
def handle_message(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    current_time = datetime.now()

    # Check if the user is verified
    last_verified = verification_data.get(user_id, {}).get('last_verified', None)
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
        user_message = update.message.text
        selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
        api_url = API_URLS.get(selected_ai, API_URLS[DEFAULT_AI])
        try:
            response = requests.get(api_url.format(user_message))
            response_data = response.json()
            answer = response_data.get("answer", "Sorry, I couldn't understand that.")
            update.message.reply_text(answer)
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            update.message.reply_text("There was an error retrieving the response. Please try again later.")
        except ValueError as e:
            logger.error(f"JSON decoding error: {e}")
            update.message.reply_text("Error parsing the response from the API. Please try again later.")
    else:
        # User needs to verify again
        send_verification_message(update, context)

# Handle verification redirection
def handle_verification_redirect(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    current_time = datetime.now()

    # Update user verification status
    verification_data[user_id] = {'last_verified': current_time}
    update.message.reply_text('You are now verified! You can use the bot normally.')

# Log errors
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(CallbackQueryHandler(button_handler))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
