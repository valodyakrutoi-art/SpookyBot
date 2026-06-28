import os
import re
import json
import time
import asyncio

import discord
from discord import app_commands

# ==================== КОНФИГ ====================
DISCORD_TOKEN = os.environ.get("DISCORD_TOKEN", "")
DATA_DIR = os.environ.get("DATA_DIR", ".")
EVENTS_CACHE_FILE = os.path.join(DATA_DIR, "events_cache.json")
DC_SETTINGS_FILE = os.path.join(DATA_DIR, "discord_settings.json")

VERSION_4DIGIT = "1.21"
VERSION_3DIGIT = "1.16.5"

DEFAULT_SETTINGS = {"sort": "anarchy", "status_filter": "both", "compact": False}

# ==================== НАСТРОЙКИ (на сервер/ЛС) ====================
def _scope_id(interaction: discord.Interaction) -> str:
    # на сервере — настройки общие для гильдии, в ЛС — на юзера
    if interaction.guild_id:
        return f"g{interaction.guild_id}"
    return f"u{interaction.user.id}"


def load_settings_all() -> dict:
    if os.path.exists(DC_SETTINGS_FILE):
        try:
            with open(DC_SETTINGS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_settings_all(data: dict):
    try:
        with open(DC_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)
    except Exception:
        pass


def get_settings(interaction) -> dict:
    data = load_settings_all()
    s = dict(DEFAULT_SETTINGS)
    s.update(data.get(_scope_id(interaction), {}))
    return s


def set_settings(interaction, **kwargs):
    data = load_settings_all()
    key = _scope_id(interaction)
    cur = dict(DEFAULT_SETTINGS)
    cur.update(data.get(key, {}))
    cur.update(kwargs)
    data[key] = cur
    save_settings_all(data)
    return cur

# ==================== ЧТЕНИЕ КЭША СОБЫТИЙ ====================
def read_events():
    if not os.path.exists(EVENTS_CACHE_FILE):
        return {VERSION_3DIGIT: [], VERSION_4DIGIT: []}, 0
    try:
        with open(EVENTS_CACHE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("events", {}), data.get("updated", 0)
    except Exception:
        return {VERSION_3DIGIT: [], VERSION_4DIGIT: []}, 0


def _format_duration(sec):
    sec = int(max(0, round(sec)))
    h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
    parts = []
    if h:
        parts.append(f"{h} ч")
    if m:
        parts.append(f"{m} мин")
    parts.append(f"{s} сек")
    return " ".join(parts)


def _live_timer(e):
    """Пересчёт таймера на лету (как в Telegram-боте)."""
    base = e.get("timer_sec")
    if base is not None and e.get("fetched_at"):
        remaining = base - (time.time() - e["fetched_at"])
        label = e.get("timer_label") or ""
        return (label + " " if label else "") + _format_duration(remaining)
    return e.get("time_str") or ""


def _live_next_in(e):
    base = e.get("next_in_sec")
    if base is not None and e.get("fetched_at"):
        return _format_duration(base - (time.time() - e["fetched_at"]))
    return str(e.get("next_in") or "?")

# ==================== ФОРМАТИРОВАНИЕ ====================
def apply_status_filter(evs, mode):
    if mode == "active":
        return [e for e in evs if not e.get("upcoming")]
    if mode == "upcoming":
        return [e for e in evs if e.get("upcoming")]
    return evs


def sort_events(evs, sort_mode):
    if sort_mode == "rarity":
        from_order = {"Легендарный": 0, "Элитный": 1, "Богатый": 2, "Солидный": 3, "Обычный": 4}
        return sorted(evs, key=lambda e: (1 if e.get("upcoming") else 0,
                                          from_order.get(e.get("rarity"), 9),
                                          e["anarchy_num"]))
    return sorted(evs, key=lambda e: (1 if e.get("upcoming") else 0, e["anarchy_num"]))


def format_one(e, compact=False):
    if e.get("upcoming"):
        return f"**Анархия {e['anarchy_num']}:** ⏳ ивент через {_live_next_in(e)}\n"
    out = f"**Анархия {e['anarchy_num']}:**\n{e.get('raw_first_line','')}\n"
    if not compact:
        if e.get("loot_level"):
            out += f"Уровень лута: {e['loot_level']}\n"
        if e.get("status"):
            out += f"Статус: {e['status']}"
            tm = _live_timer(e)
            if tm:
                out += f", {tm}"
            out += "\n"
    if e.get("location"):
        loc = re.sub(r"\s+", " ", str(e["location"])).strip()
        # обратные кавычки -> копируемый блок в Discord
        if ":" in loc:
            lab, val = loc.split(":", 1)
            out += f"{lab.strip()}: `{val.strip()}`\n"
        else:
            out += f"`{loc}`\n"
    return out + "\n"


def build_events_text(version, interaction):
    settings = get_settings(interaction)
    events, _ = read_events()
    evs = list(events.get(version, []))
    evs = apply_status_filter(evs, settings["status_filter"])
    evs = sort_events(evs, settings["sort"])
    if not evs:
        return f"📭 Нет событий для {version}."
    header = f"🎯 **События {version}**\n\n"
    body = "".join(format_one(e, settings.get("compact", False)) for e in evs)
    text = header + body
    return text[:1990] + ("…" if len(text) > 1990 else "")


def search_text(query, interaction):
    settings = get_settings(interaction)
    events, _ = read_events()
    ql = (query or "").strip().lower()
    if not ql:
        return "⚠️ Укажи название для поиска."
    out_lines = []
    for version in (VERSION_4DIGIT, VERSION_3DIGIT):
        for e in events.get(version, []):
            if ql in str(e.get("name", "")).lower():
                out_lines.append(f"[{version}] " + format_one(e, settings.get("compact", False)))
    if not out_lines:
        return f"🔍 По запросу «{query}» ничего не найдено."
    text = f"🔍 **Результаты по «{query}»**\n\n" + "".join(out_lines)
    return text[:1990] + ("…" if len(text) > 1990 else "")

# ==================== DISCORD БОТ ====================
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)


@client.event
async def on_ready():
    try:
        await tree.sync()
    except Exception as e:
        print(f"⚠️ sync: {e}")
    print(f"✅ Discord-бот запущен как {client.user}")


@tree.command(name="events1", description="События 1.16.5")
async def events1(interaction: discord.Interaction):
    await interaction.response.send_message(build_events_text(VERSION_3DIGIT, interaction))


@tree.command(name="events2", description="События 1.21")
async def events2(interaction: discord.Interaction):
    await interaction.response.send_message(build_events_text(VERSION_4DIGIT, interaction))


@tree.command(name="search", description="Поиск события по названию")
@app_commands.describe(query="Название события")
async def search(interaction: discord.Interaction, query: str):
    await interaction.response.send_message(search_text(query, interaction))


@tree.command(name="settings", description="Настройки отображения")
@app_commands.describe(
    sort="Сортировка: anarchy или rarity",
    status="Фильтр: active / upcoming / both",
    compact="Компактный режим: true/false",
)
@app_commands.choices(
    sort=[app_commands.Choice(name="По анархии", value="anarchy"),
          app_commands.Choice(name="По редкости", value="rarity")],
    status=[app_commands.Choice(name="Активные", value="active"),
            app_commands.Choice(name="Скорые", value="upcoming"),
            app_commands.Choice(name="Все", value="both")],
)
async def settings_cmd(interaction: discord.Interaction,
                       sort: app_commands.Choice[str] = None,
                       status: app_commands.Choice[str] = None,
                       compact: bool = None):
    changes = {}
    if sort is not None:
        changes["sort"] = sort.value
    if status is not None:
        changes["status_filter"] = status.value
    if compact is not None:
        changes["compact"] = compact
    if changes:
        cur = set_settings(interaction, **changes)
        scope = "сервера" if interaction.guild_id else "ваши"
        await interaction.response.send_message(
            f"✅ Настройки {scope} обновлены:\n"
            f"• Сортировка: {cur['sort']}\n"
            f"• Фильтр: {cur['status_filter']}\n"
            f"• Компактно: {cur['compact']}", ephemeral=True)
    else:
        cur = get_settings(interaction)
        await interaction.response.send_message(
            f"⚙️ Текущие настройки:\n"
            f"• Сортировка: {cur['sort']}\n"
            f"• Фильтр: {cur['status_filter']}\n"
            f"• Компактно: {cur['compact']}\n\n"
            f"Измени их параметрами команды /settings.", ephemeral=True)


@tree.command(name="help", description="Помощь по боту")
async def help_cmd(interaction: discord.Interaction):
    txt = (
        "🛡 **Spooky Events — Discord**\n\n"
        "Команды:\n"
        "• /events1 — события 1.16.5\n"
        "• /events2 — события 1.21\n"
        "• /search <название> — поиск события\n"
        "• /settings — настройки (сортировка, фильтр, компактный режим)\n"
        "• /help — эта справка\n\n"
        "Работает в личных сообщениях и на серверах. "
        "На сервере настройки общие для всех участников."
    )
    await interaction.response.send_message(txt, ephemeral=True)


def main():
    if not DISCORD_TOKEN:
        print("❌ DISCORD_TOKEN не задан. Добавь его в Railway → Variables.")
        return
    client.run(DISCORD_TOKEN)


if __name__ == "__main__":
    main()
