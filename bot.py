import os
import logging
import requests
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
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
    'jarvis': "https://jarvis.darkhacker7301.workers.dev/?question={}&state=jarvis",
    'zenith': "https://ashlynn.darkhacker7301.workers.dev/?question={}&state=Zenith"
}

# Default API
DEFAULT_AI = 'default'

# Command to start the bot
def start(update: Update, context: CallbackContext) -> None:
    keyboard = [
        [KeyboardButton("Talk to GirlfriendAI")],
        [KeyboardButton("Talk to JarvisAI")],
        [KeyboardButton("Talk to ZenithAI")],
        [KeyboardButton("Reset to Default AI")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, one_time_keyboard=True)
    update.message.reply_text(
        'Welcome! Choose an AI to talk to by clicking a button or use /select_ai <ai_name>. '
        'Available options are: girlfriend, jarvis, zenith.\n'
        'To reset to the default AI, use the button below.',
        reply_markup=reply_markup
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

# Command to reset to default AI
def reset_ai(update: Update, context: CallbackContext) -> None:
    context.user_data['selected_ai'] = DEFAULT_AI
    update.message.reply_text('You are now reset to DefaultAI.')

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

# Handle button clicks
def button_handler(update: Update, context: CallbackContext) -> None:
    text = update.message.text
    if text.startswith("Talk to"):
        ai_choice = text.split("Talk to ")[1].replace("AI", "").lower()
        if ai_choice in API_URLS:
            context.user_data['selected_ai'] = ai_choice
            update.message.reply_text(f'You are now chatting with {ai_choice.capitalize()}AI.')
    elif text == "Reset to Default AI":
        reset_ai(update, context)

# Log errors
def error(update: Update, context: CallbackContext) -> None:
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    updater = Updater(os.getenv("TELEGRAM_BOT_TOKEN"))

    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("select_ai", select_ai))
    dp.add_handler(CommandHandler("reset_ai", reset_ai))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    dp.add_handler(MessageHandler(Filters.text, button_handler))

    dp.add_error_handler(error)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
