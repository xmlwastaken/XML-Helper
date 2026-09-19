# XML Helper Bot

A Telegram assistant for school, train schedules, commute planning, tasks, homework, and weather.

## Updated data

- `storage/class_timetable.json` from `Emplois du Temps - 5°IAII.pdf`, effective 2026-09-21.
- `storage/bouznika_rabat.json` from `Casa-Kenitra-phase-2.pdf`, effective 2026-09-14.

## New rich features

- `/dashboard` — rich button dashboard.
- `/commute` or `/plan` — smart plan for the next class: chooses the best train, leave-home time, arrival buffer.
- `/today` — today's classes.
- `/nextclass` — next upcoming class.
- `/week` — full weekly timetable.
- `/card` — visual PNG timetable card.
- `/nexttrain` — next train to Rabat.
- `/fromrabat` — next train from Rabat.
- `/traincard` — visual PNG train card.
- Telegram command menu is registered automatically on startup.
- Morning commute reminders respect your school group and skip trains that do not run on Sundays/public holidays.

## Wispbyte setup

Set your real Telegram token in Wispbyte **Startup -> Environment Variables**:

```env
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
OPENWEATHERMAP_API_KEY=optional_openweathermap_key_here
```

Do not upload `.env` to GitHub.

Startup command:

```bash
python bot.py
```

or:

```bash
python3 bot.py
```

Install packages from `requirements.txt`. If Wispbyte asks for package names, use:

```text
python-telegram-bot[job-queue]==21.10 python-dotenv==1.1.1 pytz==2025.2 requests==2.32.3 APScheduler==3.10.4 Pillow==11.3.0
```

## Manual corrections applied

- Monday Maintenance: 16:45-18:45
- Tuesday Management et contrôle Qualité: 15:00-18:15
- Wednesday Audit et efficacité énergétique: 10:15-11:45
