import asyncio
import re
import json
import os
import traceback
from aiohttp import web
from telegram import (
    Update, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
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
SUPPORT_USERNAME = "SchoolShooter2016"
# ====================================================

CHOOSE_VERSION, CHOOSE_TYPE, CHOOSE_EVENTS, CHOOSE_RARITY = range(4)

ANARCHY_TYPES = {
    "Соло": 1, "Дуо": 2, "Трио": 3,
    "Квадро": 4, "Пента": 5, "Клан": 6,
}
ANARCHY_TYPE_LIST = list(ANARCHY_TYPES.keys())

# трёхзначные (1xx-6xx) -> 1.21
# четырёхзначные (1xxx-6xxx) -> 1.16.5
VERSION_3DIGIT = "1.21"
VERSION_4DIGIT = "1.16.5"

EVENT_TYPES = [
    "Метеоритный дождь", "Мистический сундук", "Адская резня",
    "Бикини боттом", "Горящий череп", "Маяк убийца",
    "Сундуки смерти", "Вулкан", "Гейзер",
]
NO_RARITY_EVENTS = {"Адская резня", "Бикини боттом", "Горящий череп"}

RARITIES = ["Легендарный", "Элитный", "Богатый", "Солидный", "Обычный"]
RARITY_ORDER = {name: i for i, name in enumerate(RARITIES)}

LANGUAGES = ["RU", "EN", "KZ", "UA", "BY"]

events_data = {"1.16.5": [], "1.21": []}

# ==================== ПЕРЕВОДЫ ====================

TR = {
    "RU": {
        "welcome": (
            "👻 *SpookyEvents Bot*\n\n"
            "Я отслеживаю ивенты на анархиях SpookyTime и показываю активные события в реальном времени.\n\n"
            "*Версии серверов:*\n"
            "• /events1 — ивенты на анархиях *1.16.5* (четырёхзначные номера: 1xxx–6xxx)\n"
            "• /events2 — ивенты на анархиях *1.21* (трёхзначные номера: 1xx–6xx)\n\n"
            "*Команды:*\n"
            "• /events1 — все ивенты 1.16.5\n"
            "• /events2 — все ивенты 1.21\n"
            "• /help — справка и поддержка\n"
            "• ➕ Добавить команду — создай быструю кнопку с нужными фильтрами\n"
            "• 🗑 Удалить команду — удали ненужную быструю команду\n"
            "• ⚙️ Настройки — сортировка и язык\n\n"
            "Используй кнопки ниже 👇"
        ),
        "no_events": "📭 Нет активных ивентов: {label}",
        "events_header": "🎯 Ивенты — {label}:\n\n",
        "btn_add": "➕ Добавить команду",
        "btn_del": "🗑 Удалить команду",
        "btn_settings": "⚙️ Настройки",
        "btn_cancel": "❌ Отмена",
        "btn_skip": "Пропустить",
        "btn_done": "✅ Готово",
        "choose_version": "➕ *Добавление быстрой команды* ({n}/{max})\n\nВыбери версию сервера:",
        "choose_anarchy_type": "✅ Версия: *{version}*\n\nВыбери типы анархий (можно несколько) или «Пропустить» — все типы:",
        "choose_events": "✅ Тип: *{type} {version}*\n\nВыбери ивенты (можно несколько) или «Пропустить» — все ивенты:",
        "choose_rarity": "Теперь выбери редкость ивентов или «Пропустить» — все редкости:",
        "cmd_added": "✅ Команда добавлена!\nТеперь кнопка появилась в меню.",
        "cmd_limit": "❌ Достигнут лимит команд ({max}).",
        "cmd_exists": "ℹ️ Такая команда уже есть у тебя.",
        "cancelled": "❌ Отменено.",
        "no_cmds_to_del": "У тебя пока нет быстрых команд для удаления.",
        "choose_del": "🗑 Выбери команду для удаления:",
        "cmd_deleted": "✅ Команда удалена.",
        "settings_title": "⚙️ *Настройки*",
        "settings_sort": "Сортировка: {val}",
        "settings_lang": "Язык: {val}",
        "settings_hidden": "Скрытые ивенты: {val}",
        "hidden_none": "нет",
        "hidden_applied": "✅ Скрытые ивенты обновлены.",
        "sort_anarchy": "По анархиям",
        "sort_rarity": "По редкостям",
        "no_cmd": "⚠️ Такой команды у тебя нет.",
        "help_text": (
            "👻 *SpookyEvents Bot* — справка\n\n"
            "*Основные команды:*\n"
            "• /start — информация о боте\n"
            "• /events1 — все ивенты 1.16.5\n"
            "• /events2 — все ивенты 1.21\n"
            "• /help — эта справка\n\n"
            "*Быстрые команды:*\n"
            "Создай свою кнопку через «➕ Добавить команду» — выбери версию, типы анархий, ивенты и редкость. Макс. 5 команд.\n\n"
            "*Настройки:*\n"
            "⚙️ Сортировка — по номеру анархии или по редкости\n"
            "⚙️ Язык — RU / EN / KZ / UA / BY\n"
            "⚙️ Скрытые ивенты — выбери типы ивентов, которые не нужно показывать\n\n"
            "По вопросам и проблемам — кнопка ниже 👇"
        ),
        "support_btn": "💬 Написать создателю",
        "support_msg": "👇 Нажми кнопку чтобы написать создателю бота:",
    },
    "EN": {
        "welcome": (
            "👻 *SpookyEvents Bot*\n\n"
            "I track events on SpookyTime anarchies and show active events in real time.\n\n"
            "*Server versions:*\n"
            "• /events1 — events on *1.16.5* anarchies (4-digit: 1xxx–6xxx)\n"
            "• /events2 — events on *1.21* anarchies (3-digit: 1xx–6xx)\n\n"
            "*Anarchy types:*\n"
            "• Solo (100x / 1000x) • Duo (200x / 2000x) • Trio (300x / 3000x)\n"
            "• Quad (400x / 4000x) • Penta (500x / 5000x) • Clan (600x / 6000x)\n\n"
            "*Commands:*\n"
            "• /events1 — all 1.16.5 events\n"
            "• /events2 — all 1.21 events\n"
            "• /help — help & support\n"
            "• ➕ Add command — create a quick button with filters\n"
            "• 🗑 Delete command — remove a quick command\n"
            "• ⚙️ Settings — sorting and language\n\n"
            "Use the buttons below 👇"
        ),
        "no_events": "📭 No active events: {label}",
        "events_header": "🎯 Events — {label}:\n\n",
        "btn_add": "➕ Add command",
        "btn_del": "🗑 Delete command",
        "btn_settings": "⚙️ Settings",
        "btn_cancel": "❌ Cancel",
        "btn_skip": "Skip",
        "btn_done": "✅ Done",
        "choose_version": "➕ *Add quick command* ({n}/{max})\n\nChoose server version:",
        "choose_anarchy_type": "✅ Version: *{version}*\n\nChoose anarchy types (multiple allowed) or «Skip» — all types:",
        "choose_events": "✅ Type: *{type} {version}*\n\nChoose events (multiple allowed) or «Skip» — all events:",
        "choose_rarity": "Now choose event rarity or «Skip» — all rarities:",
        "cmd_added": "✅ Command added!\nA new button appeared in the menu.",
        "cmd_limit": "❌ Command limit reached ({max}).",
        "cmd_exists": "ℹ️ You already have this command.",
        "cancelled": "❌ Cancelled.",
        "no_cmds_to_del": "You don't have any quick commands to delete yet.",
        "choose_del": "🗑 Choose a command to delete:",
        "cmd_deleted": "✅ Command deleted.",
        "settings_title": "⚙️ *Settings*",
        "settings_sort": "Sort: {val}",
        "settings_lang": "Language: {val}",
        "settings_hidden": "🙈 Hidden events: {val}",
        "hidden_none": "none",
        "hidden_applied": "✅ Hidden events updated.",
        "sort_anarchy": "By anarchy",
        "sort_rarity": "By rarity",
        "no_cmd": "⚠️ You don't have this command.",
        "help_text": (
            "👻 *SpookyEvents Bot* — help\n\n"
            "*Main commands:*\n"
            "• /start — bot info\n"
            "• /events1 — all 1.16.5 events\n"
            "• /events2 — all 1.21 events\n"
            "• /help — this help\n\n"
            "*Quick commands:*\n"
            "Create your button via «➕ Add command» — choose version, anarchy types, events and rarity. Max 5 commands.\n\n"
            "*Settings:*\n"
            "⚙️ Sort — by anarchy number or by rarity\n"
            "⚙️ Language — RU / EN / KZ / UA / BY\n"
            "⚙️ Hidden events — pick event types you don't want to see\n\n"
            "For questions and issues — button below 👇"
        ),
        "support_btn": "💬 Contact creator",
        "support_msg": "👇 Press the button to contact the bot creator:",
    },
    "KZ": {
        "welcome": (
            "👻 *SpookyEvents Bot*\n\n"
            "Мен SpookyTime анархияларындағы ивенттерді бақылаймын.\n\n"
            "*Сервер нұсқалары:*\n"
            "• /events1 — *1.16.5* анархиялары (4 таңбалы: 1xxx–6xxx)\n"
            "• /events2 — *1.21* анархиялары (3 таңбалы: 1xx–6xx)\n\n"
            "*Команды:*\n"
            "• /events1, /events2, /help\n"
            "• ➕ Команда қосу • 🗑 Команданы өшіру • ⚙️ Баптаулар\n\n"
            "Төмендегі батырмаларды пайдалан 👇"
        ),
        "no_events": "📭 Белсенді ивенттер жоқ: {label}",
        "events_header": "🎯 Ивенттер — {label}:\n\n",
        "btn_add": "➕ Команда қосу",
        "btn_del": "🗑 Команданы өшіру",
        "btn_settings": "⚙️ Баптаулар",
        "btn_cancel": "❌ Бас тарту",
        "btn_skip": "Өткізіп жіберу",
        "btn_done": "✅ Дайын",
        "choose_version": "➕ *Жылдам команда қосу* ({n}/{max})\n\nСервер нұсқасын таңда:",
        "choose_anarchy_type": "✅ Нұсқа: *{version}*\n\nАнархия түрлерін таңда (бірнешеу болуы мүмкін):",
        "choose_events": "✅ Түрі: *{type} {version}*\n\nИвенттерді таңда:",
        "choose_rarity": "Ивент сиректігін таңда:",
        "cmd_added": "✅ Команда қосылды!",
        "cmd_limit": "❌ Команда лимитіне жетті ({max}).",
        "cmd_exists": "ℹ️ Бұл команда сізде бар.",
        "cancelled": "❌ Бас тартылды.",
        "no_cmds_to_del": "Өшіруге командалар жоқ.",
        "choose_del": "🗑 Өшіру үшін команданы таңда:",
        "cmd_deleted": "✅ Команда өшірілді.",
        "settings_title": "⚙️ *Баптаулар*",
        "settings_sort": "Сұрыптау: {val}",
        "settings_lang": "Тіл: {val}",
        "settings_hidden": "🙈 Жасырын ивенттер: {val}",
        "hidden_none": "жоқ",
        "hidden_applied": "✅ Жасырын ивенттер жаңартылды.",
        "sort_anarchy": "Анархия бойынша",
        "sort_rarity": "Сирек бойынша",
        "no_cmd": "⚠️ Бұндай команда жоқ.",
        "help_text": "👻 *SpookyEvents Bot* — анықтама\n\nСұрақтар үшін төмендегі батырманы басыңыз 👇",
        "support_btn": "💬 Авторға жазу",
        "support_msg": "👇 Авторға жазу үшін батырманы басыңыз:",
    },
    "UA": {
        "welcome": (
            "👻 *SpookyEvents Bot*\n\n"
            "Я відстежую івенти на анархіях SpookyTime.\n\n"
            "*Версії серверів:*\n"
            "• /events1 — анархії *1.16.5* (чотиризначні: 1xxx–6xxx)\n"
            "• /events2 — анархії *1.21* (тризначні: 1xx–6xx)\n\n"
            "*Команди:*\n"
            "• /events1, /events2, /help\n"
            "• ➕ Додати команду • 🗑 Видалити команду • ⚙️ Налаштування\n\n"
            "Використовуй кнопки нижче 👇"
        ),
        "no_events": "📭 Немає активних івентів: {label}",
        "events_header": "🎯 Івенти — {label}:\n\n",
        "btn_add": "➕ Додати команду",
        "btn_del": "🗑 Видалити команду",
        "btn_settings": "⚙️ Налаштування",
        "btn_cancel": "❌ Скасувати",
        "btn_skip": "Пропустити",
        "btn_done": "✅ Готово",
        "choose_version": "➕ *Додавання швидкої команди* ({n}/{max})\n\nОбери версію сервера:",
        "choose_anarchy_type": "✅ Версія: *{version}*\n\nОбери типи анархій (можна декілька):",
        "choose_events": "✅ Тип: *{type} {version}*\n\nОбери івенти:",
        "choose_rarity": "Тепер обери рідкість:",
        "cmd_added": "✅ Команду додано!",
        "cmd_limit": "❌ Досягнуто ліміт команд ({max}).",
        "cmd_exists": "ℹ️ Така команда вже є.",
        "cancelled": "❌ Скасовано.",
        "no_cmds_to_del": "Немає команд для видалення.",
        "choose_del": "🗑 Обери команду для видалення:",
        "cmd_deleted": "✅ Команду видалено.",
        "settings_title": "⚙️ *Налаштування*",
        "settings_sort": "Сортування: {val}",
        "settings_lang": "Мова: {val}",
        "settings_hidden": "🙈 Приховані івенти: {val}",
        "hidden_none": "немає",
        "hidden_applied": "✅ Приховані івенти оновлено.",
        "sort_anarchy": "За анархіями",
        "sort_rarity": "За рідкістю",
        "no_cmd": "⚠️ Такої команди немає.",
        "help_text": "👻 *SpookyEvents Bot* — довідка\n\nЗ питань — кнопка нижче 👇",
        "support_btn": "💬 Написати творцю",
        "support_msg": "👇 Натисни кнопку щоб написати творцю бота:",
    },
    "BY": {
        "welcome": (
            "👻 *SpookyEvents Bot*\n\n"
            "Я адсочваю івэнты на анархіях SpookyTime.\n\n"
            "*Версіі сервераў:*\n"
            "• /events1 — анархіі *1.16.5* (чатырохзначныя: 1xxx–6xxx)\n"
            "• /events2 — анархіі *1.21* (трохзначныя: 1xx–6xx)\n\n"
            "*Каманды:*\n"
            "• /events1, /events2, /help\n"
            "• ➕ Дадаць каманду • 🗑 Выдаліць каманду • ⚙️ Налады\n\n"
            "Выкарыстоўвай кнопкі ніжэй 👇"
        ),
        "no_events": "📭 Няма актыўных івэнтаў: {label}",
        "events_header": "🎯 Івэнты — {label}:\n\n",
        "btn_add": "➕ Дадаць каманду",
        "btn_del": "🗑 Выдаліць каманду",
        "btn_settings": "⚙️ Налады",
        "btn_cancel": "❌ Адмена",
        "btn_skip": "Прапусціць",
        "btn_done": "✅ Гатова",
        "choose_version": "➕ *Дадаванне хуткай каманды* ({n}/{max})\n\nАбяры версію сервера:",
        "choose_anarchy_type": "✅ Версія: *{version}*\n\nАбяры тыпы анархій (можна некалькі):",
        "choose_events": "✅ Тып: *{type} {version}*\n\nАбяры івэнты:",
        "choose_rarity": "Цяпер абяры рэдкасць:",
        "cmd_added": "✅ Каманда дададзена!",
        "cmd_limit": "❌ Дасягнуты ліміт каманд ({max}).",
        "cmd_exists": "ℹ️ Такая каманда ўжо ёсць.",
        "cancelled": "❌ Адменена.",
        "no_cmds_to_del": "Няма каманд для выдалення.",
        "choose_del": "🗑 Абяры каманду для выдалення:",
        "cmd_deleted": "✅ Каманда выдалена.",
        "settings_title": "⚙️ *Налады*",
        "settings_sort": "Сартаванне: {val}",
        "settings_lang": "Мова: {val}",
        "settings_hidden": "🙈 Схаваныя івэнты: {val}",
        "hidden_none": "няма",
        "hidden_applied": "✅ Схаваныя івэнты абноўлены.",
        "sort_anarchy": "Па анархіях",
        "sort_rarity": "Па рэдкасці",
        "no_cmd": "⚠️ Такой каманды няма.",
        "help_text": "👻 *SpookyEvents Bot* — даведка\n\nПа пытаннях — кнопка ніжэй 👇",
        "support_btn": "💬 Напісаць стваральніку",
        "support_msg": "👇 Націсні кнопку каб напісаць стваральніку бота:",
    },
}


def t(lang: str, key: str, **kwargs) -> str:
    lang = lang if lang in TR else "RU"
    text = TR[lang].get(key, TR["RU"].get(key, key))
    return text.format(**kwargs) if kwargs else text

# ==================== ХРАНИЛИЩЕ ====================

DEFAULT_SETTINGS = {"sort": "anarchy", "lang": "RU", "hidden_events": []}


def load_all() -> dict:
    if os.path.exists(USER_COMMANDS_FILE):
        try:
            with open(USER_COMMANDS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_all(data: dict):
    with open(USER_COMMANDS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def get_user_entry(user_id: int) -> dict:
    data = load_all()
    key = str(user_id)
    entry = data.get(key)
    if entry is None:
        entry = {"commands": [], "settings": dict(DEFAULT_SETTINGS)}
        data[key] = entry
        save_all(data)
    elif isinstance(entry, list):
        entry = {"commands": entry, "settings": dict(DEFAULT_SETTINGS)}
        data[key] = entry
        save_all(data)
    else:
        entry.setdefault("commands", [])
        entry.setdefault("settings", dict(DEFAULT_SETTINGS))
        for k, v in DEFAULT_SETTINGS.items():
            entry["settings"].setdefault(k, v)
    return entry


def save_user_entry(user_id: int, entry: dict):
    data = load_all()
    data[str(user_id)] = entry
    save_all(data)


def get_user_cmds(user_id: int) -> list:
    return get_user_entry(user_id)["commands"]


def get_user_settings(user_id: int) -> dict:
    return get_user_entry(user_id)["settings"]


def set_user_setting(user_id: int, key: str, value):
    entry = get_user_entry(user_id)
    entry["settings"][key] = value
    save_user_entry(user_id, entry)


def add_user_cmd(user_id: int, version: str, anarchy_types: list, events: list, rarity: str) -> bool:
    entry = get_user_entry(user_id)
    cmds = entry["commands"]
    if len(cmds) >= MAX_CUSTOM_COMMANDS:
        return False
    new_entry = {
        "version": version,
        "types": sorted(anarchy_types) if anarchy_types else None,
        "events": sorted(events) if events else None,
        "rarity": rarity or None,
    }
    if new_entry in cmds:
        return False
    cmds.append(new_entry)
    entry["commands"] = cmds
    save_user_entry(user_id, entry)
    return True


def delete_user_cmd(user_id: int, idx: int) -> bool:
    entry = get_user_entry(user_id)
    cmds = entry["commands"]
    if 0 <= idx < len(cmds):
        cmds.pop(idx)
        entry["commands"] = cmds
        save_user_entry(user_id, entry)
        return True
    return False

# ==================== КЛАВИАТУРА ====================

def cmd_label(cmd: dict) -> str:
    version = cmd.get("version", "")
    types = cmd.get("types") or cmd.get("type")  # совместимость со старым форматом
    if isinstance(types, list):
        type_str = "+".join(types) if len(types) <= 3 else f"{len(types)} типов"
    else:
        type_str = types or "Все"
    label = f"🔍 {type_str} {version}"
    extras = []
    if cmd.get("events"):
        names = cmd["events"]
        extras.append(names[0] if len(names) == 1 else f"{len(names)} ив.")
    if cmd.get("rarity"):
        extras.append(cmd["rarity"])
    if extras:
        label += " (" + ", ".join(extras) + ")"
    return label


def build_main_keyboard(user_id: int) -> ReplyKeyboardMarkup:
    settings = get_user_settings(user_id)
    lang = settings["lang"]
    cmds = get_user_cmds(user_id)
    rows = [
        [KeyboardButton("/events1"), KeyboardButton("/events2")],
        [KeyboardButton("/help"), KeyboardButton(t(lang, "btn_add"))],
        [KeyboardButton(t(lang, "btn_del")), KeyboardButton(t(lang, "btn_settings"))],
    ]
    custom_buttons = [KeyboardButton(cmd_label(c)) for c in cmds]
    for i in range(0, len(custom_buttons), 2):
        rows.append(custom_buttons[i:i + 2])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

# ==================== ПАРСИНГ ИВЕНТОВ ====================

def get_version(num) -> str:
    return VERSION_4DIGIT if len(str(num)) == 4 else VERSION_3DIGIT


def filter_events(version: str, type_nums: list) -> list:
    evs = events_data.get(version, [])
    result = []
    for e in evs:
        num = e["anarchy_num"]
        if version == VERSION_4DIGIT:
            prefix = num // 1000
        else:
            prefix = num // 100
        if prefix in type_nums:
            result.append(e)
    return result


def remove_hidden(evs: list, hidden: list) -> list:
    if not hidden:
        return evs
    hidden_set = set(hidden)
    return [e for e in evs if e["name"] not in hidden_set]


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
        rarity = None
        if loot:
            for r in RARITY_ORDER:
                if r in loot:
                    rarity = r
                    break
        events.append({
            "anarchy_num": num,
            "name": name_match.group(1).strip(),
            "rarity": rarity,
            "loot_level": loot,
            "status": status,
            "time_str": time_str,
            "location": location,
            "raw_first_line": first
        })
    return events


def sort_events(evs: list, sort_mode: str) -> list:
    if sort_mode == "rarity":
        return sorted(evs, key=lambda e: (RARITY_ORDER.get(e.get("rarity"), len(RARITY_ORDER)), e["anarchy_num"]))
    return sorted(evs, key=lambda e: e["anarchy_num"])


def format_events(evs: list, version: str, lang: str, type_name: str = None) -> str:
    label = f"{type_name} {version}" if type_name else version
    if not evs:
        return t(lang, "no_events", label=label)
    out = t(lang, "events_header", label=label)
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
            await update.message.reply_text(text[i:i + 4000], **kwargs)
    else:
        await update.message.reply_text(text, **kwargs)

# ==================== КОМАНДЫ БОТА ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    kb = build_main_keyboard(user_id)
    await update.message.reply_text(t(lang, "welcome"), parse_mode="Markdown", reply_markup=kb)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    kb = build_main_keyboard(user_id)
    inline_kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t(lang, "support_btn"), url=f"https://t.me/{SUPPORT_USERNAME}")
    ]])
    await update.message.reply_text(
        t(lang, "help_text"), parse_mode="Markdown", reply_markup=kb
    )
    await update.message.reply_text(
        t(lang, "support_msg"), reply_markup=inline_kb
    )


async def events1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    kb = build_main_keyboard(user_id)
    all_type_nums = list(ANARCHY_TYPES.values())
    evs = filter_events(VERSION_4DIGIT, all_type_nums)
    evs = remove_hidden(evs, settings.get("hidden_events", []))
    evs = sort_events(evs, settings["sort"])
    await send_long(update, format_events(evs, VERSION_4DIGIT, settings["lang"]), kb)


async def events2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    kb = build_main_keyboard(user_id)
    all_type_nums = list(ANARCHY_TYPES.values())
    evs = filter_events(VERSION_3DIGIT, all_type_nums)
    evs = remove_hidden(evs, settings.get("hidden_events", []))
    evs = sort_events(evs, settings["sort"])
    await send_long(update, format_events(evs, VERSION_3DIGIT, settings["lang"]), kb)

# ==================== ДОБАВЛЕНИЕ БЫСТРОЙ КОМАНДЫ ====================

def anarchy_types_inline_kb(selected: set, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for name in ANARCHY_TYPE_LIST:
        mark = "✅ " if name in selected else ""
        rows.append([InlineKeyboardButton(f"{mark}{name}", callback_data=f"atype:{name}")])
    rows.append([InlineKeyboardButton(t(lang, "btn_skip"), callback_data="atype:skip")])
    if selected:
        rows.append([InlineKeyboardButton(t(lang, "btn_done"), callback_data="atype:done")])
    return InlineKeyboardMarkup(rows)


def events_inline_kb(selected: set, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for i, name in enumerate(EVENT_TYPES):
        mark = "✅ " if name in selected else ""
        rows.append([InlineKeyboardButton(f"{mark}{name}", callback_data=f"ev:{i}")])
    rows.append([InlineKeyboardButton(t(lang, "btn_skip"), callback_data="ev:skip")])
    if selected:
        rows.append([InlineKeyboardButton(t(lang, "btn_done"), callback_data="ev:done")])
    return InlineKeyboardMarkup(rows)


def rarity_inline_kb(lang: str) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(r, callback_data=f"rar:{r}")] for r in RARITIES]
    rows.append([InlineKeyboardButton(t(lang, "btn_skip"), callback_data="rar:skip")])
    return InlineKeyboardMarkup(rows)


async def add_cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    cmds = get_user_cmds(user_id)
    if len(cmds) >= MAX_CUSTOM_COMMANDS:
        await update.message.reply_text(
            t(lang, "cmd_limit", max=MAX_CUSTOM_COMMANDS),
            reply_markup=build_main_keyboard(user_id)
        )
        return ConversationHandler.END
    version_kb = ReplyKeyboardMarkup(
        [[KeyboardButton("1.16.5"), KeyboardButton("1.21")], [KeyboardButton(t(lang, "btn_cancel"))]],
        resize_keyboard=True
    )
    await update.message.reply_text(
        t(lang, "choose_version", n=len(cmds), max=MAX_CUSTOM_COMMANDS),
        parse_mode="Markdown", reply_markup=version_kb
    )
    return CHOOSE_VERSION


async def add_cmd_version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    text = update.message.text.strip()
    if text == t(lang, "btn_cancel"):
        return await cancel(update, context)
    if text == VERSION_4DIGIT:
        context.user_data["add_version"] = VERSION_4DIGIT
    elif text == VERSION_3DIGIT:
        context.user_data["add_version"] = VERSION_3DIGIT
    else:
        await update.message.reply_text("Пожалуйста, выбери версию кнопкой.")
        return CHOOSE_VERSION
    context.user_data["add_types"] = set()
    version = context.user_data["add_version"]
    await update.message.reply_text(
        t(lang, "choose_anarchy_type", version=version),
        parse_mode="Markdown",
        reply_markup=anarchy_types_inline_kb(set(), lang)
    )
    return CHOOSE_TYPE


async def choose_anarchy_type_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    selected = context.user_data.setdefault("add_types", set())
    data = query.data.split(":", 1)[1]

    if data == "skip":
        context.user_data["add_types"] = set()
        return await proceed_to_events(update, context, query)
    if data == "done":
        return await proceed_to_events(update, context, query)

    if data in selected:
        selected.discard(data)
    else:
        selected.add(data)
    await query.edit_message_reply_markup(reply_markup=anarchy_types_inline_kb(selected, lang))
    return CHOOSE_TYPE


async def proceed_to_events(update, context, query):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    context.user_data["add_events"] = set()
    types = context.user_data.get("add_types", set())
    version = context.user_data.get("add_version", "")
    type_str = "+".join(sorted(types)) if types else "Все"
    await query.edit_message_text(
        t(lang, "choose_events", type=type_str, version=version),
        parse_mode="Markdown",
        reply_markup=events_inline_kb(set(), lang)
    )
    return CHOOSE_EVENTS


async def choose_events_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    selected = context.user_data.setdefault("add_events", set())
    data = query.data.split(":", 1)[1]

    if data == "skip":
        context.user_data["add_events"] = set()
        return await proceed_to_rarity(update, context, query)
    if data == "done":
        return await proceed_to_rarity(update, context, query)

    idx = int(data)
    name = EVENT_TYPES[idx]
    if name in selected:
        selected.discard(name)
    else:
        selected.add(name)
    await query.edit_message_reply_markup(reply_markup=events_inline_kb(selected, lang))
    return CHOOSE_EVENTS


async def proceed_to_rarity(update, context, query):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    selected = context.user_data.get("add_events", set())
    if selected and selected.issubset(NO_RARITY_EVENTS):
        return await finalize_add_cmd(update, context, query, rarity=None)
    await query.edit_message_text(
        t(lang, "choose_rarity"),
        reply_markup=rarity_inline_kb(lang)
    )
    return CHOOSE_RARITY


async def choose_rarity_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data.split(":", 1)[1]
    rarity = None if data == "skip" else data
    return await finalize_add_cmd(update, context, query, rarity=rarity)


async def finalize_add_cmd(update, context, query, rarity):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    version = context.user_data.get("add_version")
    types_sel = list(context.user_data.get("add_types", set())) or None
    events_sel = list(context.user_data.get("add_events", set())) or None

    success = add_user_cmd(user_id, version, types_sel, events_sel, rarity)
    kb = build_main_keyboard(user_id)
    if success:
        msg = t(lang, "cmd_added")
    else:
        cmds = get_user_cmds(user_id)
        msg = t(lang, "cmd_limit", max=MAX_CUSTOM_COMMANDS) if len(cmds) >= MAX_CUSTOM_COMMANDS else t(lang, "cmd_exists")
    await query.edit_message_text(msg)
    await context.bot.send_message(chat_id=update.effective_chat.id, text="👍", reply_markup=kb)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    context.user_data.clear()
    await update.message.reply_text(t(lang, "cancelled"), reply_markup=build_main_keyboard(user_id))
    return ConversationHandler.END

# ==================== УДАЛЕНИЕ БЫСТРОЙ КОМАНДЫ ====================

async def delete_cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    cmds = get_user_cmds(user_id)
    if not cmds:
        await update.message.reply_text(t(lang, "no_cmds_to_del"), reply_markup=build_main_keyboard(user_id))
        return
    rows = [[InlineKeyboardButton(cmd_label(c), callback_data=f"delcmd:{i}")] for i, c in enumerate(cmds)]
    await update.message.reply_text(t(lang, "choose_del"), reply_markup=InlineKeyboardMarkup(rows))


async def delete_cmd_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    idx = int(query.data.split(":", 1)[1])
    delete_user_cmd(user_id, idx)
    await query.edit_message_text(t(lang, "cmd_deleted"))
    await context.bot.send_message(chat_id=update.effective_chat.id, text="👍", reply_markup=build_main_keyboard(user_id))

# ==================== НАСТРОЙКИ ====================

def hidden_events_inline_kb(selected: set, lang: str) -> InlineKeyboardMarkup:
    rows = []
    for i, name in enumerate(EVENT_TYPES):
        mark = "✅ " if name in selected else ""
        rows.append([InlineKeyboardButton(f"{mark}{name}", callback_data=f"hideev:{i}")])
    rows.append([InlineKeyboardButton(t(lang, "btn_done"), callback_data="hideev:apply")])
    rows.append([InlineKeyboardButton("⬅️", callback_data="set:back")])
    return InlineKeyboardMarkup(rows)


def settings_kb(user_id: int) -> InlineKeyboardMarkup:
    settings = get_user_settings(user_id)
    lang = settings["lang"]
    sort_label = t(lang, "sort_anarchy") if settings["sort"] == "anarchy" else t(lang, "sort_rarity")
    hidden = settings.get("hidden_events", [])
    if not hidden:
        hidden_label = t(lang, "hidden_none")
    elif len(hidden) == 1:
        hidden_label = hidden[0]
    else:
        hidden_label = f"{len(hidden)}"
    rows = [
        [InlineKeyboardButton(t(lang, "settings_sort", val=sort_label), callback_data="set:sort")],
        [InlineKeyboardButton(t(lang, "settings_lang", val=settings["lang"]), callback_data="set:lang")],
        [InlineKeyboardButton(t(lang, "settings_hidden", val=hidden_label), callback_data="set:hidden")],
    ]
    return InlineKeyboardMarkup(rows)


async def settings_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = get_user_settings(user_id)["lang"]
    await update.message.reply_text(
        t(lang, "settings_title"), parse_mode="Markdown", reply_markup=settings_kb(user_id)
    )


async def settings_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id
    data = query.data

    if data == "set:sort":
        lang = get_user_settings(user_id)["lang"]
        rows = [
            [InlineKeyboardButton(t(lang, "sort_anarchy"), callback_data="setsort:anarchy")],
            [InlineKeyboardButton(t(lang, "sort_rarity"), callback_data="setsort:rarity")],
            [InlineKeyboardButton("⬅️", callback_data="set:back")],
        ]
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
        return
    if data.startswith("setsort:"):
        set_user_setting(user_id, "sort", data.split(":", 1)[1])
        await query.edit_message_reply_markup(reply_markup=settings_kb(user_id))
        return
    if data == "set:lang":
        rows = [[InlineKeyboardButton(l, callback_data=f"setlang:{l}")] for l in LANGUAGES]
        rows.append([InlineKeyboardButton("⬅️", callback_data="set:back")])
        await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(rows))
        return
    if data.startswith("setlang:"):
        set_user_setting(user_id, "lang", data.split(":", 1)[1])
        await query.edit_message_reply_markup(reply_markup=settings_kb(user_id))
        await context.bot.send_message(chat_id=update.effective_chat.id, text="👍", reply_markup=build_main_keyboard(user_id))
        return
    if data == "set:hidden":
        lang = get_user_settings(user_id)["lang"]
        hidden = set(get_user_settings(user_id).get("hidden_events", []))
        context.user_data["hidden_temp"] = hidden
        await query.edit_message_reply_markup(reply_markup=hidden_events_inline_kb(hidden, lang))
        return
    if data.startswith("hideev:"):
        lang = get_user_settings(user_id)["lang"]
        val = data.split(":", 1)[1]
        temp = context.user_data.setdefault(
            "hidden_temp", set(get_user_settings(user_id).get("hidden_events", []))
        )
        if val == "apply":
            set_user_setting(user_id, "hidden_events", sorted(temp))
            context.user_data.pop("hidden_temp", None)
            await query.edit_message_reply_markup(reply_markup=settings_kb(user_id))
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=t(lang, "hidden_applied"),
                reply_markup=build_main_keyboard(user_id)
            )
            return
        idx = int(val)
        name = EVENT_TYPES[idx]
        if name in temp:
            temp.discard(name)
        else:
            temp.add(name)
        await query.edit_message_reply_markup(reply_markup=hidden_events_inline_kb(temp, lang))
        return
    if data == "set:back":
        context.user_data.pop("hidden_temp", None)
        await query.edit_message_reply_markup(reply_markup=settings_kb(user_id))
        return

# ==================== ОБРАБОТКА КАСТОМНЫХ КОМАНД ====================

async def handle_custom_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    settings = get_user_settings(user_id)
    lang = settings["lang"]

    if text == t(lang, "btn_add"):
        return await add_cmd_start(update, context)
    if text == t(lang, "btn_del"):
        return await delete_cmd_start(update, context)
    if text == t(lang, "btn_settings"):
        return await settings_start(update, context)

    cmds = get_user_cmds(user_id)
    matched = next((c for c in cmds if cmd_label(c) == text), None)
    if matched is None:
        return

    version = matched["version"]
    # поддержка старого формата (type) и нового (types)
    if matched.get("types"):
        type_nums = [ANARCHY_TYPES[tp] for tp in matched["types"] if tp in ANARCHY_TYPES]
    elif matched.get("type"):
        type_nums = [ANARCHY_TYPES[matched["type"]]] if matched["type"] in ANARCHY_TYPES else list(ANARCHY_TYPES.values())
    else:
        type_nums = list(ANARCHY_TYPES.values())

    evs = filter_events(version, type_nums)
    if matched.get("events"):
        evs = [e for e in evs if e["name"] in matched["events"]]
    if matched.get("rarity"):
        evs = [e for e in evs if e.get("rarity") == matched["rarity"]]
    evs = remove_hidden(evs, settings.get("hidden_events", []))
    evs = sort_events(evs, settings["sort"])

    types_label = "+".join(matched["types"]) if matched.get("types") else matched.get("type", "")
    await send_long(update, format_events(evs, version, lang, types_label), build_main_keyboard(user_id))

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

    await run_web_server()

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
                        events_data[VERSION_4DIGIT].clear()
                        events_data[VERSION_3DIGIT].clear()
                        for event in parsed:
                            v = get_version(event["anarchy_num"])
                            events_data[v].append(event)
                        events_data[VERSION_4DIGIT].sort(key=lambda x: x["anarchy_num"])
                        events_data[VERSION_3DIGIT].sort(key=lambda x: x["anarchy_num"])
                        print(f"🔄 Обновлено: {VERSION_4DIGIT} — {len(events_data[VERSION_4DIGIT])}, {VERSION_3DIGIT} — {len(events_data[VERSION_3DIGIT])}")
            except Exception as e:
                print(f"❌ Ошибка опроса: {e}")
                traceback.print_exc()
            await asyncio.sleep(UPDATE_INTERVAL)

    asyncio.create_task(update_loop())

    bot_app = Application.builder().token(BOT_TOKEN).build()
    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", help_cmd))
    bot_app.add_handler(CommandHandler("events1", events1))
    bot_app.add_handler(CommandHandler("events2", events2))

    # Все локализованные варианты кнопок "Добавить команду"
    add_btn_pattern = "^(" + "|".join(re.escape(TR[l]["btn_add"]) for l in LANGUAGES) + ")$"
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(add_btn_pattern), add_cmd_start)],
        states={
            CHOOSE_VERSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_cmd_version)],
            CHOOSE_TYPE: [CallbackQueryHandler(choose_anarchy_type_cb, pattern=r"^atype:")],
            CHOOSE_EVENTS: [CallbackQueryHandler(choose_events_cb, pattern=r"^ev:")],
            CHOOSE_RARITY: [CallbackQueryHandler(choose_rarity_cb, pattern=r"^rar:")],
        },
        fallbacks=[
            MessageHandler(filters.TEXT & ~filters.COMMAND, cancel),
            CommandHandler("start", start),
        ],
    )
    bot_app.add_handler(conv_handler)

    bot_app.add_handler(CallbackQueryHandler(delete_cmd_cb, pattern=r"^delcmd:"))
    bot_app.add_handler(CallbackQueryHandler(settings_cb, pattern=r"^set"))
    bot_app.add_handler(CallbackQueryHandler(settings_cb, pattern=r"^hideev:"))

    bot_app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
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
