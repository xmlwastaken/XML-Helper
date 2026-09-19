import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from shared import get_user_homework, save_user_homework
from core.school_utils import format_time_remaining, MOROCCO_TZ_OBJ

HOMEWORK_FILE = "storage/homework_assignments.json"

MANAGING_HOMEWORK, ADDING_TITLE, ADDING_DESCRIPTION, ADDING_DUE_DATE = range(4)

def get_all_assignments_sorted(user_id: str):
    assignments = get_user_homework(user_id)
    assignments.sort(key=lambda x: x['due_date'])
    return assignments

def format_assignment(assignment, include_index=False):
    due_date = datetime.fromisoformat(assignment['due_date'])
    time_left = format_time_remaining(due_date)
    now = datetime.now(MOROCCO_TZ_OBJ)
    
    if due_date < now:
        urgency = "🔴"
        status = "OVERDUE"
    elif "h" in time_left or "m" in time_left or "0d" in time_left:
        urgency = "🟡"
        status = time_left
    else:
        urgency = "🟢"
        status = time_left
    
    index = f"{assignment['id']}. " if include_index else ""
    
    return (
        f"{urgency} {index}*{assignment['title']}*\n"
        f"   📅 Due: {due_date.strftime('%a, %b %d at %H:%M')}\n"
        f"   ⏰ Status: {status}\n"
        f"   📝 {assignment.get('description', 'No description')}\n"
    )

async def homework_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    assignments = get_all_assignments_sorted(user_id)
    
    keyboard = [
        [InlineKeyboardButton("📋 View All Assignments", callback_data="hw_all")],
        [InlineKeyboardButton("➕ Add Assignment", callback_data="hw_add")],
        [InlineKeyboardButton("✅ Mark Complete", callback_data="hw_complete")],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if assignments:
        message = "📚 *Homework Manager*\n\n"
        message += f"You have *{len(assignments)} assignments* total\n\n"
        message += "Click 'View All Assignments' to see them sorted by due date."
    else:
        message = "📚 *Homework Manager*\n\n🎉 No assignments! You're all caught up!"
    
    message += "\n\nWhat would you like to do?"
    
    if update.message:
        await update.message.reply_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    elif update.callback_query:
        await update.callback_query.message.edit_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    
    return MANAGING_HOMEWORK

async def show_all_assignments(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    assignments = get_all_assignments_sorted(user_id)
    
    if not assignments:
        message = "📅 *All Assignments*\n\n🎉 No assignments!"
    else:
        message = "📅 *All Assignments* (Sorted by Due Date)\n\n"
        
        for assignment in assignments:
            message += format_assignment(assignment, include_index=True) + "\n"
    
    keyboard = [
        [InlineKeyboardButton("⬅️ Back", callback_data="hw_back")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    return MANAGING_HOMEWORK

async def start_add_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    context.user_data['new_assignment'] = {}
    
    await query.edit_message_text(
        "📝 *Adding New Assignment*\n\nEnter the assignment title:",
        parse_mode='Markdown'
    )
    return ADDING_TITLE

async def process_assignment_title(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    title = update.message.text
    context.user_data['new_assignment']['title'] = title
    
    await update.message.reply_text(
        "Enter assignment description (or type 'skip' for no description):"
    )
    return ADDING_DESCRIPTION

async def process_assignment_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    description = update.message.text
    if description.lower() != 'skip':
        context.user_data['new_assignment']['description'] = description
    
    await update.message.reply_text(
        "Enter due date (format: DD-MM-YYYY)\nExample: 20-01-2024"
    )
    return ADDING_DUE_DATE

async def process_due_date(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    due_date_str = update.message.text
    
    try:
        due_date = datetime.strptime(due_date_str, "%d-%m-%Y")
        due_date = MOROCCO_TZ_OBJ.localize(datetime.combine(due_date.date(), datetime.strptime("23:59", "%H:%M").time()))
        context.user_data['new_assignment']['due_date'] = due_date.isoformat()
    except ValueError:
        await update.message.reply_text(
            "❌ Invalid format. Please use: DD-MM-YYYY\nExample: 20-01-2024\nTry again:"
        )
        return ADDING_DUE_DATE
    
    user_id = str(update.effective_user.id)
    assignments = get_user_homework(user_id)
    
    new_id = max([a.get('id', 0) for a in assignments], default=0) + 1
    context.user_data['new_assignment']['id'] = new_id
    
    assignments.append(context.user_data['new_assignment'])
    save_user_homework(user_id, assignments)
    
    await update.message.reply_text("✅ Assignment added successfully!")
    return await homework_command(update, context)

async def mark_assignment_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    assignments = get_all_assignments_sorted(user_id)
    
    if not assignments:
        await query.edit_message_text("No assignments to mark complete!")
        return await homework_command(update, context)
    
    keyboard = []
    for assignment in assignments:
        btn_text = f"{assignment['id']}. {assignment['title'][:30]}..." if len(assignment['title']) > 30 else f"{assignment['id']}. {assignment['title']}"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"complete_{assignment['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Back", callback_data="hw_back")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "Select assignment to mark complete:",
        reply_markup=reply_markup
    )
    return MANAGING_HOMEWORK

async def complete_assignment(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    assignment_id = int(query.data.replace("complete_", ""))
    
    assignments = get_user_homework(user_id)
    assignments = [a for a in assignments if a['id'] != assignment_id]
    save_user_homework(user_id, assignments)
    
    await query.edit_message_text("✅ Assignment marked complete!")
    return await homework_command(update, context)

def get_homework_conversation_handler():
    return ConversationHandler(
        entry_points=[CommandHandler("homework", homework_command)],
        states={
            MANAGING_HOMEWORK: [
                CallbackQueryHandler(show_all_assignments, pattern="^hw_all$"),
                CallbackQueryHandler(start_add_assignment, pattern="^hw_add$"),
                CallbackQueryHandler(mark_assignment_complete, pattern="^hw_complete$"),
                CallbackQueryHandler(homework_command, pattern="^hw_back$"),
            ],
            ADDING_TITLE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_assignment_title)
            ],
            ADDING_DESCRIPTION: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_assignment_description)
            ],
            ADDING_DUE_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, process_due_date)
            ],
        },
        fallbacks=[CommandHandler("homework", homework_command)],
        per_message=False,
    )