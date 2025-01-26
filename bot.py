import os
import logging
import google.generativeai as genai
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

# Configure Gemini AI
genai.configure(api_key="AIzaSyC712T9g0E43i3JcA2uSaNDS6kP8NjjjBY")
model = genai.GenerativeModel("gemini-1.5-flash")

# Verification settings
VERIFICATION_INTERVAL = timedelta(hours=12)  # 12 hours for re-verification

# Channel that users need to join to use the bot
REQUIRED_CHANNEL = "@public_botz"  # Replace with your channel

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
        user_data = verification_collection.find_one({'user_id': user_id})
        last_verified = user_data.get('last_verified') if user_data else None
        if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
            await send_start_message(update, context)
        else:
            await send_verification_message(update, context)

async def send_join_channel_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    keyboard = [[InlineKeyboardButton("Join Channel", url=f"https://t.me/public_botz")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'To use this bot, you need to join our updates channel first.',
        reply_markup=reply_markup
    )

async def send_verification_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    verification_link = f"https://t.me/{context.bot.username}?start=verified"
    keyboard = [
        [InlineKeyboardButton(
            "I'm not a robot🤖",  # New button (not a web app)
            url=f"https://linkshortify.com/st?api=7d706f6d7c95ff3fae2f2f40cff10abdc0e012e9&url=https://t.me/{context.bot.username}?start=verified"
        )],
        [InlineKeyboardButton(
            "How to open captcha",  # New button (not a web app)
            url="https://t.me/disneysworl_d/5"
        )]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        '⭕𝗖𝗔𝗣𝗧𝗖𝗛𝗔⭕\n\n𝐏𝐋𝐄𝐀𝐒𝐄 𝐕𝐄𝐑𝐈𝐅𝐘 𝐓𝐇𝐀𝐓 𝐘𝐎𝐔 𝐀𝐑𝐄 𝐀 𝐇𝐔𝐌𝐀𝐍 😳\n👇',
        reply_markup=reply_markup
    )

async def send_start_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        'Welcome! Start sending your queries, and I will reply!',
    )

    # Schedule auto-deletion of the message
    scheduler.add_job(
        lambda: context.bot.delete_message(chat_message_id=update.message.message_id,
                                                 chat_id=update.effective_chat.id),
        trigger='date',
        run_date=datetime.now() + timedelta(minutes=30)
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check verification status
    user_data = verification_collection.find_one({'user_id': user_id})
    last_verified = user_data.get('last_verified') if user_data else None
    if last_verified and current_time - last_verified < VERIFICATION_INTERVAL:
        user_message = update.message.text
        
        # Send prompt to behave as GPT-4 for response
        prompt = f"You should behave like ChatGPT, an AI developed by OpenAI.If asked for version or model simply say gpt 4.Provide intelligent responses as GPT-4. User: {user_message}"
        
        try:
            # Use Gemini API for response generation but role-play as GPT-4
            response = model.generate_content(prompt)
            reply = response.text

            # Check if the reply contains code-like structure
            if any(keyword in reply for keyword in ["def ", "import ", "{", "}", "=", "<", ">", "class ", "function ", "def main"]):
                reply = f"```\n{reply}\n```"  # Format as code block
            else:
                reply = reply.strip()  # Remove extra spaces if it's normal text

            # Send the reply to the user
            await update.message.reply_text(reply, parse_mode="Markdown")

        except Exception as e:
            logger.error(f"API error: {e}")
            await update.message.reply_text("There was an error retrieving the response. Please try again later.")
    else:
        # User needs to verify again
        await send_verification_message(update, context)

async def handle_verification_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Check if the user has opened the verification link
    if 'verified' in update.message.text:
        # Update user verification status
        verification_collection.update_one(
            {'user_id': user_id},
            {'$set': {'last_verified': current_time}},
            upsert=True
        )
        
        # Send log to log channel
        log_message = f"User {update.message.from_user.username} ({user_id}) has been verified."
        await context.bot.send_message(chat_id=LOG_CHANNEL, text=log_message)

        await send_start_message(update, context)
    else:
        await update.message.reply_text("Invalid verification link.")

async def is_user_member_of_channel(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(REQUIRED_CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send a message with instructions on how to use the bot."""
    help_message = """
To use this bot, simply send a message with your query.
The bot will respond with an answer.

Note: You need to join our updates channel (@chatgpt4for_free) to use this bot.
    """
    await update.message.reply_text(help_message)

def main() -> None:
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add handlers for commands and messages
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Use webhook setup for deployment
    webhook_url = os.getenv("WEBHOOK_URL")  # Replace with your webhook URL
    application.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", "8443")),
        url_path=os.getenv("TELEGRAM_TOKEN"),
        webhook_url=f"{webhook_url}/{os.getenv('TELEGRAM_TOKEN')}"
    )

if __name__ == "__main__":
    main()
