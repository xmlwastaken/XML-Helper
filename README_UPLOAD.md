# Updated bot files

Updated data:
- `storage/class_timetable.json` from `Emplois du Temps - 5°IAII.pdf`, effective 2026-09-21.
- `storage/bouznika_rabat.json` from `Casa-Kenitra-phase-2.pdf`, effective 2026-09-14.

Upload everything to GitHub/Wispbyte except `.env`.
Set your real `TELEGRAM_BOT_TOKEN` in Wispbyte Startup -> Environment Variables.

Startup command on Wispbyte:

```bash
python bot.py
```

or, if required by your image:

```bash
python3 bot.py
```


Manual corrections applied after timetable review:
- Monday Maintenance: 16:45-18:45
- Tuesday Management et contrôle Qualité: 15:00-18:15
- Wednesday Audit et efficacité énergétique: 10:15-11:45

Bot improvements included:
- Added Telegram command menu setup on startup.
- Added quick commands: `/today`, `/week`, `/nextclass`, `/nexttrain`, `/fromrabat`.
- Added a Next Class button in the school menu.
- School timetable now reloads cleanly after updates/restarts.
- Morning commute reminders now respect school group filtering.
- Train reminders now skip trains marked as not running on Sundays/public holidays.
- Runtime/private user data is ignored for GitHub safety.
