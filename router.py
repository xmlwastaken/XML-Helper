from telegram.ext import CommandHandler, CallbackQueryHandler

from core import train, school, tasks, weather, alerts, dashboard, commute
from core.tasks import get_todo_conversation_handler
from core.settings import get_settings_conversation_handler
from core.homework import get_homework_conversation_handler


def setup_handlers(application):
    # Conversation handlers first so their callbacks/messages are captured correctly.
    application.add_handler(get_settings_conversation_handler())
    application.add_handler(get_todo_conversation_handler())
    application.add_handler(get_homework_conversation_handler())

    # Main commands
    application.add_handler(CommandHandler("start", alerts.start))
    application.add_handler(CommandHandler("help", alerts.start))
    application.add_handler(CommandHandler("dashboard", dashboard.dashboard_command))
    application.add_handler(CommandHandler("home", dashboard.dashboard_command))

    # School commands
    application.add_handler(CommandHandler("school", school.school_command))
    application.add_handler(CommandHandler("today", school.today_command))
    application.add_handler(CommandHandler("week", school.week_command))
    application.add_handler(CommandHandler("nextclass", school.next_class_command))
    application.add_handler(CommandHandler("card", dashboard.send_today_card))

    # Train/commute commands
    application.add_handler(CommandHandler("train", train.train_command))
    application.add_handler(CommandHandler("nexttrain", train.next_to_rabat_command))
    application.add_handler(CommandHandler("fromrabat", train.next_from_rabat_command))
    application.add_handler(CommandHandler("traincard", dashboard.send_train_card))
    application.add_handler(CommandHandler("commute", commute.commute_command))
    application.add_handler(CommandHandler("plan", commute.commute_command))

    # Utilities
    application.add_handler(CommandHandler("weather", weather.weather_command))
    application.add_handler(CommandHandler("homework", get_homework_conversation_handler().entry_points[0].callback))

    # Dashboard callbacks
    application.add_handler(CallbackQueryHandler(dashboard.dashboard_callback, pattern="^dash_"))

    # Train callbacks
    application.add_handler(CallbackQueryHandler(train.next_train_callback, pattern="^next_(to_rabat|from_rabat)$"))
    application.add_handler(CallbackQueryHandler(train.full_schedule_callback, pattern="^full_"))
    application.add_handler(CallbackQueryHandler(train.back_to_train_menu, pattern="^back_to_train_menu$"))

    # School callbacks
    application.add_handler(
        CallbackQueryHandler(
            school.handle_school_schedule,
            pattern="^(today_schedule|weekly_overview|next_school_class)$",
        )
    )
    application.add_handler(CallbackQueryHandler(school.back_to_school_menu, pattern="^school_back_to_menu$"))
