from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)

from shared import get_user_tasks, save_user_tasks

SELECTING_ACTION, AWAITING_TASK_DESCRIPTION, AWAITING_TASK_NUMBER = range(3)

def get_tasks_text(user_id: str) -> str:
    tasks = get_user_tasks(user_id)
    if not tasks:
        return "🎉 Your to-do list is empty! Add a task to get started."

    tasks_text = "📝 *Your To-Do List*:\n\n"
    for i, task in enumerate(tasks, 1):
        tasks_text += f"`{i}.` {task}\n"
    return tasks_text

async def start_todo_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = str(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("➕ Add a Task", callback_data="add")],
        [InlineKeyboardButton("✅ Complete a Task", callback_data="done")],
        [InlineKeyboardButton("❌ Close Menu", callback_data="close")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    tasks_text = get_tasks_text(user_id)
    menu_text = f"{tasks_text}\n\n*What would you like to do?*"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(
            text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
        )
    else:
        await update.message.reply_text(
            text=menu_text, reply_markup=reply_markup, parse_mode="Markdown"
        )

    return SELECTING_ACTION

async def prompt_for_task_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="✏️ Okay, what task would you like to add?",
        reply_markup=reply_markup
    )
    return AWAITING_TASK_DESCRIPTION

async def add_new_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task_description = update.message.text
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    tasks.append(task_description)
    save_user_tasks(user_id, tasks)

    await update.message.reply_text(
        f"✅ Task added: *{task_description}*", parse_mode="Markdown"
    )
    return await start_todo_command(update, context)

async def prompt_for_task_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()

    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)
    if not tasks:
        await query.answer("Your to-do list is already empty!", show_alert=True)
        return SELECTING_ACTION

    keyboard = [[InlineKeyboardButton("⬅️ Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text="🔢 Please send the number of the task you want to complete.",
        reply_markup=reply_markup,
    )
    return AWAITING_TASK_NUMBER

async def complete_task(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    task_number_str = update.message.text
    user_id = str(update.effective_user.id)
    tasks = get_user_tasks(user_id)

    if not task_number_str.isdigit() or not (1 <= int(task_number_str) <= len(tasks)):
        await update.message.reply_text(
            "That's not a valid task number. Please try again."
        )
        return AWAITING_TASK_NUMBER

    task_number = int(task_number_str)
    removed_task = tasks.pop(task_number - 1)
    save_user_tasks(user_id, tasks)

    await update.message.reply_text(
        f"👍 Great job! Task completed: *{removed_task}*",
        parse_mode="Markdown"
    )
    return await start_todo_command(update, context)

async def close_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("✅ To-Do menu closed.")
    return ConversationHandler.END

def get_todo_conversation_handler() -> ConversationHandler:
    return ConversationHandler(
        entry_points=[CommandHandler("tasks", start_todo_command)],
        states={
            SELECTING_ACTION: [
                CallbackQueryHandler(prompt_for_task_description, pattern="^add$"),
                CallbackQueryHandler(prompt_for_task_number, pattern="^done$"),
                CallbackQueryHandler(close_menu, pattern="^close$"),
            ],
            AWAITING_TASK_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_new_task),
                CallbackQueryHandler(start_todo_command, pattern="^back_to_menu$"),
            ],
            AWAITING_TASK_NUMBER: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, complete_task),
                CallbackQueryHandler(start_todo_command, pattern="^back_to_menu$"),
            ],
        },
        fallbacks=[CommandHandler("tasks", start_todo_command)],
        per_message=False,
    )