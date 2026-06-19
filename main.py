import asyncio
import re
import json
import os
import traceback
from aiohttp import web
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)
from telethon import TelegramClient
from telethon.sessions import StringSession

# ==================== КОНФИГУРАЦИЯ ====================
API_ID = int(os.environ.get("API_ID", 38810606))
API_HASH = os.environ.get("API_HASH", "ad5c6998fe3df082dfdf66f836d11b24")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "+16722019447")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8690367451:AAF1dc_lnPE1z0J7AeVDUV2kcU6SUXk1Q8U")
PORT = int(os.environ.get("PORT", 8080))
SPOOKY_BOT = "@SpookyTimeBot"
REQUEST_DELAY = 2
UPDATE_INTERVAL = 30
USER_COMMANDS_FILE = "user_commands.json"
MAX_CUSTOM_COMMANDS = 5
# ====================================================

CHOOSE_VERSION, CHOOSE_TYPE = range(2)

ANARCHY_TYPES = {
    "Соло": 1, "Дуо": 2, "Трио": 3,
    "Квадро": 4, "Пента": 5, "Клан": 6,
}

events_data = {"1.16.5": [], "1.21": []}

# ==================== ХРАНИЛИЩЕ КОМАНД ====================

def load_user_commands() -> dict:
    if os.path.exists(USER_COMMANDS_FILE):
        try:
            with open(USER_COMMANDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_user_commands(data: dict):
    with open(USER_COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_cmds(user_id: int) -> list:
    return load_user_commands().get(str(user_id), [])

def add_user_cmd(user_id: int, version: str, anarchy_type: str) -> bool:
    data = load_user_commands()
    key = str(user_id)
    cmds = data.get(key, [])
    if len(cmds) >= MAX_CUSTOM_COMMANDS:
        return False
    entry = {"version": version, "type": anarchy_type}
    if entry in cmds:
        return False
    cmds.append(entry)
    data[key] = cmds
    save_user_commands(data)
    return True

# ==================== КЛАВИАТУРА ====================

def cmd_label(cmd: dict) -> str:
    return f"🔍 {cmd['type']} {cmd['version']}"

def build_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    cmds = get_user_cmds(user_id)
    rows = [
        [KeyboardButton("/events1"), KeyboardButton("/events2")],
        [KeyboardButton("/help"), KeyboardButton("➕ Добавить команду")],
    ]
    custom_buttons = [KeyboardButton(cmd_label(c)) for c in cmds]
    for i in range(0, len(custom_buttons), 2):
        rows.append(custom_buttons[i:i+2])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ==================== ПАРСИНГ ИВЕНТОВ ====================

def get_version(num):
    return "1.16.5" if len(str(num)) == 3 else "1.21"

def filter_events(version: str, type_num: int) -> list:
    evs = events_data.get(version, [])
    if version == "1.16.5":
        return [e for e in evs if (e["anarchy_num"] // 100) == type_num]
    else:
        return [e for e in evs if (e["anarchy_num"] // 1000) == type_num]

def parse_events(text):
    events = []
    pattern = r'Анархия (\d+):\s*(.*?)(?=Анархия \d+:|$)'
    for num_str, content in re.findall(pattern, text, re.DOTALL):
        if "До следующего ивента:" in content:
            continue
        num = int(num_str)
        lines = content.strip().split("\n")
        if not lines:
            continue
        first = lines[0].strip()
        name_match = re.search(r"\]\s*(.+?)$", first)
        if not name_match:
            continue
        loot = status = time_str = location = None
        for line in lines[1:]:
            line = line.strip()
            if "Уровень лута:" in line:
                loot = line.split(":", 1)[1].strip()
            elif "Статус:" in line:
                parts = line.split(":", 1)[1].strip().split(",", 1)
                status = parts[0].strip()
                if len(parts) > 1:
                    time_str = parts[1].strip()
            elif "Координаты:" in line or "Локация:" in line:
                location = line
        events.append({
            "anarchy_num": num,
            "name": name_match.group(1).strip(),
            "loot_level": loot,
            "status": status,
            "time_str": time_str,
            "location": location,
            "raw_first_line": first
        })
    return events

def format_events(evs: list, version: str, type_name: str = None) -> str:
    label = f"{type_name} {version}" if type_name else version
    if not evs:
        return f"📭 Нет активных ивентов: {label}"
    out = f"🎯 Ивенты — {label}:\n\n"
    for e in evs:
        out += f"Анархия {e['anarchy_num']}:\n{e['raw_first_line']}\n"
        if e["loot_level"]:
            out += f"Уровень лута: {e['loot_level']}\n"
        if e["status"]:
            out += f"Статус: {e['status']}"
            if e["time_str"]:
                out += f", {e['time_str']}"
            out += "\n"
        if e["location"]:
            out += e["location"] + "\n"
        out += "\n"
    return out

async def send_long(update: Update, text: str, keyboard=None):
    kwargs = {"reply_markup": keyboard} if keyboard else {}
    if len(text) > 4000:
        for i in range(0, len(text), 4000):
            await update.message.reply_text(text[i:i+4000], **kwargs)
    else:
        await update.message.reply_text(text, **kwargs)

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = build_main_keyboard(update.effective_user.id)
    await update.message.reply_text(
        "👻 Привет! Я SpookyEvents — бот для отслеживания ивентов на анархиях.\n\n"
        "Используй кнопки ниже для навигации.",
        reply_markup=kb
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cmds = get_user_cmds(user_id)
    kb = build_main_keyboard(user_id)
    text = (
        "👻 *SpookyEvents Bot*\n\n"
        "Я слежу за ивентами на серверах SpookyTime и показываю активные события.\n\n"
        "*Основные команды:*\n"
        "• /events1 — ивенты на версии 1.16.5\n"
        "• /events2 — ивенты на версии 1.21\n"
        "• /help — эта справка\n"
        "• ➕ Добавить команду — создать быструю команду для нужного типа анархии\n\n"
        "*Типы анархий:*\n"
        "• Соло (100x / 1000x)\n"
        "• Дуо (200x / 2000x)\n"
        "• Трио (300x / 3000x)\n"
        "• Квадро (400x / 4000x)\n"
        "• Пента (500x / 5000x)\n"
        "• Клан (600x / 6000x)\n\n"
    )
    if cmds:
        text += f"*Твои быстрые команды ({len(cmds)}/{MAX_CUSTOM_COMMANDS}):*\n"
        for c in cmds:
            text += f"• {cmd_label(c)}\n"
    else:
        text += f"У тебя пока нет быстрых команд (макс. {MAX_CUSTOM_COMMANDS}).\nНажми ➕ Добавить команду."
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=kb)

async def events1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = build_main_keyboard(update.effective_user.id)
    await send_long(update, format_events(events_data.get("1.16.5", []), "1.16.5"), kb)

async def events2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    kb = build_main_keyboard(update.effective_user.id)
    await send_long(update, format_events(events_data.get("1.21", []), "1.21"), kb)

# ==================== ДОБАВЛЕНИЕ КОМАНДЫ ====================

async def add_cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cmds = get_user_cmds(user_id)
    if len(cmds) >= MAX_CUSTOM_COMMANDS:
        await update.message.reply_text(
            f"❌ У тебя уже {MAX_CUSTOM_COMMANDS} быстрых команд — это максимум.",
            reply_markup=build_main_keyboard(user_id)
        )
        return ConversationHandler.END
    version_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("1.16"), KeyboardButton("1.21")], [KeyboardButton("❌ Отмена")]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        f"➕ *Добавление быстрой команды* ({len(cmds)}/{MAX_CUSTOM_COMMANDS})\n\nВыбери версию сервера:",
        parse_mode="Markdown", reply_markup=version_kb
    )
    return CHOOSE_VERSION

async def add_cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await cancel(update, context)
    if text == "1.16":
        context.user_data["add_version"] = "1.16.5"
    elif text == "1.21":
        context.user_data["add_version"] = "1.21"
    else:
        await update.message.reply_text("Пожалуйста, выбери версию кнопкой.")
        return CHOOSE_VERSION
    type_kb = ReplyKeyboardMarkup(
        [
            [KeyboardButton("Соло"), KeyboardButton("Дуо"), KeyboardButton("Трио")],
            [KeyboardButton("Квадро"), KeyboardButton("Пента"), KeyboardButton("Клан")],
            [KeyboardButton("❌ Отмена")]
        ],
        resize_keyboard=True
    )
    await update.message.reply_text(
        f"✅ Версия: *{context.user_data['add_version']}*\n\nТеперь выбери тип анархии:",
        parse_mode="Markdown", reply_markup=type_kb
    )
    return CHOOSE_TYPE

async def add_cmd_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    if text == "❌ Отмена":
        return await cancel(update, context)
    if text not in ANARCHY_TYPES:
        await update.message.reply_text("Пожалуйста, выбери тип анархии кнопкой.")
        return CHOOSE_TYPE
    version = context.user_data.get("add_version")
    user_id = update.effective_user.id
    success = add_user_cmd(user_id, version, text)
    kb = build_main_keyboard(user_id)
    if success:
        await update.message.reply_text(
            f"✅ Команда *{text} {version}* добавлена!\nТеперь кнопка «🔍 {text} {version}» появилась в меню.",
            parse_mode="Markdown", reply_markup=kb
        )
    else:
        cmds = get_user_cmds(user_id)
        if len(cmds) >= MAX_CUSTOM_COMMANDS:
            await update.message.reply_text(f"❌ Достигнут лимит команд ({MAX_CUSTOM_COMMANDS}).", reply_markup=kb)
        else:
            await update.message.reply_text(f"ℹ️ Команда *{text} {version}* уже есть у тебя.", parse_mode="Markdown", reply_markup=kb)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Отменено.", reply_markup=build_main_keyboard(update.effective_user.id))
    return ConversationHandler.END

async def handle_custom_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    if text == "➕ Добавить команду":
        return await add_cmd_start(update, context)
    match = re.match(r"🔍 (\S+) (1\.16\.5|1\.21)$", text)
    if not match:
        return
    type_name, version = match.group(1), match.group(2)
    cmds = get_user_cmds(user_id)
    if not any(c["version"] == version and c["type"] == type_name for c in cmds):
        await update.message.reply_text("⚠️ Такой команды у тебя нет.")
        return
    type_num = ANARCHY_TYPES.get(type_name)
    if type_num is None:
        await update.message.reply_text("⚠️ Неизвестный тип анархии.")
        return
    await send_long(update, format_events(filter_events(version, type_num), version, type_name), build_main_keyboard(user_id))

# ==================== ВЕБ-АВТОРИЗАЦИЯ ====================

code_future = None
phone_code_hash = None

async def web_index(request):
    return web.Response(content_type="text/html", text="""
<html><head><meta charset="utf-8">
<style>body{font-family:sans-serif;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;margin:0;background:#1a1a2e}
h2{color:#e0e0e0}input{font-size:24px;padding:12px;width:220px;border-radius:8px;border:none;margin-right:8px}
button{font-size:24px;padding:12px 24px;border-radius:8px;border:none;background:#7289da;color:white;cursor:pointer}</style>
</head><body>
<h2>👻 SpookyEvents — Введи код из Telegram</h2>
<form method="POST" action="/code">
    <input name="code" placeholder="12345" autofocus/>
    <button type="submit">Войти</button>
</form>
</body></html>
""")

async def web_submit_code(request):
    global code_future
    data = await request.post()
    code = data.get("code", "").strip()
    if code_future and not code_future.done():
        code_future.set_result(code)
        return web.Response(content_type="text/html", text="""
<html><head><meta charset="utf-8">
<style>body{font-family:sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;background:#1a1a2e}
h2{color:#43b581}</style></head><body>
<h2>✅ Код принят! Бот запускается...</h2>
</body></html>
""")
    return web.Response(text="Ошибка: код уже был введён.")

async def run_web_server():
    app = web.Application()
    app.router.add_get("/", web_index)
    app.router.add_post("/code", web_submit_code)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Веб-сервер запущен на порту {PORT} — открой домен Railway и введи код")

# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

async def main():
    global code_future, phone_code_hash

    # Запускаем веб-сервер сразу
    await run_web_server()

    # Подключаемся и запрашиваем код
    user_client = TelegramClient(StringSession(), API_ID, API_HASH)
    await user_client.connect()

    print(f"📱 Отправляю код на {PHONE_NUMBER}...")
    result = await user_client.send_code_request(PHONE_NUMBER)
    phone_code_hash = result.phone_code_hash
    print("📱 Код отправлен — жду ввода на веб-странице...")

    loop = asyncio.get_event_loop()
    code_future = loop.create_future()
    code = await code_future

    try:
        await user_client.sign_in(PHONE_NUMBER, code, phone_code_hash=phone_code_hash)
        print("✅ Userbot (Telethon) успешно авторизован")
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return

    # Запускаем опрос SpookyBot
    async def update_loop():
        while True:
            try:
                await user_client.send_message(SPOOKY_BOT, "/events")
                await asyncio.sleep(REQUEST_DELAY)
                messages = await user_client.get_messages(SPOOKY_BOT, limit=1)
                if messages:
                    msg = messages[0]
                    if msg.text and ("Анархия" in msg.text or "До следующего" in msg.text):
                        parsed = parse_events(msg.text)
                        events_data["1.16.5"].clear()
                        events_data["1.21"].clear()
                        for event in parsed:
                            v = get_version(event["anarchy_num"])
                            events_data[v].append(event)
                        events_data["1.16.5"].sort(key=lambda x: x["anarchy_num"])
                        events_data["1.21"].sort(key=lambda x: x["anarchy_num"])
                        print(f"🔄 Обновлено: 1.16.5 — {len(events_data['1.16.5'])}, 1.21 — {len(events_data['1.21'])}")
            except Exception as e:
                print(f"❌ Ошибка опроса: {e}")
                traceback.print_exc()
            await asyncio.sleep(UPDATE_INTERVAL)

    asyncio.create_task(update_loop())

    # Запускаем telegram бота
    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_cmd))
    bot_app.add_handler(CommandHandler("events1", events1))
    bot_app.add_handler(CommandHandler("events2", events2))

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^➕ Добавить команду$"), add_cmd_start)],
        states={
            CHOOSE_VERSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cmd_version)],
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cmd_type)],
        },
        fallbacks=[
            MessageHandler(filters.Regex(r"^❌ Отмена$"), cancel),
            CommandHandler("start", start),
        ],
    )
    bot_app.add_handler(conv_handler)
    bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.Regex(r"^🔍 "),
        handle_custom_cmd
    ))

    print("🤖 Telegram-бот запущен")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())
