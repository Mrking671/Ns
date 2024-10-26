
        # User needs to verify again
        await send_verification_message(update, context)

async def handle_verification_redirect(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.message.from_user.id)
    current_time = datetime.now()

    # Update user verification status
    verification_collection.update_one(
        {'user_id': user_id},
        {'$set': {'last_verified': current_time}},
        upsert=True
    )
    await update.message.reply_text('ʏᴏᴜ ᴀʀᴇ ɴᴏᴡ ᴠᴇʀғɪᴇᴅ!🥰')
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

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMINS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    message_text = ' '.join(context.args)
    if not message_text:
        await update.message.reply_text("Please provide a message to broadcast.")
        return

    users = verification_collection.find({})
    for user in users:
        try:
            await context.bot.send_message(chat_id=user['user_id'], text=message_text)
        except Exception as e:
            logger.error(f"Error sending broadcast to {user['user_id']}: {e}")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if str(update.message.from_user.id) not in ADMINS:
        await update.message.reply_text("You don't have permission to use this command.")
        return

    user_count = verification_collection.count_documents({})
    await update.message.reply_text(f"Number of verified users: {user_count}")

def main():
    # Create the application with the provided bot token
    application = ApplicationBuilder().token(os.getenv("TELEGRAM_TOKEN")).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex(r'.*verified.*'), handle_verification_redirect))
    application.add_handler(CommandHandler("broadcast", broadcast, filters=filters.User(username=ADMINS)))
    application.add_handler(CommandHandler("stats", stats, filters=filters.User(username=ADMINS)))

    # Add error handler
    application.add_error_handler(error)

    # Start the webhook to listen for updates
    PORT = int(os.environ.get("PORT", 8443))
    WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Make sure to set this environment variable in your Render settings
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=os.getenv("TELEGRAM_TOKEN"),
        webhook_url=f"{WEBHOOK_URL}/{os.getenv('TELEGRAM_TOKEN')}"
    )

if __name__ == '__main__':
    main()
