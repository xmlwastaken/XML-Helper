from __future__ import annotations

import os
from datetime import datetime, timedelta
from statistics import mean

import pytz
import requests
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import MOROCCO_TZ, BOUZNIKA_TIMETABLE_FILE, MOHAMMEDIA_TIMETABLE_FILE
from shared import get_user_settings, load_json
from core.school import get_next_class, get_user_classes, format_subject
from core.commute import find_best_train_for_next_class
from core.train import is_sunday_or_holiday

load_dotenv()
WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")
MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)

CITIES = ["Benslimane", "Bouznika", "Rabat"]


def _parse_time_on_date(date, hhmm: str) -> datetime:
    return MOROCCO_TZ_OBJ.localize(datetime.combine(date, datetime.strptime(hhmm, "%H:%M").time()))


def _route_return_info(settings: dict):
    route = settings.get('train_route', 'bouznika_rabat')
    if route == 'mohammedia_rabat':
        return load_json(MOHAMMEDIA_TIMETABLE_FILE), 'rabat_to_mohammedia', 'departure', 'arrival', 'Mohammedia'
    return load_json(BOUZNIKA_TIMETABLE_FILE), 'rabat_to_bouznika', 'Rabat Ville', 'Bouznika', 'Bouznika'


def _find_return_train(settings: dict, after_dt: datetime):
    data, key, dep_key, arr_key, station_city = _route_return_info(settings)
    is_sun_hol = is_sunday_or_holiday(after_dt)
    for train in data.get(key, []):
        if is_sun_hol and not train.get('operates_weekends', True):
            continue
        dep = train.get(dep_key)
        arr = train.get(arr_key)
        if not dep or not arr:
            continue
        dep_dt = _parse_time_on_date(after_dt.date(), dep)
        arr_dt = _parse_time_on_date(after_dt.date(), arr)
        if dep_dt >= after_dt:
            return {
                'train': train,
                'departure': dep,
                'arrival': arr,
                'departure_dt': dep_dt,
                'arrival_dt': arr_dt,
                'station_city': station_city,
            }
    return None


def build_day_plan(user_id: str):
    """Build the useful full-day plan: leave home, train out, classes, train back, back home."""
    upcoming, best = find_best_train_for_next_class(user_id)
    if not upcoming:
        return None

    day_name, first_class_dt, first_subject = upcoming
    settings = get_user_settings(user_id)
    day_classes = get_user_classes(user_id, day_name)
    if not day_classes:
        return None

    last_class = max(day_classes, key=lambda c: c.get('end_time', '00:00'))
    last_end_dt = _parse_time_on_date(first_class_dt.date(), last_class['end_time'])
    school_to_station_mins = int(settings.get('travel_time_from_station_to_school_mins', 15))
    home_to_station_mins = int(settings.get('travel_time_to_station_mins', 45))

    earliest_rabat_departure = last_end_dt + timedelta(minutes=school_to_station_mins)
    return_train = _find_return_train(settings, earliest_rabat_departure)

    if best:
        leave_home_dt = best['leave_home_dt']
        outbound = best
    else:
        leave_home_dt = first_class_dt - timedelta(minutes=home_to_station_mins + school_to_station_mins)
        outbound = None

    back_home_dt = None
    if return_train:
        back_home_dt = return_train['arrival_dt'] + timedelta(minutes=home_to_station_mins)

    return {
        'day_name': day_name,
        'date': first_class_dt.date(),
        'classes': day_classes,
        'first_class_dt': first_class_dt,
        'last_class': last_class,
        'last_end_dt': last_end_dt,
        'leave_home_dt': leave_home_dt,
        'outbound': outbound,
        'earliest_rabat_departure': earliest_rabat_departure,
        'return_train': return_train,
        'back_home_dt': back_home_dt,
        'settings': settings,
    }


def _fetch_forecast(city: str):
    if not WEATHER_API_KEY:
        return None, "missing_api_key"
    url = "https://api.openweathermap.org/data/2.5/forecast"
    params = {"q": f"{city},MA", "appid": WEATHER_API_KEY, "units": "metric"}
    try:
        response = requests.get(url, params=params, timeout=12)
        response.raise_for_status()
        return response.json().get('list', []), None
    except Exception as exc:
        return None, str(exc)


def _forecast_window(city: str, start_dt: datetime, end_dt: datetime):
    forecasts, error = _fetch_forecast(city)
    if error:
        return {'city': city, 'error': error, 'points': []}

    points = []
    # include one slot before and after for 3-hour forecast resolution
    start_ts = int((start_dt - timedelta(hours=2)).timestamp())
    end_ts = int((end_dt + timedelta(hours=2)).timestamp())
    for item in forecasts:
        ts = int(item.get('dt', 0))
        if start_ts <= ts <= end_ts:
            points.append(item)

    if not points and forecasts:
        # Fallback to the nearest available points for that date.
        target_date = start_dt.date()
        for item in forecasts:
            dt = datetime.fromtimestamp(int(item.get('dt', 0)), MOROCCO_TZ_OBJ)
            if dt.date() == target_date:
                points.append(item)

    return {'city': city, 'points': points, 'error': None}


def _summarize_city_weather(city_data: dict):
    points = city_data.get('points', [])
    if not points:
        return None

    temps = [p['main']['temp'] for p in points]
    feels = [p['main'].get('feels_like', p['main']['temp']) for p in points]
    pops = [p.get('pop', 0) for p in points]
    winds = [p.get('wind', {}).get('speed', 0) for p in points]
    descriptions = [p.get('weather', [{}])[0].get('description', '').title() for p in points]
    rain_mm = sum(p.get('rain', {}).get('3h', 0) for p in points)

    return {
        'city': city_data['city'],
        'min_temp': min(temps),
        'max_temp': max(temps),
        'avg_feels': mean(feels),
        'rain_chance': max(pops) if pops else 0,
        'rain_mm': rain_mm,
        'max_wind': max(winds) if winds else 0,
        'descriptions': descriptions,
    }


def _overall_weather(start_dt: datetime, end_dt: datetime):
    city_summaries = []
    errors = []
    for city in CITIES:
        data = _forecast_window(city, start_dt, end_dt)
        if data.get('error'):
            errors.append((city, data['error']))
            continue
        summary = _summarize_city_weather(data)
        if summary:
            city_summaries.append(summary)
    if not city_summaries:
        return None, errors

    min_temp = min(c['min_temp'] for c in city_summaries)
    max_temp = max(c['max_temp'] for c in city_summaries)
    max_rain_chance = max(c['rain_chance'] for c in city_summaries)
    total_rain = sum(c['rain_mm'] for c in city_summaries)
    max_wind = max(c['max_wind'] for c in city_summaries)
    return {
        'cities': city_summaries,
        'min_temp': min_temp,
        'max_temp': max_temp,
        'max_rain_chance': max_rain_chance,
        'total_rain': total_rain,
        'max_wind': max_wind,
    }, errors


def _clothing_recommendation(weather: dict, leave_dt: datetime, back_dt: datetime | None):
    min_t = weather['min_temp']
    max_t = weather['max_temp']
    rain_chance = weather['max_rain_chance']
    rain_mm = weather['total_rain']
    wind = weather['max_wind']

    outfit = []
    extras = []

    if min_t <= 8:
        outfit.append("warm jacket or coat")
        outfit.append("hoodie/sweater layer")
    elif min_t <= 14:
        outfit.append("light jacket")
        outfit.append("sweater or hoodie")
    elif min_t <= 19:
        outfit.append("light overshirt/hoodie for morning and evening")
    else:
        outfit.append("light T-shirt or polo")

    if max_t >= 30:
        outfit.append("breathable clothes")
        extras.append("water bottle")
        extras.append("sunglasses/cap")
    elif max_t >= 24:
        outfit.append("comfortable light pants or jeans")
    else:
        outfit.append("jeans or comfortable pants")

    if rain_chance >= 0.55 or rain_mm >= 1.0:
        extras.append("umbrella")
        extras.append("water-resistant shoes/jacket")
    elif rain_chance >= 0.30:
        extras.append("small umbrella just in case")

    if wind >= 8:
        extras.append("avoid loose cap; wind is noticeable")

    # Long day note
    if back_dt:
        hours_out = (back_dt - leave_dt).total_seconds() / 3600
        if hours_out >= 10:
            extras.append("snack/power bank because it is a long day")

    return outfit, extras


def format_outfit_advice(user_id: str) -> str:
    plan = build_day_plan(user_id)
    if not plan:
        return "I couldn't find an upcoming school day to plan for. Check /school and your timetable."

    start_dt = plan['leave_home_dt']
    end_dt = plan['back_home_dt'] or (plan['last_end_dt'] + timedelta(hours=2))
    weather, errors = _overall_weather(start_dt, end_dt)

    text = (
        f"👕 *Outfit AI for {plan['day_name'].title()}*\n\n"
        f"🏠 Leave Benslimane: *{start_dt.strftime('%H:%M')}*\n"
    )
    if plan['outbound']:
        text += f"🚆 Bouznika → Rabat: *{plan['outbound']['departure']} → {plan['outbound']['arrival']}*\n"
    text += f"🏫 Classes: *{plan['first_class_dt'].strftime('%H:%M')} → {plan['last_end_dt'].strftime('%H:%M')}*\n"
    if plan['return_train']:
        text += f"🚆 Rabat → Bouznika: *{plan['return_train']['departure']} → {plan['return_train']['arrival']}*\n"
    if plan['back_home_dt']:
        text += f"🏠 Back home estimate: *{plan['back_home_dt'].strftime('%H:%M')}*\n"
    text += "\n"

    if not weather:
        text += (
            "⚠️ Weather forecast is unavailable. Add `OPENWEATHERMAP_API_KEY` in Wispbyte to enable smart outfit advice.\n\n"
            "Basic suggestion: wear comfortable shoes, jeans/pants, and carry a light layer because Benslimane/Bouznika mornings can feel cooler than Rabat."
        )
        return text

    outfit, extras = _clothing_recommendation(weather, start_dt, plan['back_home_dt'])
    text += (
        f"🌦️ *Weather across Benslimane, Bouznika, Rabat*\n"
        f"• Temp range: *{weather['min_temp']:.0f}°C → {weather['max_temp']:.0f}°C*\n"
        f"• Rain risk: *{weather['max_rain_chance'] * 100:.0f}%*\n"
        f"• Wind max: *{weather['max_wind']:.0f} m/s*\n\n"
        f"✅ *Wear:* {', '.join(outfit)}.\n"
    )
    if extras:
        text += f"🎒 *Take:* {', '.join(dict.fromkeys(extras))}.\n"

    text += "\n📍 *City details*\n"
    for city in weather['cities']:
        desc = city['descriptions'][0] if city['descriptions'] else "Forecast"
        text += (
            f"• {city['city']}: {city['min_temp']:.0f}-{city['max_temp']:.0f}°C, "
            f"rain {city['rain_chance'] * 100:.0f}%, {desc}\n"
        )

    return text


async def outfit_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    keyboard = [[InlineKeyboardButton("🧭 Commute Plan", callback_data="dash_commute")]]
    await update.message.reply_text(
        format_outfit_advice(user_id),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown",
    )
