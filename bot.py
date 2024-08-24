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
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification

# File for storing verification data
VERIFICATION_FILE = 'verification_data.json'

# Channel that users need to join to use the bot
REQUIRED_CHANNEL = "@purplebotz"  # Replace with your channel

# Channel where logs will be sent
LOG_CHANNEL = "@gaheggwgwi"  # Replace with your log channel

def load_verification_data():
    if os.path.exists(VERIFICATION_FILE):
        with open(VERIFICATION_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_verification_data(data):
    with open(VERIFICATION_FILE, 'w') as f:
        json.dump(data, f)

verification_data = load_verification_data()

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
        last_verified = verification_data.get(user_id, {}).get('last_verified', None)
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

    keyboard = [[InlineKeyboardButton("Verify Now", url="https://chatgptgiminiai.blogspot.com/2024/08/verification-page-body-font-family.html")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Please verify yourself by clicking the link below. You need to verify every 12 hours to use the bot.\n'
        'Once verified, you will be redirected back to the bot.',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [
        [InlineKeyboardButton("Talk to GirlfriendAI", callback_data='girlfriend')],
        [InlineKeyboardButton("Talk to JarvisAI", callback_data='jarvis')],
        [InlineKeyboardButton("Talk to ZenithAI", callback_data='zenith')],
        [InlineKeyboardButton("Reset to ChatGPT", callback_data='reset')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Welcome! Choose an AI to talk to by clicking a button. Available options are: GirlfriendAI, JarvisAI, ZenithAI.\n'
        'To reset to ChatGPT, click the button below.',
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data

    if data in API_URLS:
        context.user_data['selected_ai'] = data
        await query.answer()
        await query.edit_message_text(text=f'You are now chatting with {data.capitalize()}AI.')
    elif data == 'reset':
        context.user_data['selected_ai'] = DEFAULT_AI
        await query.answer()
        await query.edit_message_text(text='You are now reset to ChatGPT.')

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user is verified
    last_verified = verification_data.get(user_id, {}).get('last_verified', None)
    if last_verified and current_time - datetime.fromisoformat(last_verified) < VERIFICATION_INTERVAL:
        user_message = update.message.text
        selected_ai = context.user_data.get('selected_ai', DEFAULT_AI)
        api_url = API_URLS.get(selected_ai, API_URLS[DEFAULT_AI])
        try:
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
    verification_data[user_id] = {'last_verified': current_time.isoformat()}
    save_verification_data(verification_data)
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

async def broadcast_message(context: ContextTypes.DEFAULT_TYPE) -> None:
    message_text = context.job.context.get('message_text', 'This is a broadcast message')
    for user_id in verification_data.keys():
        try:
            await context.bot.send_message(chat_id=user_id, text=message_text)
        except Exception as e:
            logger.error(f"Error sending broadcast to {user_id}: {e}")

def main():
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'.*verified.*'), handle_verification_redirect))

    application.add_error_handler(error)

    application.run_polling()  # Use polling instead of webhook

if __name__ == '__main__':
    main()
