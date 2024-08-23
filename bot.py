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

API_URL = "https://chatgpt.darkhacker7301.workers.dev/?question="

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text('Hello! Ask me anything.')

def handle_message(update: Update, context: CallbackContext) -> None:
    user_message = update.message.text
    try:
        response = requests.get(API_URL + user_message)
        response_data = response.json()  # Parse the JSON response
        answer = response_data.get("answer", "Sorry, I couldn't understand that.")
        update.message.reply_text(answer)
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error: {e}")
        update.message.reply_text("There was an error retrieving the response. Please try again later.")
    except ValueError as e:
        logger.error(f"JSON decoding error: {e}")
        update.message.reply_text("Error parsing the response from the API. Please try again later.")

def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
