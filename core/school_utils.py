from datetime import datetime, timedelta
import pytz
from shared import load_json, save_json
from config import SCHOOL_SCHEDULE_FILE, MOROCCO_TZ

MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)

def get_current_day_name() -> str:
    now = datetime.now(MOROCCO_TZ_OBJ)
    return now.strftime("%A").upper()

def get_todays_classes():
    school_schedule = load_json(SCHOOL_SCHEDULE_FILE)
    day_name = get_current_day_name()
    return school_schedule.get(day_name, [])

def get_weekly_schedule():
    return load_json(SCHOOL_SCHEDULE_FILE)

def format_time_remaining(due_date: datetime) -> str:
    now = datetime.now(MOROCCO_TZ_OBJ)
    time_left = due_date - now
    
    if time_left.total_seconds() < 0:
        return "OVERDUE"
    
    days = time_left.days
    hours = int(time_left.seconds / 3600)
    
    if days > 0:
        return f"{days}d {hours}h"
    elif hours > 0:
        return f"{hours}h"
    else:
        minutes = int(time_left.seconds / 60)
        return f"{minutes}m"