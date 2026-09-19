import json
import math
import os
import requests
from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from shared import format_timedelta, load_json, get_user_settings
from config import BOUZNIKA_TIMETABLE_FILE, MOHAMMEDIA_TIMETABLE_FILE, MOROCCO_TZ, TRAIN_ROUTES

from dotenv import load_dotenv
load_dotenv()

MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)

# Fixed-date Moroccan public holidays for the 2026 school year.
# Trains marked with * in the ONCF PDF do not run on Sundays/public holidays.
MOROCCO_HOLIDAYS = [
    "2026-01-01", "2026-01-11", "2026-05-01", "2026-07-30",
    "2026-08-14", "2026-08-20", "2026-08-21", "2026-11-06", "2026-11-18"
]

def is_sunday_or_holiday(now: datetime) -> bool:
    if now.weekday() == 6:
        return True
    today_str = now.strftime("%Y-%m-%d")
    return today_str in MOROCCO_HOLIDAYS

def get_user_train_data(user_id: str):
    settings = get_user_settings(user_id)
    train_route = settings.get('train_route', 'bouznika_rabat')
    
    if train_route == 'mohammedia_rabat':
        # Freshly load data to reflect any file changes immediately
        mohammedia_data = load_json(MOHAMMEDIA_TIMETABLE_FILE)
        return mohammedia_data, 'mohammedia_to_rabat', 'rabat_to_mohammedia', 'Mohammedia - Rabat'
    else:
        # Freshly load data to reflect any file changes immediately
        bouznika_data = load_json(BOUZNIKA_TIMETABLE_FILE)
        return bouznika_data, 'bouznika_to_rabat', 'rabat_to_bouznika', 'Bouznika - Rabat'

def get_weather_for_city_at_time(city: str, arrival_time_str: str) -> str:
    api_key = os.getenv("OPENWEATHERMAP_API_KEY")
    if not api_key:
        return "Weather forecast not available"
    
    try:
        arrival_time = datetime.strptime(arrival_time_str, "%H:%M").time()
        today = datetime.now(MOROCCO_TZ_OBJ).date()
        arrival_datetime = MOROCCO_TZ_OBJ.localize(datetime.combine(today, arrival_time))
        timestamp = int(arrival_datetime.timestamp())
        
        url = f"http://api.openweathermap.org/data/2.5/forecast?q={city}&appid={api_key}&units=metric"
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        closest_forecast = None
        min_time_diff = float('inf')
        
        for forecast in data.get('list', []):
            forecast_time = forecast['dt']
            time_diff = abs(forecast_time - timestamp)
            if time_diff < min_time_diff:
                min_time_diff = time_diff
                closest_forecast = forecast
        
        if closest_forecast:
            weather_desc = closest_forecast["weather"][0]["description"].title()
            temp = closest_forecast["main"]["temp"]
            feels_like = closest_forecast["main"]["feels_like"]
            return f"{weather_desc}, {temp}°C (feels like {feels_like}°C)"
        return "No forecast available for arrival time"
    except Exception as e:
        print(f"Weather API error: {e}")
        return "Could not retrieve weather forecast"

def find_next_train(user_id: str, direction: str):
    train_data, to_rabat_key, from_rabat_key, route_name = get_user_train_data(user_id)
    now = datetime.now(MOROCCO_TZ_OBJ)
    is_sun_hol = is_sunday_or_holiday(now)
    
    if direction == "to_rabat":
        schedule = train_data.get(to_rabat_key, [])
        weather_city = "Rabat"
    else:
        schedule = train_data.get(from_rabat_key, [])
        weather_city = "Bouznika" if "Bouznika" in route_name else "Mohammedia"

    for train in schedule:
        if is_sun_hol and not train.get('operates_weekends', True):
            continue
            
        if 'departure' in train:
            departure_time_str = train.get('departure')
            arrival_time_str = train.get('arrival')
        else:
            if direction == "to_rabat":
                departure_time_str = train.get('Bouznika')
                arrival_time_str = train.get("Rabat Ville")
            else:
                departure_time_str = train.get("Rabat Ville")
                arrival_time_str = train.get('Bouznika')
                
        if departure_time_str:
            departure_time_obj = datetime.strptime(departure_time_str, "%H:%M").time()
            departure_datetime = MOROCCO_TZ_OBJ.localize(datetime.combine(now.date(), departure_time_obj))
            if departure_datetime > now:
                weather_info = get_weather_for_city_at_time(weather_city, arrival_time_str)
                return {
                    "train_number": train.get("train_number"),
                    "train_type": train.get("type"),
                    "departure_time": departure_time_str,
                    "arrival_time": arrival_time_str,
                    "time_to": departure_datetime - now,
                    "operates_weekends": train.get('operates_weekends', True),
                    "destination_weather": weather_info,
                    "weather_city": weather_city,
                    "route_name": route_name
                }
    return None

def format_next_train_response(user_id: str, direction: str) -> str:
    direction_key = "to_rabat" if direction == "to_rabat" else "from_rabat"
    dir_icon = "➡" if direction_key == "to_rabat" else "⬅"
    next_train_data = find_next_train(user_id, direction_key)

    if not next_train_data:
        return "🌙 *No more trains available today*"

    t_num = str(next_train_data.get('train_number', 'N/A'))
    t_type = next_train_data.get('train_type', '')
    type_disp = f" ({t_type})" if t_type else ""
    time_to = format_timedelta(next_train_data['time_to'])
    weekend_warning = "\n\n📌 *Note:* This train does not run on Sundays/public holidays" if not next_train_data.get('operates_weekends', True) else ""

    return (
        f"{dir_icon} *Next Train - {next_train_data['route_name']}*\n\n"
        f"🚆 *Train {t_num}{type_disp}*\n"
        f"⏰ *Departing:* {time_to}\n"
        f"📍 *Departure:* {next_train_data['departure_time']}\n"
        f"🎯 *Arrival:* {next_train_data['arrival_time']}\n\n"
        f"🌤 *Weather in {next_train_data['weather_city']} at arrival:*\n"
        f"{next_train_data['destination_weather']}{weekend_warning}"
    )


def format_full_day_schedule(user_id: str, direction: str):
    train_data, to_rabat_key, from_rabat_key, route_name = get_user_train_data(user_id)
    now = datetime.now(MOROCCO_TZ_OBJ)
    is_sun_hol = is_sunday_or_holiday(now)
    
    if direction == "to_rabat":
        schedule = train_data.get(to_rabat_key, [])
        header = f"🚆 *{route_name} - Complete Schedule*\n\n"
    else:
        schedule = train_data.get(from_rabat_key, [])
        parts = route_name.split(' - ')
        header = f"🚆 *{parts[1]} - {parts[0]} - Complete Schedule*\n\n"
    
    train_info = ""
    for train in schedule:
        if is_sun_hol and not train.get('operates_weekends', True):
            continue
           
        if 'departure' in train:
            dep_time = train.get('departure', 'N/A')
            arr_time = train.get('arrival', 'N/A')
        else:
            if direction == "to_rabat":
                dep_time = train.get('Bouznika', 'N/A')
                arr_time = train.get("Rabat Ville", 'N/A')
            else:
                dep_time = train.get("Rabat Ville", 'N/A')
                arr_time = train.get('Bouznika', 'N/A')
            
        if dep_time != 'N/A':
            dep_time_obj = datetime.strptime(dep_time, "%H:%M").time()
            dep_dt = MOROCCO_TZ_OBJ.localize(datetime.combine(now.date(), dep_time_obj))
            
            t_num = str(train.get("train_number", 'N/A'))
            t_type = train.get('type', '')
            type_disp = f" ({t_type})" if t_type else ""
            weekend_warn = " 🚫" if not train.get('operates_weekends', True) else ""
          
            if dep_dt < now:
                train_info += f"⚫ {t_num}{type_disp}{weekend_warn}\n"
                train_info += f"   {dep_time} → {arr_time} _(Departed)_\n\n"
            else:
                train_info += f"🟢 {t_num}{type_disp}{weekend_warn}\n"
                train_info += f"   {dep_time} → {arr_time}\n\n"
    
    return header + (train_info if train_info else "🌙 No trains scheduled for today\n\n")

async def train_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    train_route = TRAIN_ROUTES[settings.get('train_route', 'bouznika_rabat')]
    
    keyboard = [
        [InlineKeyboardButton("➡ Next to Rabat", callback_data='next_to_rabat'),
         InlineKeyboardButton("📋 All to Rabat", callback_data='full_to_rabat')],
        [InlineKeyboardButton("⬅ Next from Rabat", callback_data='next_from_rabat'),
         InlineKeyboardButton("📋 All from Rabat", callback_data='full_from_rabat')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    msg = (
        f"🚆 *Train Schedule - {train_route}*\n\n"
        "Check train times and schedules for your commute.\n"
        "Trains marked 🚫 do not run on Sundays/public holidays."
    )
    if update.message:
        await update.message.reply_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        try:
            await update.callback_query.message.edit_text(msg, reply_markup=reply_markup, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" not in str(e): raise


async def next_to_rabat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_next_train_response(user_id, "to_rabat"), parse_mode='Markdown')


async def next_from_rabat_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_next_train_response(user_id, "from_rabat"), parse_mode='Markdown')

async def next_train_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    
    direction_key = "to_rabat" if query.data == 'next_to_rabat' else "from_rabat"
    dir_icon = "➡" if direction_key == "to_rabat" else "⬅"
    next_train_data = find_next_train(user_id, direction_key)

    if next_train_data:
        t_num = str(next_train_data.get('train_number', 'N/A'))
        t_type = next_train_data.get('train_type', '')
        type_disp = f" ({t_type})" if t_type else ""
        time_to = format_timedelta(next_train_data['time_to'])
        weekend_warning = "\n\n📌 *Note:* No service on Sundays/holidays" if not next_train_data.get('operates_weekends', True) else ""
        
        response = (
            f"{dir_icon} *Next Train - {next_train_data['route_name']}*\n\n"
            f"🚆 *Train {t_num}{type_disp}*\n"
            f"⏰ *Departing:* {time_to}\n"
            f"📍 *Departure:* {next_train_data['departure_time']}\n"
            f"🎯 *Arrival:* {next_train_data['arrival_time']}\n\n"
            f"🌤 *Weather in {next_train_data['weather_city']} at arrival:*\n"
            f"{next_train_data['destination_weather']}{weekend_warning}"
        )
    else:
        response = "🌙 *No more trains available today*"

    back_button = [[InlineKeyboardButton("🔙 Back to Trains", callback_data='back_to_train_menu')]]
    await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup(back_button), parse_mode='Markdown')

async def full_schedule_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    
    response = format_full_day_schedule(user_id, "to_rabat" if query.data == 'full_to_rabat' else "from_rabat")
    back_button = [[InlineKeyboardButton("🔙 Back to Trains", callback_data='back_to_train_menu')]]
    await query.edit_message_text(response, reply_markup=InlineKeyboardMarkup(back_button), parse_mode='Markdown')

async def back_to_train_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        await train_command(update, context)
    except BadRequest as e:
        if "Message is not modified" not in str(e): raise