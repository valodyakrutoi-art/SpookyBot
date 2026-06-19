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
phone_code_hash = None
code_future = None

async def index(request):
    return web.Response(content_type="text/html", text="""
<html><head><meta charset="utf-8"></head><body>
<h2>Введи код из Telegram</h2>
<form method="POST" action="/code">
    <input name="code" placeholder="12345" style="font-size:24px;padding:10px;width:200px" autofocus/>
    <button type="submit" style="font-size:24px;padding:10px">Отправить</button>
</form>
</body></html>
""")

async def submit_code(request):
    global code_future
    data = await request.post()
    code = data.get("code", "").strip()
    if code_future and not code_future.done():
        code_future.set_result(code)
        return web.Response(content_type="text/html", text="""
<html><head><meta charset="utf-8"></head><body>
<h2>✅ Код принят! Смотри логи Railway — там появится SESSION_STRING.</h2>
</body></html>
""")
    return web.Response(text="Ошибка.")

async def auth_flow():
    global phone_code_hash, code_future
    await client.connect()
    result = await client.send_code_request(PHONE_NUMBER)
    phone_code_hash = result.phone_code_hash
    print(f"📱 Код отправлен на {PHONE_NUMBER} — жди ввода на веб-странице...")

    loop = asyncio.get_event_loop()
    code_future = loop.create_future()
    code = await code_future

    await client.sign_in(PHONE_NUMBER, code, phone_code_hash=phone_code_hash)
    session_string = client.session.save()
    print("\n✅ SESSION_STRING (скопируй в Variables Railway):")
    print(session_string)
    print("\nТеперь задеплой основной main.py и добавь SESSION_STRING в Variables.")

async def start():
    app = web.Application()
    app.router.add_get("/", index)
    app.router.add_post("/code", submit_code)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()
    print(f"🌐 Сервер запущен на порту {PORT}")

    await auth_flow()
    await asyncio.sleep(3600)

asyncio.run(start())
