import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory storage for active users
# For production, use a database (Render free tier restarts lose data)
active_users = set()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    active_users.add(chat_id)
    
    # Cancel any existing job for this chat
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    # Schedule hourly reminder
    context.job_queue.run_repeating(
        send_reminder,
        interval=3600,  # 1 hour in seconds
        first=10,       # first reminder after 10 seconds
        chat_id=chat_id,
        name=str(chat_id)
    )
    
    await update.message.reply_text(
        "✅ Hourly reminders activated!\n"
        "You will receive a message every hour.\n"
        "Use /stop to pause or /status to check."
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    active_users.discard(chat_id)
    
    current_jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    for job in current_jobs:
        job.schedule_removal()
    
    await update.message.reply_text("⏸ Reminders paused. Use /start to resume.")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.effective_chat.id
    jobs = context.job_queue.get_jobs_by_name(str(chat_id))
    
    if jobs:
        await update.message.reply_text("🟢 Reminders are ACTIVE (every hour).")
    else:
        await update.message.reply_text("🔴 Reminders are INACTIVE. Use /start to begin.")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Available commands:\n"
        "/start - Activate hourly reminders\n"
        "/stop - Pause reminders\n"
        "/status - Check status\n"
        "/help - Show this message"
    )

async def send_reminder(context: ContextTypes.DEFAULT_TYPE) -> None:
    job = context.job
    chat_id = job.chat_id
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text="⏰ Hourly reminder: Take a moment to check your tasks!"
        )
    except Exception as e:
        logger.error(f"Failed to send reminder to {chat_id}: {e}")

def main() -> None:
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise ValueError("BOT_TOKEN environment variable not set")
    
    application = Application.builder().token(token).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("stop", stop))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("help", help_command))
    
    logger.info("Bot starting...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
