import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler,
)

from shared import get_user_settings, save_user_settings
from config import TRAIN_ROUTES, SCHOOL_GROUPS

(
    CHOOSING,
    AWAITING_TRAVEL_TO_STATION,
    AWAITING_TRAVEL_FROM_STATION,
    CHOOSING_TRAIN_ROUTE,
    CHOOSING_SCHOOL_GROUP,
) = range(5)

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    
    keyboard = [
        [
            InlineKeyboardButton(
                f"To Station: {settings['travel_time_to_station_mins']} mins",
                callback_data="change_travel_to_station",
            )
        ],
        [
            InlineKeyboardButton(
                f"From Station: {settings['travel_time_from_station_to_school_mins']} mins",
                callback_data="change_travel_from_station",
            )
        ],
        [
            InlineKeyboardButton(
                f"Train Route: {TRAIN_ROUTES[settings.get('train_route', 'bouznika_rabat')]}",
                callback_data="change_train_route",
            )
        ],
        [
            InlineKeyboardButton(
                f"School Group: {SCHOOL_GROUPS[settings.get('school_group', 'G1')]}",
                callback_data="change_school_group",
            )
        ],
        [InlineKeyboardButton("✅ Done", callback_data="done")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = "⚙️ *Settings Menu*\n\nSelect a setting to change:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=message_text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=message_text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    return CHOOSING

async def ask_for_new_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    setting_to_change = query.data

    context.user_data["setting_to_change"] = setting_to_change

    if setting_to_change == "change_travel_to_station":
        await query.edit_message_text(
            "Enter new travel time to the station (in minutes):"
        )
        return AWAITING_TRAVEL_TO_STATION
    elif setting_to_change == "change_travel_from_station":
        await query.edit_message_text(
            "Enter new travel time from the station (in minutes):"
        )
        return AWAITING_TRAVEL_FROM_STATION
    elif setting_to_change == "change_train_route":
        keyboard = [
            [InlineKeyboardButton("Bouznika - Rabat", callback_data="route_bouznika_rabat")],
            [InlineKeyboardButton("Mohammedia - Rabat", callback_data="route_mohammedia_rabat")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🚆 Select your train route:",
            reply_markup=reply_markup
        )
        return CHOOSING_TRAIN_ROUTE
    elif setting_to_change == "change_school_group":
        keyboard = [
            [InlineKeyboardButton("Group 1 (G1)", callback_data="group_G1")],
            [InlineKeyboardButton("Group 2 (G2)", callback_data="group_G2")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_to_settings")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "🏫 Select your school group:",
            reply_markup=reply_markup
        )
        return CHOOSING_SCHOOL_GROUP
    return CHOOSING

async def update_train_route(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    
    if query.data == "route_bouznika_rabat":
        settings['train_route'] = 'bouznika_rabat'
        await query.edit_message_text("✅ Train route set to: Bouznika - Rabat")
    elif query.data == "route_mohammedia_rabat":
        settings['train_route'] = 'mohammedia_rabat'
        await query.edit_message_text("✅ Train route set to: Mohammedia - Rabat")
    
    save_user_settings(user_id, settings)
    return await settings_command(update, context)

async def update_school_group(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)
    
    if query.data == "group_G1":
        settings['school_group'] = 'G1'
        await query.edit_message_text("✅ School group set to: Group 1 (G1)")
    elif query.data == "group_G2":
        settings['school_group'] = 'G2'
        await query.edit_message_text("✅ School group set to: Group 2 (G2)")
    
    save_user_settings(user_id, settings)
    return await settings_command(update, context)

async def update_value(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    new_value = update.message.text
    setting_to_change = context.user_data.get("setting_to_change")
    
    user_id = str(update.effective_user.id)
    settings = get_user_settings(user_id)

    if not new_value.isdigit():
        await update.message.reply_text("Invalid input. Please send a number.")
        if setting_to_change == "change_travel_to_station":
            return AWAITING_TRAVEL_TO_STATION
        elif setting_to_change == "change_travel_from_station":
            return AWAITING_TRAVEL_FROM_STATION

    key_to_update = {
        "change_travel_to_station": "travel_time_to_station_mins",
        "change_travel_from_station": "travel_time_from_station_to_school_mins",
    }.get(setting_to_change)

    if key_to_update:
        settings[key_to_update] = int(new_value)
        save_user_settings(user_id, settings)
        await update.message.reply_text("✅ Setting updated successfully!")
    else:
        await update.message.reply_text("An error occurred. Please try again.")

    await settings_command(update, context)
    return CHOOSING

async def back_to_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    return await settings_command(update, context)

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Settings saved. ✅")
    context.user_data.clear()
    return ConversationHandler.END

def get_settings_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("settings", settings_command)],
        states={
            CHOOSING: [
                CallbackQueryHandler(ask_for_new_value, pattern="^change_"),
                CallbackQueryHandler(done, pattern="^done$"),
            ],
            AWAITING_TRAVEL_TO_STATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_value)
            ],
            AWAITING_TRAVEL_FROM_STATION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, update_value)
            ],
            CHOOSING_TRAIN_ROUTE: [
                CallbackQueryHandler(update_train_route, pattern="^route_"),
                CallbackQueryHandler(back_to_settings, pattern="^back_to_settings$"),
            ],
            CHOOSING_SCHOOL_GROUP: [
                CallbackQueryHandler(update_school_group, pattern="^group_"),
                CallbackQueryHandler(back_to_settings, pattern="^back_to_settings$"),
            ],
        },
        fallbacks=[CommandHandler("cancel", done)],
        per_message=False,
    )