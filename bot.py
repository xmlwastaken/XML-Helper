import os
import datetime
import logging
import pytz
from dotenv import load_dotenv
from telegram.ext import Application, ContextTypes
from telegram.error import Conflict

from config import MOROCCO_TZ
from router import setup_handlers
from core.alerts import schedule_departure_reminder, send_todo_reminder

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and handle conflicts caused by multiple instances."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(context.error, Conflict):
        logger.fatal("Conflict: Another instance is running with this token. Please ensure only one server is active.")

def main() -> None:
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not bot_token:
        logger.error("Error: TELEGRAM_BOT_TOKEN environment variable is not set.")
        exit(1)

    application = Application.builder().token(bot_token).build()
    
    # Register global error handler
    application.add_error_handler(error_handler)
    
    setup_handlers(application)
    
    morocco_tz = pytz.timezone(MOROCCO_TZ)
    if application.job_queue:
        application.job_queue.run_daily(
            schedule_departure_reminder,
            time=datetime.time(hour=4, minute=0, tzinfo=morocco_tz),
            days=tuple(range(7)),
            name="departure_scheduler"
        )
        
        application.job_queue.run_daily(
            send_todo_reminder,
            time=datetime.time(hour=6, minute=30, tzinfo=morocco_tz),
            days=tuple(range(7)),
            name="morning_reminder"
        )
        
        application.job_queue.run_daily(
            send_todo_reminder,
            time=datetime.time(hour=22, minute=0, tzinfo=morocco_tz),
            days=tuple(range(7)),
            name="evening_reminder"
        )

    logger.info("Bot is starting. Dropping pending updates...")
    # drop_pending_updates=True prevents the bot from processing old messages on restart
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()