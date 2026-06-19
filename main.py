# Задеплой этот файл на Railway вместо main.py (временно)
# Переименуй в main.py, задеплой, введи код через веб-страницу
# После получения SESSION_STRING - задеплой обратно основной main.py

import asyncio
import os
from aiohttp import web
from telethon import TelegramClient
from telethon.sessions import StringSession

API_ID = int(os.environ.get("API_ID", 38810606))
API_HASH = os.environ.get("API_HASH", "ad5c6998fe3df082dfdf66f836d11b24")
PHONE_NUMBER = os.environ.get("PHONE_NUMBER", "+16722019447")
PORT = int(os.environ.get("PORT", 8080))

client = TelegramClient(StringSession(), API_ID, API_HASH)
code_future = None

async def index(request):
    return web.Response(text="""
<html><body>
<h2>Telegram Auth</h2>
<form method="POST" action="/code">
    <input name="code" placeholder="Введи код из Telegram" style="font-size:20px;padding:10px" />
    <button type="submit" style="font-size:20px;padding:10px">Отправить</button>
</form>
</body></html>
""", content_type="text/html")

async def submit_code(request):
    global code_future
    data = await request.post()
    code = data.get("code", "").strip()
    if code_future and not code_future.done():
        code_future.set_result(code)
        return web.Response(text="<html><body><h2>Код принят! Жди SESSION_STRING в логах Railway.</h2></body></html>", content_type="text/html")
    return web.Response(text="Ошибка — код уже был введён или сессия не ожидает кода.")

async def main():
    global code_future
    await client.connect()

    async def code_callback():
        global code_future
        loop = asyncio.get_event_loop()
        code_future = loop.create_future()
        print("⏳ Жду код на веб-странице...")
        return await code_future

    await client.sign_in(PHONE_NUMBER, code_callback=code_callback)

    session_string = client.session.save()
    print("\n✅ SESSION_STRING (скопируй в переменные Railway):")
    print(session_string)
    print("\nТеперь задеплой обратно основной main.py и добавь SESSION_STRING в Variables.")

app = web.Application()
app.router.add_get("/", index)
app.router.add_post("/code", submit_code)

runner = web.AppRunner(app)

async def start():
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Сервер запущен на порту {PORT}")
    await main()

asyncio.run(start())
