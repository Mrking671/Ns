import os
import json
from flask import Flask, request, redirect
from telegram import Update, Bot
from telegram.ext import Dispatcher, CommandHandler, MessageHandler, Filters, CallbackContext
from telegram.ext import Updater
from pymongo import MongoClient
import datetime

app = Flask(__name__)

# Replace this with your actual bot token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
# MongoDB URI
MONGO_URI = os.getenv("MONGO_URI")

bot = Bot(token=TELEGRAM_TOKEN)
dispatcher = Dispatcher(bot, None, workers=0)

client = MongoClient(MONGO_URI)
db = client['bot_db']
users_collection = db['users']

# Verification URL
VERIFICATION_URL = "https://your-blogspot-url.com/verify"

# Helper functions
def check_verification(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if user:
        last_verified = user.get('last_verified')
        if last_verified:
            time_diff = datetime.datetime.now() - last_verified
            return time_diff.total_seconds() < 43200  # 12 hours
    return False

def update_verification(user_id):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"last_verified": datetime.datetime.now()}},
        upsert=True
    )

# Command handlers
def start(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if check_verification(user_id):
        update.message.reply_text('Welcome back! You are verified.')
    else:
        update.message.reply_text(
            'You need to verify yourself before using the bot. Click the button below to verify.',
            reply_markup=telegram.ReplyKeyboardMarkup([[telegram.KeyboardButton('Verify')]])
        )

def verify(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not check_verification(user_id):
        update.message.reply_text(
            'Please open the following link in your browser and stay there for 1 minute to verify: ' + VERIFICATION_URL
        )
    else:
        update.message.reply_text('You are already verified!')

def handle_message(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if not check_verification(user_id):
        update.message.reply_text('You need to verify yourself first. Use /verify to start the verification process.')
        return

    text = update.message.text

    if text.startswith('/chatgpt'):
        api_url = "https://chatgpt.darkhacker7301.workers.dev/?question=" + text[len('/chatgpt '):]
    elif text.startswith('/girlfriendai'):
        api_url = "https://chatgpt.darkhacker7301.workers.dev/?question=" + text[len('/girlfriendai '):] + "&state=girlfriend"
    elif text.startswith('/jarvis'):
        api_url = "https://jarvis.darkhacker7301.workers.dev/?question=" + text[len('/jarvis '):] + "&state=jarvis"
    elif text.startswith('/zenith'):
        api_url = "https://ashlynn.darkhacker7301.workers.dev/?question=" + text[len('/zenith '):] + "&state=Zenith"
    else:
        api_url = "https://chatgpt.darkhacker7301.workers.dev/?question=" + text

    response = requests.get(api_url)
    data = response.json()
    answer = data.get("answer", "Sorry, I don't have an answer for that.")
    update.message.reply_text(answer)

# Add handlers to the dispatcher
dispatcher.add_handler(CommandHandler('start', start))
dispatcher.add_handler(CommandHandler('verify', verify))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

@app.route('/webhook', methods=['POST'])
def webhook():
    if request.method == 'POST':
        update = Update.de_json(request.get_json(force=True), bot)
        dispatcher.process_update(update)
        return 'OK'

if __name__ == '__main__':
    # Set up webhook when the bot starts
    bot.set_webhook(url=f"https://{os.environ['RENDER_EXTERNAL_HOSTNAME']}/webhook")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8443)))
