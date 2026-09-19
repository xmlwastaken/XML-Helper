from __future__ import annotations

from datetime import datetime, timedelta
import pytz
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import MOROCCO_TZ, BOUZNIKA_TIMETABLE_FILE, MOHAMMEDIA_TIMETABLE_FILE
from shared import load_json, get_user_settings, format_timedelta
from core.school import get_next_class, format_subject
from core.train import is_sunday_or_holiday

MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)


def _route_info(settings: dict):
    route = settings.get('train_route', 'bouznika_rabat')
    if route == 'mohammedia_rabat':
        return load_json(MOHAMMEDIA_TIMETABLE_FILE), 'mohammedia_to_rabat', 'Mohammedia - Rabat', 'departure', 'arrival'
    return load_json(BOUZNIKA_TIMETABLE_FILE), 'bouznika_to_rabat', 'Bouznika - Rabat', 'Bouznika', 'Rabat Ville'


def find_best_train_for_next_class(user_id: str):
    upcoming = get_next_class(user_id)
    if not upcoming:
        return None, None

    day_name, class_start_dt, subject = upcoming
    settings = get_user_settings(user_id)
    data, key, route_name, dep_key, arr_key = _route_info(settings)
    travel_from_station = int(settings.get('travel_time_from_station_to_school_mins', 15))
    travel_to_station = int(settings.get('travel_time_to_station_mins', 45))
    latest_station_arrival = class_start_dt - timedelta(minutes=travel_from_station)
    is_sun_hol = is_sunday_or_holiday(class_start_dt)

    best = None
    for train in data.get(key, []):
        if is_sun_hol and not train.get('operates_weekends', True):
            continue
        dep = train.get(dep_key)
        arr = train.get(arr_key)
        if not dep or not arr:
            continue
        arr_dt = MOROCCO_TZ_OBJ.localize(datetime.combine(class_start_dt.date(), datetime.strptime(arr, '%H:%M').time()))
        dep_dt = MOROCCO_TZ_OBJ.localize(datetime.combine(class_start_dt.date(), datetime.strptime(dep, '%H:%M').time()))
        if arr_dt <= latest_station_arrival:
            best = {
                'train': train,
                'route_name': route_name,
                'departure': dep,
                'arrival': arr,
                'departure_dt': dep_dt,
                'arrival_dt': arr_dt,
                'leave_home_dt': dep_dt - timedelta(minutes=travel_to_station),
                'station_buffer_mins': int((latest_station_arrival - arr_dt).total_seconds() // 60),
            }
    return (day_name, class_start_dt, subject), best


def format_commute_plan(user_id: str) -> str:
    upcoming, best = find_best_train_for_next_class(user_id)
    if not upcoming:
        return "🎉 No upcoming class found this week."

    day_name, class_start_dt, subject = upcoming
    now = datetime.now(MOROCCO_TZ_OBJ)
    text = (
        f"🧭 *Smart Commute Plan*\n\n"
        f"🏫 *Next class:* {day_name.title()} at {class_start_dt.strftime('%H:%M')}\n"
        f"{format_subject(subject)}\n"
    )

    if not best:
        text += "⚠️ I couldn't find a train that arrives early enough for this class."
        return text

    train = best['train']
    leave_delta = best['leave_home_dt'] - now
    leave_text = format_timedelta(leave_delta) if leave_delta.total_seconds() > 0 else "now / already passed"
    text += (
        f"🚆 *Best train:* {train.get('train_number', 'N/A')} — {best['route_name']}\n"
        f"📍 Depart: {best['departure']}\n"
        f"🎯 Arrive Rabat Ville: {best['arrival']}\n"
        f"🚶 Leave home: {best['leave_home_dt'].strftime('%H:%M')} ({leave_text})\n"
        f"🕒 Buffer before class/tram/walk: {best['station_buffer_mins']} min\n"
    )
    if not train.get('operates_weekends', True):
        text += "\n📌 This train does not run on Sundays/public holidays."
    return text


async def commute_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("🚆 Open Train Menu", callback_data='back_to_train_menu')]]
    await update.message.reply_text(format_commute_plan(user_id), reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
