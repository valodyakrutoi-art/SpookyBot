import asyncio
import re
import traceback
from telegram import Update
from telegram.ext import Application, CommandHandler
from telethon import TelegramClient

# ==================== КОНФИГУРАЦИЯ ====================
API_ID = 38810606
API_HASH = "ad5c6998fe3df082dfdf66f836d11b24"
PHONE_NUMBER = "+16722019447"
BOT_TOKEN = "8690367451:AAEmqLL8CDoDiOsshEi57xKlMfCpzO_BgTI"
SPOOKY_BOT = "@SpookyTimeBot"
REQUEST_DELAY = 2
UPDATE_INTERVAL = 30
# ====================================================

events_data = {"1.16.5": [], "1.21": []}

def get_version(num):
    return "1.16.5" if len(str(num)) == 3 else "1.21"

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
        name = name_match.group(1).strip()
        loot = None
        status = None
        time_str = None
        location = None
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
            "name": name,
            "loot_level": loot,
            "status": status,
            "time_str": time_str,
            "location": location,
            "raw_first_line": first
        })
    return events

async def send_events(update, version):
    evs = events_data.get(version, [])
    if not evs:
        await update.message.reply_text(f"📭 Нет активных ивентов на {version}")
        return
    out = f"🎯 Ивенты на {version}:\n\n"
    for e in evs:
        out += f"Анархия {e['anarchy_num']}:\n"
        out += f"{e['raw_first_line']}\n"
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
    if len(out) > 4000:
        for i in range(0, len(out), 4000):
            await update.message.reply_text(out[i:i + 4000])
    else:
        await update.message.reply_text(out)

async def events1(update: Update, context):
    await send_events(update, "1.16.5")

async def events2(update: Update, context):
    await send_events(update, "1.21")

async def main():
    # Инициализация клиента Telethon (без прокси)
    user_client = TelegramClient("session", API_ID, API_HASH)
    
    try:
        await user_client.start(phone=PHONE_NUMBER)
        print("✅ Userbot (Telethon) успешно авторизован")
    except Exception as e:
        print(f"❌ Ошибка авторизации: {e}")
        return
    
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
                            version = get_version(event["anarchy_num"])
                            events_data[version].append(event)
                        # Сортировка по номеру анархии (вместо приоритетов)
                        events_data["1.16.5"].sort(key=lambda x: x["anarchy_num"])
                        events_data["1.21"].sort(key=lambda x: x["anarchy_num"])
                        print(f"🔄 Обновлено: 1.16.5 — {len(events_data['1.16.5'])}, 1.21 — {len(events_data['1.21'])}")
            except Exception as e:
                print(f"❌ Ошибка опроса: {e}")
                traceback.print_exc()
            await asyncio.sleep(UPDATE_INTERVAL)
    
    asyncio.create_task(update_loop())
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("events1", events1))
    app.add_handler(CommandHandler("events2", events2))
    
    print("🤖 Telegram-бот запущен")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    asyncio.run(main())