from telegram import Update
from telegram.ext import (
    CommandHandler, CallbackQueryHandler, MessageHandler, filters,
    ConversationHandler, ContextTypes
)

from core import train, school, tasks, weather, alerts
from core.tasks import get_todo_conversation_handler
from core.settings import get_settings_conversation_handler
from core.homework import get_homework_conversation_handler

def setup_handlers(application):
    application.add_handler(get_settings_conversation_handler())
    application.add_handler(get_todo_conversation_handler())
    application.add_handler(get_homework_conversation_handler())
    
    application.add_handler(CommandHandler("start", alerts.start))
    application.add_handler(CommandHandler("weather", weather.weather_command))
    application.add_handler(CommandHandler("train", train.train_command))
    application.add_handler(CommandHandler("school", school.school_command))
    application.add_handler(CommandHandler("homework", get_homework_conversation_handler().entry_points[0].callback))
    
    application.add_handler(CallbackQueryHandler(train.next_train_callback, pattern="^next_"))
    application.add_handler(CallbackQueryHandler(train.full_schedule_callback, pattern="^full_"))
    application.add_handler(CallbackQueryHandler(train.back_to_train_menu, pattern="^back_to_train_menu$"))
    
    application.add_handler(
        CallbackQueryHandler(
            school.handle_school_schedule,
            pattern="^(today_schedule|weekly_overview)$",
        )
    )
    application.add_handler(CallbackQueryHandler(school.back_to_school_menu, pattern="^school_back_to_menu$"))