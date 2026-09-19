# XML Helper Bot

A Telegram assistant focused on useful daily student features: school, trains, commute planning, weather, and outfit advice.

## Main commands

- `/dashboard` — main daily dashboard.
- `/commute` or `/plan` — best train plan for the next class.
- `/outfit` or `/clothes` — clothes recommendation based on:
  - your full school day,
  - estimated leave-home time from Benslimane,
  - Bouznika train departure,
  - Rabat school day,
  - return train and estimated home time,
  - all-day weather across Benslimane, Bouznika, and Rabat.
- `/today` — today's classes.
- `/nextclass` — next upcoming class.
- `/week` — full weekly timetable.
- `/nexttrain` — next train to Rabat.
- `/fromrabat` — next train from Rabat.
- `/weather` — current weather.
- `/settings` — route, group, and travel times.

Hidden but still available if wanted:

- `/card` — visual PNG timetable card.
- `/traincard` — visual PNG train card.

## Data

- `storage/class_timetable.json` from `Emplois du Temps - 5°IAII.pdf`, effective 2026-09-21.
- `storage/bouznika_rabat.json` from `Casa-Kenitra-phase-2.pdf`, effective 2026-09-14.

Manual corrections applied:

- Monday Maintenance: 16:45-18:45
- Tuesday Management et contrôle Qualité: 15:00-18:15
- Wednesday Audit et efficacité énergétique: 10:15-11:45

## Wispbyte setup

Set environment variables in Wispbyte **Startup -> Environment Variables**:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENWEATHERMAP_API_KEY=your_openweathermap_key_here
```

`OPENWEATHERMAP_API_KEY` is required for full `/outfit` weather-based advice. Without it, the bot still gives a basic clothing suggestion.

Startup command:

```bash
python bot.py
```

or:

```bash
python3 bot.py
```

Install packages from `requirements.txt`. If Wispbyte asks for package names manually:

```text
python-telegram-bot[job-queue]==21.10 python-dotenv==1.1.1 pytz==2025.2 requests==2.32.3 APScheduler==3.10.4 Pillow==11.3.0
```

Do not upload `.env` to GitHub.
