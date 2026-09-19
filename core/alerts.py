import os
import json
import pytz
import requests
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes

from shared import load_json, get_user_settings, get_user_tasks
from config import USER_SETTINGS_FILE, SCHOOL_SCHEDULE_FILE, MOROCCO_TZ, TRAIN_ROUTES, BOUZNIKA_TIMETABLE_FILE, MOHAMMEDIA_TIMETABLE_FILE
from core.train import is_sunday_or_holiday

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    get_user_settings(user_id)
    
    welcome_message = (
        "Welcome to your Personal Assistant Bot!\n\n"
        "I'm here to help you stay organized. You can check your train and "
        "school schedules, get weather updates, manage tasks, and configure "
        "settings right from this chat.\n\n"
        "📋 All Available Commands\n\n"
        "🏫 School:\n"
        "/school - School menu\n"
        "/today - Today's classes\n"
        "/nextclass - Next upcoming class\n"
        "/week - Full weekly schedule\n"
        "/homework - Manage assignments\n\n"
        "🚆 Train:\n"
        "/train - Train menu\n"
        "/nexttrain - Next train to Rabat\n"
        "/fromrabat - Next train from Rabat\n\n"
        "🛠️ Utilities:\n"
        "/tasks - To-do list\n"
        "/weather - Weather forecast\n"
        "/settings - Bot settings\n\n"
        "Simply click any command above to use it!"
    )
    if update.message:
        await update.message.reply_text(welcome_message)

async def send_todo_reminder(context: ContextTypes.DEFAULT_TYPE):
    """Restored missing function to fix the ImportError"""
    try:
        all_settings = load_json(USER_SETTINGS_FILE)
    except FileNotFoundError:
        return

    for user_id_str, settings in all_settings.items():
        user_id = settings.get("user_telegram_id")
        if not user_id:
            continue
            
        tasks = get_user_tasks(user_id)
        if not tasks:
            continue

        message = f"🔔 Daily To-Do Reminder! 🔔\n\nYou have {len(tasks)} pending task(s):\n\n"
        for i, task in enumerate(tasks, 1):
            message += f"{i}. {task}\n"

        message += "\nUse the /tasks command to manage them."

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=message
            )
        except Exception as e:
            print(f"Failed to send reminder to user {user_id}: {e}")

def get_weather_for_rabat() -> str:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Weather data not available."

    url = f"http://api.openweathermap.org/data/2.5/weather?q=Rabat&appid={api_key}&units=metric"
    try:
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        weather_desc = data["weather"][0]["description"].title()
        temp = data["main"]["temp"]
        return f"{weather_desc}, {temp}°C"
    except requests.exceptions.RequestException:
        return "Could not retrieve weather data."

def filter_classes_for_group(day_schedule: list, school_group: str) -> list:
    return [
        subject for subject in day_schedule
        if not subject.get('group') or subject.get('group') == school_group
    ]


def format_day_schedule(day_schedule: list) -> str:
    schedule_text = ""
    for subject in day_schedule:
        group_text = f" ({subject['group']})" if subject.get('group') else ""
        schedule_text += (
            f"  • {subject['subject']}{group_text}\n"
            f"    Time: {subject['start_time']} - {subject['end_time']}\n"
            f"    Location: {subject['location']}\n"
        )
    return schedule_text.strip()

async def send_departure_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data.get("user_id")
    message = job_data.get("message")
    if user_id and message:
        await context.bot.send_message(chat_id=user_id, text=message)

async def schedule_departure_reminder(context: ContextTypes.DEFAULT_TYPE):
    try:
        all_settings = load_json(USER_SETTINGS_FILE)
        school_schedule = load_json(SCHOOL_SCHEDULE_FILE)
        bouznika_data = load_json(BOUZNIKA_TIMETABLE_FILE)
        mohammedia_data = load_json(MOHAMMEDIA_TIMETABLE_FILE)
    except FileNotFoundError:
        return

    morocco_tz = pytz.timezone(MOROCCO_TZ)
    today = datetime.now(morocco_tz)
    day_name = today.strftime('%A').upper()

    raw_day_schedule = school_schedule.get(day_name, [])
    if not raw_day_schedule:
        return

    is_sun_hol = is_sunday_or_holiday(today)

    for user_id_str, settings in all_settings.items():
        user_id = settings.get("user_telegram_id")
        if not user_id:
            continue

        user_group = settings.get('school_group', 'G1')
        day_schedule = filter_classes_for_group(raw_day_schedule, user_group)
        if not day_schedule:
            continue

        train_route = settings.get('train_route', 'bouznika_rabat')
        
        if train_route == 'mohammedia_rabat':
            train_data = mohammedia_data
            station_key = 'mohammedia_to_rabat'
            route_name = 'Mohammedia - Rabat'
        else:
            train_data = bouznika_data
            station_key = 'bouznika_to_rabat'
            route_name = 'Bouznika - Rabat'

        first_class = day_schedule[0]
        class_start_time_str = first_class['start_time']
        class_start_time = datetime.strptime(class_start_time_str, "%H:%M").time()
        first_class_datetime = morocco_tz.localize(datetime.combine(today.date(), class_start_time))

        travel_from_station_mins = settings.get('travel_time_from_station_to_school_mins', 15)
        latest_arrival_at_station = first_class_datetime - timedelta(minutes=travel_from_station_mins)

        suitable_train = None
        trains_to_rabat = train_data.get(station_key, [])
        
        for train in reversed(trains_to_rabat):
            if is_sun_hol and not train.get('operates_weekends', True):
                continue

            if train_route == 'mohammedia_rabat':
                arrival_time_str = train.get("arrival")
            else:
                arrival_time_str = train.get("Rabat Ville")
                
            if arrival_time_str:
                train_arrival_time = datetime.strptime(arrival_time_str, "%H:%M").time()
                train_arrival_datetime = morocco_tz.localize(datetime.combine(today.date(), train_arrival_time))
                if train_arrival_datetime <= latest_arrival_at_station:
                    suitable_train = train
                    break

        if not suitable_train:
            continue

        if train_route == 'mohammedia_rabat':
            train_departure_str = suitable_train['departure']
            train_arrival_str = suitable_train.get("arrival", "N/A")
        else:
            train_departure_str = suitable_train['Bouznika']
            train_arrival_str = suitable_train.get("Rabat Ville", "N/A")
            
        train_departure_time = datetime.strptime(train_departure_str, "%H:%M").time()
        train_departure_datetime = morocco_tz.localize(datetime.combine(today.date(), train_departure_time))

        # IMPROVED: Now uses the user's specific travel time setting instead of 90 minutes
        travel_to_station_mins = settings.get('travel_time_to_station_mins', 45)
        leave_home_datetime = train_departure_datetime - timedelta(minutes=travel_to_station_mins)

        if leave_home_datetime > today and context.job_queue:
            rabat_weather = get_weather_for_rabat()
            formatted_schedule = format_day_schedule(day_schedule)
            
            message = (
                f"☀️ Your Morning Briefing\n\n"
                f"Good morning! Here is your schedule and travel plan to get your day started.\n\n"
                f"🏫 Today's Schedule\n"
                f"{formatted_schedule}\n\n"
                f"🚆 Your Commute ({route_name})\n"
                f"  • Departure: {train_departure_str}\n"
                f"  • Arrival: {train_arrival_str}\n"
                f"  • Train: {suitable_train.get('train_number', 'N/A')} ({suitable_train.get('type', 'N/A')})\n\n"
                f"🌦️ Weather in Rabat\n"
                f"  • Forecast: {rabat_weather}\n\n"
                f"Have a great and productive day! ✨"
            )
            
            context.job_queue.run_once(
                send_departure_reminder,
                leave_home_datetime,
                data={"user_id": user_id, "message": message},
                name=f"departure_reminder_{user_id}"
            )