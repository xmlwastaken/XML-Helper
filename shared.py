import json
import math
import os
from datetime import timedelta
from telegram.ext import ContextTypes

# These functions are defined here, so they don't need to be imported
def load_json(file_path: str) -> list | dict:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Return empty list for specific files, otherwise empty dict
        list_types = ["todo_list", "homework", "study_sessions"]
        return [] if any(x in file_path for x in list_types) else {}

def save_json(file_path: str, data: list | dict) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def format_timedelta(td: timedelta) -> str:
    total_minutes = math.ceil(td.total_seconds() / 60)
    if total_minutes < 1:
        return "now"
    days, remaining_minutes = divmod(total_minutes, 1440)
    hours, minutes = divmod(remaining_minutes, 60)
    parts = []
    if days > 0: parts.append(f"{days} day{'s' if days > 1 else ''}")
    if hours > 0: parts.append(f"{hours} hour{'s' if hours > 1 else ''}")
    if minutes > 0: parts.append(f"{minutes} minute{'s' if minutes > 1 else ''}")
    return "in " + " and ".join(parts) if parts else "now"

def get_user_settings(user_id: str) -> dict:
    all_settings = load_json("storage/user_preferences.json")
    uid = str(user_id)
    if uid not in all_settings:
        all_settings[uid] = {
            "travel_time_to_station_mins": 45,
            "travel_time_from_station_to_school_mins": 15,
            "train_route": "bouznika_rabat",
            "school_group": "G1",
            "user_telegram_id": uid
        }
        save_json("storage/user_preferences.json", all_settings)
    return all_settings[uid]

def save_user_settings(user_id: str, settings: dict) -> None:
    all_settings = load_json("storage/user_preferences.json")
    all_settings[str(user_id)] = settings
    save_json("storage/user_preferences.json", all_settings)

def get_user_tasks(user_id: str) -> list:
    return load_json(f"storage/todo_list_{user_id}.json")

def save_user_tasks(user_id: str, tasks: list) -> None:
    save_json(f"storage/todo_list_{user_id}.json", tasks)

def get_user_homework(user_id: str) -> list:
    return load_json(f"storage/homework_assignments_{user_id}.json")

def save_user_homework(user_id: str, homework: list) -> None:
    save_json(f"storage/homework_assignments_{user_id}.json", homework)