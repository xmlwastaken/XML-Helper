import json
import pytz
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler

from shared import load_json, get_user_settings
from config import SCHOOL_SCHEDULE_FILE, DAY_ORDER, MOROCCO_TZ, CALLBACK_BACK_TO_SCHOOL_MENU, SCHOOL_GROUPS

MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)
school_schedule = load_json(SCHOOL_SCHEDULE_FILE)

def get_current_day_and_time() -> tuple[str, datetime]:
    now = datetime.now(MOROCCO_TZ_OBJ)
    current_day_name = now.strftime("%A").upper()
    return current_day_name, now

def format_subject(subject_info: dict) -> str:
    group_info = f" (Group {subject_info['group']})" if subject_info.get('group') else ""
    return (
        f"🎯 {subject_info['subject']}{group_info}\n"
        f"   ⏰ {subject_info['start_time']} - {subject_info['end_time']}\n"
        f"   📍 {subject_info['location']}\n"
    )

def get_user_classes(user_id: str, day_name: str):
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    
    day_classes = school_schedule.get(day_name, [])
    
    if not day_classes:
        return []
    
    filtered_classes = []
    for subject in day_classes:
        if not subject.get('group'):
            filtered_classes.append(subject)
        elif subject.get('group') == user_group:
            filtered_classes.append(subject)
    
    return filtered_classes

def format_weekly_overview(user_id: str):
    weekly_schedule = load_json(SCHOOL_SCHEDULE_FILE)
    current_day, now = get_current_day_and_time()
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    
    message = f"📚 *Your Weekly Schedule (Group {user_group})*\n\n"
    
    for day in DAY_ORDER:
        day_classes = get_user_classes(user_id, day)
        if day_classes:
            day_indicator = "✅" if day == current_day else "📅"
            message += f"{day_indicator} *{day}*\n"
            
            for subject in day_classes:
                message += f"   {format_subject(subject)}"
            message += "\n"
    
    total_classes = sum(len(get_user_classes(user_id, day)) for day in DAY_ORDER)
    message += f"📊 *Weekly Total:* {total_classes} classes"
    
    return message

async def school_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    
    keyboard = [
        [InlineKeyboardButton("📖 Today's Classes", callback_data="today_schedule")],
        [InlineKeyboardButton("🗓️ Full Week", callback_data="weekly_overview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    current_day, now = get_current_day_and_time()
    today_classes = get_user_classes(user_id, current_day)
    
    message_text = f"🎓 *School Schedule (Group {user_group})*\n\n"
    
    if today_classes:
        message_text += f"Today is *{current_day}* - you have *{len(today_classes)} classes*\n"
    else:
        message_text += f"Today is *{current_day}* - no classes scheduled\n"
    
    message_text += "\nChoose what you'd like to view:"

    if update.message:
        await update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_school_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    
    data = query.data
    response_text = ""

    if data == "today_schedule":
        current_day, _ = get_current_day_and_time()
        today_classes = get_user_classes(user_id, current_day)
        if today_classes:
            response_text = f"📖 *Today's Classes - {current_day} (Group {user_group})*\n\n"
            for subject in today_classes:
                response_text += format_subject(subject) + "\n"
        else:
            response_text = f"🎉 *No classes today!*\nEnjoy your free time on {current_day}!"

    elif data == "weekly_overview":
        response_text = format_weekly_overview(user_id)

    back_button = [
        [InlineKeyboardButton("🔙 Back to School Menu", callback_data=CALLBACK_BACK_TO_SCHOOL_MENU)]
    ]
    await query.edit_message_text(text=response_text, reply_markup=InlineKeyboardMarkup(back_button), parse_mode='Markdown')

async def back_to_school_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await school_command(update, context)