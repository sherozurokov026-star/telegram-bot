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
    sheet.append_row([
        task_id,
        datetime.now().strftime("%Y-%m-%d %H:%M"),
        task,
        executor,
        deadline.strftime("%Y-%m-%d %H:%M"),
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


# -------------------- DEADLINE CHECK --------------------

async def check_deadlines(context: ContextTypes.DEFAULT_TYPE):
    rows = sheet.get_all_records()
    now = datetime.now()

    for r in rows:
        status = r["Status"]
        task = r["Task"]
        executor = r.get("Executor")
        deadline = datetime.strptime(r["Deadline"], "%Y-%m-%d %H:%M")

        if status == "bajarildi":
            continue

        executor_id = None

        for uid, name in EXECUTORS.items():
            if name == executor:
                executor_id = uid

        if executor_id is None:
            continue

        seconds = (deadline - now).total_seconds()

        if 0 < seconds <= 600:
            await context.bot.send_message(
                executor_id,
                f"⚠️ <b>Ogohlantirish</b>\n\n⏰ 10 minut qoldi!\n\n📄 {task}",
                parse_mode="HTML"
            )

        if seconds <= 0:
            await context.bot.send_message(
                executor_id,
                f"⛔ <b>Muddat tugadi!</b>\n\n📄 {task}",
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
            f"⛔ Muddati o'tgan: <b>{data['expired']}</b>\n\n"
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
    context.user_data["task_text"] = update.message.text
    context.user_data["type"] = "text"
    await deadline_keyboard(update)


async def voice_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["task_voice"] = update.message.voice.file_id
    context.user_data["type"] = "voice"
    await deadline_keyboard(update)


async def video_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["task_video"] = update.message.video.file_id
    context.user_data["type"] = "video"
    await deadline_keyboard(update)


async def photo_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["task_photo"] = update.message.photo[-1].file_id
    context.user_data["type"] = "photo"
    await deadline_keyboard(update)


async def file_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["task_file"] = update.message.document.file_id
    context.user_data["type"] = "file"
    await deadline_keyboard(update)


async def videonote_task(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    context.user_data["task_videonote"] = update.message.video_note.file_id
    context.user_data["type"] = "videonote"
    await deadline_keyboard(update)


# -------------------- DEADLINE --------------------

async def deadline_keyboard(update):
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

    await update.message.reply_text(
        "⏰ <b>Muddatni tanlang</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def deadline_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    hours = int(query.data.split("|")[1])
    deadline = datetime.now() + timedelta(hours=hours)

    context.user_data["deadline"] = deadline

    keyboard = []
    for uid, name in EXECUTORS.items():
        keyboard.append([InlineKeyboardButton(name, callback_data=f"assign|{uid}")])

    await query.edit_message_text(
        "👤 <b>Ijrochini tanlang</b>",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


# -------------------- ASSIGN --------------------

async def assign(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query
    await query.answer()

    user_id = int(query.data.split("|")[1])
    deadline = context.user_data["deadline"]
    task_type = context.user_data["type"]

    task_id = get_next_task_id()

    keyboard = [
        [InlineKeyboardButton("✅ Bajarildi", callback_data=f"done|{task_id}")]
    ]

    if task_type == "text":

        text = context.user_data["task_text"]

        await context.bot.send_message(
            user_id,
            f"📌 <b>YANGI TASK</b>\n\n"
            f"🆔 <code>#{task_id}</code>\n"
            f"📄 {text}\n\n"
            f"⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML"
        )

        save_task(task_id, text, EXECUTORS[user_id], deadline)

    elif task_type == "voice":

        await context.bot.send_voice(
            user_id,
            context.user_data["task_voice"],
            caption=f"🆔 #{task_id}\n⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        save_task(task_id, "Voice task", EXECUTORS[user_id], deadline)

    elif task_type == "video":

        await context.bot.send_video(
            user_id,
            context.user_data["task_video"],
            caption=f"🆔 #{task_id}\n⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        save_task(task_id, "Video task", EXECUTORS[user_id], deadline)

    elif task_type == "photo":

        await context.bot.send_photo(
            user_id,
            context.user_data["task_photo"],
            caption=f"🆔 #{task_id}\n⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        save_task(task_id, "Photo task", EXECUTORS[user_id], deadline)

    elif task_type == "file":

        await context.bot.send_document(
            user_id,
            context.user_data["task_file"],
            caption=f"🆔 #{task_id}\n⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        save_task(task_id, "File task", EXECUTORS[user_id], deadline)

    elif task_type == "videonote":

        await context.bot.send_video_note(
            user_id,
            context.user_data["task_videonote"]
        )

        await context.bot.send_message(
            user_id,
            f"🆔 #{task_id}\n⏰ {deadline}",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        save_task(task_id, "Video note task", EXECUTORS[user_id], deadline)

    await query.edit_message_text("✅ Task yuborildi")


async def done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data

    # 🔥 UNIVERSAL PARSE
    if "|" in data:
        task_id = data.split("|")[-1]
    elif "_" in data:
        task_id = data.split("_")[-1]
    else:
        task_id = data

    # 🔥 STATE
    context.user_data["waiting_result"] = True
    context.user_data["task_id"] = task_id

    # 🔥 TUGMANI O‘CHIRISH
    await query.edit_message_reply_markup(reply_markup=None)

    await query.message.reply_text("📎 Natija faylni yuboring (photo/video/file/voice/text)")

# -------------------- RESULT --------------------

async def handle_result(update: Update, context: ContextTypes.DEFAULT_TYPE):

    # ❗ faqat result rejimida ishlaydi
    if not context.user_data.get("waiting_result"):
        return

    task_id = context.user_data.get("task_id")
    user = update.effective_user

    # 🔥 STATUS UPDATE
    if task_id:
        try:
            update_status(task_id)
        except Exception as e:
            print("Status xato:", e)

    # 🔥 TASK TEXT
    try:
        task_text = get_task_text(task_id)
    except:
        task_text = "Task"

    caption = (
        f"✅ <b>Task bajarildi</b>\n\n"
        f"🆔 #{task_id}\n"
        f"👤 {EXECUTORS.get(user.id, user.first_name)}\n"
        f"📄 {task_text}"
    )

    # ===============================
    # 🔥 HAMMA TURDAGI NATIJA
    # ===============================

    if update.message.document:
        await context.bot.send_document(
            ADMIN_ID,
            update.message.document.file_id,
            caption=caption,
            parse_mode="HTML"
        )

    elif update.message.photo:
        await context.bot.send_photo(
            ADMIN_ID,
            update.message.photo[-1].file_id,
            caption=caption,
            parse_mode="HTML"
        )

    elif update.message.video:
        await context.bot.send_video(
            ADMIN_ID,
            update.message.video.file_id,
            caption=caption,
            parse_mode="HTML"
        )

    elif update.message.video_note:
        await context.bot.send_video_note(
            ADMIN_ID,
            update.message.video_note.file_id
        )
        await context.bot.send_message(
            ADMIN_ID,
            caption,
            parse_mode="HTML"
        )

    elif update.message.voice:
        await context.bot.send_voice(
            ADMIN_ID,
            update.message.voice.file_id,
            caption=caption,
            parse_mode="HTML"
        )

    elif update.message.text:
        await context.bot.send_message(
            ADMIN_ID,
            caption + f"\n\n💬 {update.message.text}",
            parse_mode="HTML"
        )

    else:
        await context.bot.send_message(
            ADMIN_ID,
            caption,
            parse_mode="HTML"
        )

    # 🔥 USERGA JAVOB
    await update.message.reply_text("✅ Natija yuborildi!")

    # 🔥 STATE TOZALASH
    context.user_data.pop("waiting_result", None)
    context.user_data.pop("task_id", None)


# -------------------- MAIN --------------------

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))

    # 🔥 ENG MUHIM FIX (HAMMA NARSANI USHLAYDI)
    app.add_handler(MessageHandler(
        filters.ALL & (~filters.User(user_id=ADMIN_ID)),
        handle_result
    ), group=0)

    # 🔥 faqat ADMIN task beradi
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
    app.add_handler(CallbackQueryHandler(assign, pattern="assign"))
    app.add_handler(CallbackQueryHandler(done, pattern="done"))
    app.add_handler(CallbackQueryHandler(stats, pattern="stats"))
    app.add_handler(CallbackQueryHandler(all_tasks, pattern="tasks"))

    app.job_queue.run_repeating(check_deadlines, interval=60)

    print("BOT ISHLADI 🚀")
    app.run_polling()


if __name__ == "__main__":
    main()