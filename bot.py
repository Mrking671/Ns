import os
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

# Configure Kimi AI
KIMI_API_KEY = "sk-hGQSlTarv9Hoi0gKTqk4c3Ar5RKtSozVh4lqO17M7jznmMXk"
KIMI_API_URL = "https://api.moonshot.cn/v1/chat/completions"

# Verification settings
VERIFICATION_INTERVAL = timedelta(hours=12)

# Channel that users need to join to use the bot
REQUIRED_CHANNEL = "@public_botz"

# Channel where logs will be sent
LOG_CHANNEL = "@chatgptlogs"

# Admins and MongoDB setup
ADMINS = ["@Lordsakunaa", "6951715555"]
MONGO_URI = os.getenv('MONGO_URI')
client = MongoClient(MONGO_URI)
db = client['telegram_bot']
verification_collection = db['verification_data']

# Scheduler for auto-deletion of messages
scheduler = AsyncIOScheduler()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    if not await is_user_member_of_channel(context, update.effective_user.id):
        await send_join_channel_message(update, context)
        return

    if 'verified' in context.args:
        await handle_verification_redirect(update, context)
    else:
        user_data = verification_collection.find_one({'user_id': user_id})
        last_verified = user_data.get('last_verified') if user_data else None
        if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
            await send_start_message(update, context)
        else:
            await send_verification_message(update, context)

async def send_join_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Join Channel", url="https://t.me/public_botz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'To use this bot, you need to join our updates channel first.',
        reply_markup=reply_markup
    )

async def send_verification_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    verification_link = f"https://t.me/chatgpt490_bot?start=verified"
    keyboard = [
        [InlineKeyboardButton(
            "I'm not a robot🤖",
            url="https://linkshortify.com/st?api=7d706f6d7c95ff3fae2f2f40cff10abdc0e012e9&url=https://t.me/chatgpt490_bot?start=verified"
        )],
        [InlineKeyboardButton(
            "How to open captcha",
            url="https://t.me/disneysworl_d/5"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '⭕HCAPTCHA⭕\n\nPLEASE VERIFY THAT YOU ARE HUMAN 😳\n👇',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Welcome! Start sending your queries, and I will reply!',
    )

    scheduler.add_job(
        lambda: context.bot.delete_message(chat_id=update.effective_chat.id,
                                           message_id=update.message.message_id),
        trigger='date',
        run_date=datetime.now() + timedelta(minutes=30)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        logger.error("Received update without message")
        return

    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
        user_message = update.message.text
        
        # Enhanced prompt with explicit formatting instructions
        prompt = f"""You are an AI assistant. Follow these rules:
1. If asked about your version/model, respond with "KIMI AI"
2. Always format code blocks in Markdown with triple backticks
3. Provide clear, concise answers
4. Use proper Markdown formatting for all responses

User query: {user_message}"""
        
        try:
            headers = {
                "Authorization": f"Bearer {KIMI_API_KEY}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "moonshot-v1-8k",
                "messages": [{"role": "user", "content": prompt}]
            }
            response = requests.post(KIMI_API_URL, headers=headers, json=data)
            response.raise_for_status()
            
            reply = response.json()["choices"][0]["message"]["content"].strip()
            
            # Send formatted response with Markdown
            await update.message.reply_text(reply, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"API error: {e}")
            await update.message.reply_text("There was an error processing your request. Please try again.")
    else:
        await send_verification_message(update, context)

async def handle_verification_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    if 'verified' in update.message.text:
        verification_collection.update_one(
            {'user_id': user_id},
            {'$set': {'last_verified': current_time}},
            upsert=True
        )
        
        log_message = f"User {update.message.from_user.username} ({user_id}) verified."
        await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

        await send_start_message(update, context)
    else:
        await update.message.reply_text("Invalid verification link.")

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Membership check error: {e}")
        return False

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    help_message = """
To use this bot:
1. Send any message/question
2. The bot will respond in Markdown format
3. Code blocks are automatically formatted

Note: You must join @public_botz to use this bot
    """
    await update.message.reply_text(help_message)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(msg="Exception while handling update:", exc_info=context.error)
    await context.bot.send_message(chat_id=LOG_CHANNEL, text=f"Error occurred: {context.error}")

def main() -> None:
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    webhook_url = os.getenv("WEBHOOK_URL")
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8443")),
        url_path=os.getenv("TELEGRAM_TOKEN"),
        webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_TOKEN')}"
    )

if __name__ == "__main__":
    main()
