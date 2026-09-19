import os
import requests
from telegram import Update
from telegram.ext import ContextTypes

from shared import get_user_settings

from dotenv import load_dotenv
load_dotenv()

WEATHER_API_KEY = os.getenv("OPENWEATHERMAP_API_KEY")

async def weather_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    train_route = settings.get('train_route', 'bouznika_rabat')
    
    if train_route == 'bouznika_rabat':
        CITIES = ["Benslimane", "Bouznika", "Rabat"]
    else:
        CITIES = ["Mohammedia", "Rabat"]

    if not WEATHER_API_KEY:
        if update.message:
            await update.message.reply_text(
                "❌ *Weather service is currently unavailable*\n\n"
                "The weather feature requires an API key that hasn't been configured yet. "
                "Please check your environment variables or contact the bot administrator.",
                parse_mode="Markdown"
            )
        return

    full_weather_report = "🌤️ *Current Weather Report*\n\n"

    for city in CITIES:
        url = (
            f"http://api.openweathermap.org/data/2.5/weather?q={city}"
            f"&appid={WEATHER_API_KEY}&units=metric"
        )
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()

            if data.get("cod") != 200:
                full_weather_report += (
                    f"📍 *{city}*\n"
                    f"   ❌ API Error: {data.get('message', 'Unknown error')}\n\n"
                )
                continue

            weather_desc = data["weather"][0]["description"].title()
            temp = data["main"]["temp"]
            feels_like = data["main"]["feels_like"]
            humidity = data["main"]["humidity"]

            full_weather_report += (
                f"📍 *{city}*\n"
                f"   🌡️ {temp}°C (feels like {feels_like}°C)\n"
                f"   ☁️ {weather_desc}\n"
                f"   💧 {humidity}% humidity\n\n"
            )

        except requests.exceptions.RequestException as e:
            full_weather_report += (
                f"📍 *{city}*\n"
                f"   ❌ Network error: {str(e)}\n\n"
            )
        except Exception as e:
            full_weather_report += (
                f"📍 *{city}*\n"
                f"   ❌ Unexpected error: {str(e)}\n\n"
            )

    if update.message:
        await update.message.reply_text(full_weather_report, parse_mode="Markdown")