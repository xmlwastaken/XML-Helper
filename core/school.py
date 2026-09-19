import pytz
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from shared import load_json, get_user_settings
from config import SCHOOL_SCHEDULE_FILE, DAY_ORDER, MOROCCO_TZ, CALLBACK_BACK_TO_SCHOOL_MENU

MOROCCO_TZ_OBJ = pytz.timezone(MOROCCO_TZ)


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
    """Load the timetable fresh every time so GitHub/Wispbyte pulls are reflected after restart."""
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    school_schedule = load_json(SCHOOL_SCHEDULE_FILE)
    day_classes = school_schedule.get(day_name, [])

    filtered_classes = []
    for subject in day_classes:
        if not subject.get('group') or subject.get('group') == user_group:
            filtered_classes.append(subject)

    return sorted(filtered_classes, key=lambda item: item.get('start_time', '99:99'))


def get_next_class(user_id: str):
    """Return the next upcoming class today or within the next week."""
    _, now = get_current_day_and_time()

    for day_offset in range(7):
        target_date = now.date() + timedelta(days=day_offset)
        day_name = target_date.strftime("%A").upper()
        for subject in get_user_classes(user_id, day_name):
            start = datetime.strptime(subject['start_time'], "%H:%M").time()
            start_dt = MOROCCO_TZ_OBJ.localize(datetime.combine(target_date, start))
            if start_dt > now:
                return day_name, start_dt, subject
    return None


def format_weekly_overview(user_id: str):
    current_day, _ = get_current_day_and_time()
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')

    message = f"📚 *Your Weekly Schedule (Group {user_group})*\n\n"
    total_classes = 0

    for day in DAY_ORDER:
        day_classes = get_user_classes(user_id, day)
        if day_classes:
            total_classes += len(day_classes)
            day_indicator = "✅" if day == current_day else "📅"
            message += f"{day_indicator} *{day}*\n"
            for subject in day_classes:
                message += f"   {format_subject(subject)}"
            message += "\n"

    message += f"📊 *Weekly Total:* {total_classes} classes"
    return message


def format_today_schedule(user_id: str):
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')
    current_day, _ = get_current_day_and_time()
    today_classes = get_user_classes(user_id, current_day)

    if today_classes:
        response_text = f"📖 *Today's Classes - {current_day} (Group {user_group})*\n\n"
        for subject in today_classes:
            response_text += format_subject(subject) + "\n"
        return response_text
    return f"🎉 *No classes today!*\nEnjoy your free time on {current_day}!"


def format_next_class(user_id: str):
    upcoming = get_next_class(user_id)
    if not upcoming:
        return "🎉 *No upcoming classes found this week.*"

    day_name, start_dt, subject = upcoming
    _, now = get_current_day_and_time()
    minutes = int((start_dt - now).total_seconds() // 60)
    hours, mins = divmod(minutes, 60)
    if hours >= 24:
        days, hours = divmod(hours, 24)
        starts_in = f"in {days} day{'s' if days != 1 else ''} and {hours} hour{'s' if hours != 1 else ''}"
    elif hours > 0:
        starts_in = f"in {hours} hour{'s' if hours != 1 else ''} and {mins} minute{'s' if mins != 1 else ''}"
    else:
        starts_in = f"in {mins} minute{'s' if mins != 1 else ''}"

    return (
        f"⏭️ *Next Class - {day_name.title()}*\n\n"
        f"Starts {starts_in}\n\n"
        f"{format_subject(subject)}"
    )


async def school_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    user_group = settings.get('school_group', 'G1')

    keyboard = [
        [InlineKeyboardButton("⏭️ Next Class", callback_data="next_school_class")],
        [InlineKeyboardButton("📖 Today's Classes", callback_data="today_schedule")],
        [InlineKeyboardButton("🗓️ Full Week", callback_data="weekly_overview")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    current_day, _ = get_current_day_and_time()
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
        try:
            await update.callback_query.message.edit_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise


async def today_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_today_schedule(user_id), parse_mode='Markdown')


async def week_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_weekly_overview(user_id), parse_mode='Markdown')


async def next_class_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    await update.message.reply_text(format_next_class(user_id), parse_mode='Markdown')


async def handle_school_schedule(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    data = query.data

    if data == "today_schedule":
        response_text = format_today_schedule(user_id)
    elif data == "weekly_overview":
        response_text = format_weekly_overview(user_id)
    elif data == "next_school_class":
        response_text = format_next_class(user_id)
    else:
        response_text = "Unknown school option."

    back_button = [[InlineKeyboardButton("🔙 Back to School Menu", callback_data=CALLBACK_BACK_TO_SCHOOL_MENU)]]
    await query.edit_message_text(text=response_text, reply_markup=InlineKeyboardMarkup(back_button), parse_mode='Markdown')


async def back_to_school_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await school_command(update, context)
