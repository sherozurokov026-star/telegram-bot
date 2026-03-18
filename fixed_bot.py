import logging
from datetime import datetime, timedelta

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

import gspread
from oauth2client.service_account import ServiceAccountCredentials

logging.basicConfig(level=logging.INFO)

# ⚠️ TOKENNI BU YERGA QO'YING (BotFather dan olingan yangi token)
TOKEN = "8105479376:AAHHSgBXJJbzYk2iBaydoXokZDSr9Xf4ZQU"
ADMIN_ID = 6495290274

EXECUTORS = {
    1699889770: "Manager",
    5573693040: "Kotibyat",
    8328138767: "Dizayner"
}

scope = [
    "https://spreadsheets.google.com/feeds",
    "https://www.googleapis.com/auth/drive"
]

creds = ServiceAccountCredentials.from_json_keyfile_name(
    "credentials.json", scope
)

client = gspread.authorize(creds)
sheet = client.open("TasksBot").sheet1


def get_next_task_id():
    rows = sheet.get_all_values()
    if len(rows) <= 1:
        return 1
    last = rows[-1][0]
    try:
        return int(last) + 1
    except:
        return len(rows)


def save_task(task_id, task, executor, deadline):
    deadline_str = deadline.strftime("%Y-%m-%d %H:%M")
    sheet.append_row([
        task_id,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        task,
        executor,
        deadline_str,
        "yangi"
    ])


def update_status(task_id):
    rows = sheet.get_all_values()
    for i in range(1, len(rows)):
        if rows[i][0] == str(task_id):
            sheet.update_cell(i + 1, 6, "bajarildi")
            break


def get_task_text(task_id):
    rows = sheet.get_all_values()
    for i in range(1, len(rows)):
        if rows[i][0] == str(task_id):
            return rows[i][2]
    return "Topilmadi"


def get_task_executor(task_id):
    rows = sheet.get_all_values()
    for i in range(1, len(rows)):
        if rows[i][0] == str(task_id):
            return rows[i][3]
    return "Noma'lum"


# -------------------- STATISTIKA --------------------

def get_executor_stats():
    rows = sheet.get_all_records()
    now = datetime.now()

    stats = {}

    for name in EXECUTORS.values():
        stats[name] = {"new": 0, "done": 0, "expired": 0}

    for r in rows:
        executor = r.get("Executor")
        status = r.get("Status")
        deadline = datetime.strptime(r["Deadline"], "%Y-%m-%d %H:%M")

        if executor not in stats:
            stats[executor] = {"new": 0, "done": 0, "expired": 0}

        if status == "bajarildi":
            stats[executor]["done"] += 1
        elif deadline < now:
            stats[executor]["expired"] += 1
        else:
            stats[executor]["new"] += 1

    return stats


# -------------------- DEADLINE --------------------

async def deadline_keyboard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("⏱ 1 soat", callback_data="deadline|1"),
            InlineKeyboardButton("⏱ 3 soat", callback_data="deadline|3")
        ],
        [
            InlineKeyboardButton("⏱ 6 soat", callback_data="deadline|6"),
            InlineKeyboardButton("🌙 12 soat", callback_data="deadline|12")
        ],
        [
            InlineKeyboardButton("📅 24 soat", callback_data="deadline|24")
        ]
    ]

    text = "⏰ <b>Muddatni tanlang</b>"

    if update.message:
        await update.message.reply_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )
    elif update.callback_query:
        query = update.callback_query
        await query.answer()

        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )


async def deadline_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    hours = int(query.data.split("|")[1])
    deadline = datetime.now() + timedelta(hours=hours)

    context.user_data["deadline"] = deadline
    context.user_data["selected_users"] = []

    keyboard = []

    for uid, name in EXECUTORS.items():
        keyboard.append([
            InlineKeyboardButton(f"⬜ {name}", callback_data=f"toggle|{uid}")
        ])

    keyboard.append([
        InlineKeyboardButton("🚀 Yuborish", callback_data="send_multi")
    ])

    await query.edit_message_text(
        "👥 <b>Ijrochilarni tanlang</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# -------------------- START --------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("📊 Statistik", callback_data="stats"),
            InlineKeyboardButton("📋 Barcha tasklar", callback_data="tasks")
        ]
    ]

    await update.message.reply_text(
        "✨ <b>TASK MANAGER BOT</b>\n\n"
        "📌 Task yuboring\n"
        "⏰ Muddat tanlang\n"
        "👤 Ijrochiga yuboriladi\n\n"
        "👇 <b>Menyu:</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# -------------------- STATISTIKA --------------------

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    stats = get_executor_stats()

    text = "📊 <b>IJROCHILAR STATISTIKASI</b>\n\n"

    user_id = query.from_user.id

    for name, data in stats.items():

        if user_id != ADMIN_ID:
            if EXECUTORS.get(user_id) != name:
                continue

        text += (
            f"👤 <b>{name}</b>\n"
            f"🆕 Yangi: <b>{data['new']}</b>\n"
            f"✅ Bajarilgan: <b>{data['done']}</b>\n"
            f"⏔ Muddati o'tgan: <b>{data['expired']}</b>\n\n"
        )

    await query.edit_message_text(text, parse_mode="HTML")


# -------------------- TASKLAR --------------------

async def all_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    rows = sheet.get_all_records()

    if not rows:
        await query.edit_message_text("❌ Tasklar yo‘q")
        return

    new_tasks = []
    done_tasks = []

    user_id = query.from_user.id
    user_name = EXECUTORS.get(user_id)

    for r in rows:

        if user_id != ADMIN_ID:
            if r["Executor"] != user_name:
                continue

        task = (
            f"🆔 <code>#{r['TaskID']}</code>\n"
            f"📄 <b>{r['Task']}</b>\n"
            f"👤 {r['Executor']}\n"
            f"⏰ {r['Deadline']}\n"
        )

        if r["Status"] == "bajarildi":
            done_tasks.append(task)
        else:
            new_tasks.append(task)

    text = "🚨 <b>AKTIV TASKLAR</b>\n\n"

    for t in new_tasks:
        text += t + "\n"

    text += "\n✅ <b>BAJARILGAN TASKLAR</b>\n\n"

    for t in done_tasks:
        text += t + "\n"

    await query.edit_message_text(text[:4000], parse_mode="HTML")


# -------------------- TASK TYPES --------------------

async def text_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_text"] = update.message.text
    context.user_data["type"] = "text"

    await deadline_keyboard(update, context)


async def voice_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_voice"] = update.message.voice.file_id
    context.user_data["type"] = "voice"

    await deadline_keyboard(update, context)


async def video_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_video"] = update.message.video.file_id
    context.user_data["type"] = "video"

    await deadline_keyboard(update, context)


async def photo_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_photo"] = update.message.photo[-1].file_id
    context.user_data["type"] = "photo"

    await deadline_keyboard(update, context)


async def file_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_file"] = update.message.document.file_id
    context.user_data["type"] = "file"

    await deadline_keyboard(update, context)


async def videonote_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    context.user_data.clear()
    context.user_data["task_videonote"] = update.message.video_note.file_id
    context.user_data["type"] = "videonote"

    await deadline_keyboard(update, context)


# -------------------- TOGGLE USER --------------------

async def toggle_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("|")[1])

    selected = context.user_data.get("selected_users", [])

    if user_id in selected:
        selected.remove(user_id)
    else:
        selected.append(user_id)

    context.user_data["selected_users"] = selected

    keyboard = []

    for uid, name in EXECUTORS.items():
        mark = "✅" if uid in selected else "⬜"
        keyboard.append([
            InlineKeyboardButton(f"{mark} {name}", callback_data=f"toggle|{uid}")
        ])

    keyboard.append([
        InlineKeyboardButton("🚀 Yuborish", callback_data="send_multi")
    ])

    await query.edit_message_reply_markup(
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# -------------------- SEND MULTI --------------------

async def send_multi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    selected = context.user_data.get("selected_users", [])

    if not selected:
        await query.answer("❌ Hech kim tanlanmagan", show_alert=True)
        return

    deadline = context.user_data.get("deadline")
    if not deadline:
        await query.answer("❌ Deadline tanlanmagan", show_alert=True)
        return

    deadline_str = deadline.strftime("%Y-%m-%d %H:%M")

    task_type = context.user_data.get("type")
    task_id = get_next_task_id()

    keyboard = [
        [InlineKeyboardButton("✅ Bajarildi", callback_data=f"done|{task_id}")]
    ]

    for user_id in selected:
        name = EXECUTORS[user_id]

        try:
            if task_type == "text":
                text = context.user_data["task_text"]

                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        f"📌 <b>YANGI TASK</b>\n\n"
                        f"🆔 <code>#{task_id}</code>\n"
                        f"📄 {text}\n\n"
                        f"⏰ {deadline_str}"
                    ),
                    reply_markup=InlineKeyboardMarkup(keyboard),
                    parse_mode="HTML"
                )
                save_task(task_id, text, name, deadline)

            elif task_type == "voice":
                await context.bot.send_voice(
                    chat_id=user_id,
                    voice=context.user_data["task_voice"],
                    caption=f"🆔 #{task_id}\n⏰ {deadline_str}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                save_task(task_id, "Voice task", name, deadline)

            elif task_type == "video":
                await context.bot.send_video(
                    chat_id=user_id,
                    video=context.user_data["task_video"],
                    caption=f"🆔 #{task_id}\n⏰ {deadline_str}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                save_task(task_id, "Video task", name, deadline)

            elif task_type == "photo":
                await context.bot.send_photo(
                    chat_id=user_id,
                    photo=context.user_data["task_photo"],
                    caption=f"🆔 #{task_id}\n⏰ {deadline_str}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                save_task(task_id, "Photo task", name, deadline)

            elif task_type == "file":
                await context.bot.send_document(
                    chat_id=user_id,
                    document=context.user_data["task_file"],
                    caption=f"🆔 #{task_id}\n⏰ {deadline_str}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                save_task(task_id, "File task", name, deadline)

            elif task_type == "videonote":
                await context.bot.send_video_note(
                    chat_id=user_id,
                    video_note=context.user_data["task_videonote"]
                )
                await context.bot.send_message(
                    chat_id=user_id,
                    text=f"🆔 #{task_id}\n⏰ {deadline_str}",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                save_task(task_id, "Video note task", name, deadline)

        except Exception as e:
            print("Yuborishda xato:", e)

    await query.edit_message_text("✅ Task yuborildi")


# -------------------- DONE --------------------

async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    task_id = query.data.split("|")[-1]

    context.user_data["waiting_result"] = True
    context.user_data["task_id"] = task_id

    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text("📎 Natijani yuboring")


# -------------------- RESULT --------------------

async def handle_result(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message:
        return

    if not context.user_data.get("waiting_result"):
        return

    task_id = context.user_data.get("task_id")
    user = update.effective_user
    username = EXECUTORS.get(user.id, user.first_name)

    try:
        update_status(task_id)
    except:
        pass

    try:
        task_text = get_task_text(task_id)
    except:
        task_text = "Task"

    caption = (
        f"✅ <b>Bajarildi</b>\n\n"
        f"🆔 #{task_id}\n"
        f"👤 {username}\n"
        f"📄 {task_text}"
    )

    if message.document:
        await context.bot.send_document(ADMIN_ID, message.document.file_id, caption=caption, parse_mode="HTML")

    elif message.photo:
        await context.bot.send_photo(ADMIN_ID, message.photo[-1].file_id, caption=caption, parse_mode="HTML")

    elif message.video:
        await context.bot.send_video(ADMIN_ID, message.video.file_id, caption=caption, parse_mode="HTML")

    elif message.voice:
        await context.bot.send_voice(ADMIN_ID, message.voice.file_id, caption=caption, parse_mode="HTML")

    elif message.video_note:
        await context.bot.send_video_note(ADMIN_ID, message.video_note.file_id)
        await context.bot.send_message(ADMIN_ID, caption, parse_mode="HTML")

    elif message.text:
        await context.bot.send_message(ADMIN_ID, caption + f"\n\n💬 {message.text}", parse_mode="HTML")

    await message.reply_text("✅ Yuborildi")

    context.user_data.clear()


# -------------------- MAIN --------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    app.add_handler(MessageHandler(
        filters.ALL & (~filters.User(user_id=ADMIN_ID)),
        handle_result
    ), group=0)

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(user_id=ADMIN_ID),
        text_task
    ))

    app.add_handler(MessageHandler(
        filters.VOICE & filters.User(user_id=ADMIN_ID),
        voice_task
    ))

    app.add_handler(MessageHandler(
        filters.VIDEO & filters.User(user_id=ADMIN_ID),
        video_task
    ))

    app.add_handler(MessageHandler(
        filters.PHOTO & filters.User(user_id=ADMIN_ID),
        photo_task
    ))

    app.add_handler(MessageHandler(
        filters.Document.ALL & filters.User(user_id=ADMIN_ID),
        file_task
    ))

    app.add_handler(MessageHandler(
        filters.VIDEO_NOTE & filters.User(user_id=ADMIN_ID),
        videonote_task
    ))

    app.add_handler(CallbackQueryHandler(deadline_select, pattern="deadline"))
    app.add_handler(CallbackQueryHandler(toggle_user, pattern="toggle"))
    app.add_handler(CallbackQueryHandler(send_multi, pattern="send_multi"))
    app.add_handler(CallbackQueryHandler(done, pattern="done"))
    app.add_handler(CallbackQueryHandler(stats, pattern="stats"))
    app.add_handler(CallbackQueryHandler(all_tasks, pattern="tasks"))

    print("BOT ISHLADI 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()
