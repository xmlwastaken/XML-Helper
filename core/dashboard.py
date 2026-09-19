from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.error import BadRequest

from shared import get_user_settings
from config import TRAIN_ROUTES
from core.school import format_next_class, format_today_schedule
from core.train import format_next_train_response
from core.commute import format_commute_plan
from core.visuals import make_schedule_card, make_train_card
from core.school import get_current_day_and_time, get_user_classes
from core.train import find_next_train
from shared import format_timedelta


def _main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎓 School", callback_data="dash_school"), InlineKeyboardButton("🚆 Train", callback_data="dash_train")],
        [InlineKeyboardButton("🧭 Commute Plan", callback_data="dash_commute")],
        [InlineKeyboardButton("🖼 Today Card", callback_data="dash_today_card"), InlineKeyboardButton("🖼 Train Card", callback_data="dash_train_card")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="dash_settings")],
    ])


async def dashboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    route = TRAIN_ROUTES.get(settings.get('train_route', 'bouznika_rabat'), 'Bouznika - Rabat')
    text = (
        "✨ *XML Helper Dashboard*\n\n"
        f"🚆 Route: *{route}*\n"
        f"🏫 Group: *{settings.get('school_group', 'G1')}*\n\n"
        "Choose what you need:"
    )
    await update.message.reply_text(text, reply_markup=_main_keyboard(), parse_mode='Markdown')


async def dashboard_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    user_id = str(update.effective_user.id)
    data = query.data

    if data == "dash_school":
        text = format_next_class(user_id) + "\n\n" + format_today_schedule(user_id)
    elif data == "dash_train":
        text = format_next_train_response(user_id, 'to_rabat')
    elif data == "dash_commute":
        text = format_commute_plan(user_id)
    elif data == "dash_settings":
        text = "Use /settings to update route, group, and travel times."
    elif data == "dash_today_card":
        await send_today_card(update, context, from_callback=True)
        return
    elif data == "dash_train_card":
        await send_train_card(update, context, from_callback=True)
        return
    else:
        text = "Unknown dashboard action."

    try:
        await query.edit_message_text(text, reply_markup=_main_keyboard(), parse_mode='Markdown')
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            raise


async def send_today_card(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False) -> None:
    user_id = str(update.effective_user.id)
    day, _ = get_current_day_and_time()
    classes = get_user_classes(user_id, day)
    items = [
        {"time": f"{c['start_time']} - {c['end_time']}", "title": c['subject'], "meta": c['location']}
        for c in classes
    ]
    img = make_schedule_card("Today's Classes", day.title(), items)
    target = update.callback_query.message if from_callback else update.message
    if img:
        await target.reply_photo(photo=img, caption="🖼 Your visual schedule card")
    else:
        await target.reply_text(format_today_schedule(user_id), parse_mode='Markdown')


async def send_train_card(update: Update, context: ContextTypes.DEFAULT_TYPE, from_callback: bool = False) -> None:
    user_id = str(update.effective_user.id)
    nxt = find_next_train(user_id, 'to_rabat')
    if nxt:
        nxt['time_to_text'] = format_timedelta(nxt['time_to']).replace('in ', '')
    img = make_train_card("Next Train to Rabat", nxt)
    target = update.callback_query.message if from_callback else update.message
    if img:
        await target.reply_photo(photo=img, caption="🚆 Your next train card")
    else:
        await target.reply_text(format_next_train_response(user_id, 'to_rabat'), parse_mode='Markdown')
