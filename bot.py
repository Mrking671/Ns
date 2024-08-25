import os
import logging
import requests
import json
from pymongo import MongoClient
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

# Admin ID(s)
ADMIN_IDS = [6951715555]  # Your Telegram ID

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
DEFAULT_AI = 'chatgpt'

# Verification settings
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification

# MongoDB setup
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["chatgpt_bot"]
collection = db["users"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user has joined the required channel
    if not await is_user_member_of_channel(context, update.effective_user.id):
        await send_join_channel_message(update, context)
        return

    last_verified = collection.find_one({"user_id": user_id})
    if last_verified and current_time - datetime.fromisoformat(last_verified['last_verified']) < VERIFICATION_INTERVAL:
        await send_start_message(update, context)
    else:
        await send_verification_message(update, context)

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id="@purplebotz", user_id=user_id)
        return member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        logger.error(f"Error checking user membership status: {e}")
        return False

async def send_join_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Join Channel", url="https://t.me/purplebotz")]]
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
        [InlineKeyboardButton("Talk to GPT-4", callback_data='gpt4')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text('Welcome! Select an AI to start talking:', reply_markup=reply_markup)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    text = update.message.text

    # Ensure the user is verified and a member of the channel
    if not await is_user_member_of_channel(context, update.effective_user.id):
        await send_join_channel_message(update, context)
        return

    last_verified = collection.find_one({"user_id": user_id})
    if last_verified and datetime.now() - datetime.fromisoformat(last_verified['last_verified']) > VERIFICATION_INTERVAL:
        await send_verification_message(update, context)
        return

    # Handle the message with the default AI
    await respond_with_ai(update, context, text, DEFAULT_AI)

async def respond_with_ai(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str, ai: str) -> None:
    if ai not in API_URLS:
        ai = DEFAULT_AI

    api_url = API_URLS[ai].format(text)
    response = requests.get(api_url)
    answer = response.json().get('answer', "Sorry, I couldn't process your request.")
    await update.message.reply_text(answer)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    ai_choice = query.data
    await query.edit_message_text(text=f"Selected option: {ai_choice}\nPlease send me a message to continue.")
    context.user_data['ai_choice'] = ai_choice

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    total_users = collection.count_documents({})
    await update.message.reply_text(f"Total users: {total_users}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    message = ' '.join(context.args)
    if not message:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    users = collection.find({})
    failed_count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=message)
        except Exception as e:
            failed_count += 1
            logger.error(f"Failed to send message to {user['user_id']}: {e}")

    await update.message.reply_text(f"Broadcast sent. Failed to send to {failed_count} users.")

def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stats", stats))
    application.add_handler(CommandHandler("broadcast", broadcast, filters=filters.User(ADMIN_IDS)))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
