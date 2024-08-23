import os
import logging
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# API URLs
API_URLS = {
    'default': "https://chatgpt.darkhacker7301.workers.dev/?question=",
    'girlfriend': "https://chatgpt.darkhacker7301.workers.dev/?question={}&state=girlfriend",
    'jarvis': "https://jarvis.darkhacker7301.workers.dev/?question=",
    'zenith': "https://ashlynn.darkhacker7301.workers.dev/?question={}&state=Zenith"
}

# Default API
DEFAULT_AI = 'default'

# Command to start the bot
def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        'Welcome! Use /select_ai <ai_name> to choose an AI. Available options are: girlfriend, jarvis, zenith.'
    )

# Command to select AI
def select_ai(update: Update, context: CallbackContext) -> None:
    if context.args:
        ai_choice = context.args[0].lower()
        if ai_choice in API_URLS:
            context.user_data['selected_ai'] = ai_choice
            update.message.reply_text(f'You are now chatting with {ai_choice.capitalize()}AI.')
        else:
            update.message.reply_text('Invalid AI choice. Use /select_ai <ai_name> with one of the following: girlfriend, jarvis, zenith.')
    else:
        update.message.reply_text('Please specify an AI choice. Use /select_ai <ai_name>.')

# Handle all messages
def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
    api_url = API_URLS.get(selected_ai, API_URLS['default'])
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

# Log errors
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("select_ai", select_ai))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
