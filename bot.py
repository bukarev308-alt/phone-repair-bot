# bot_weekly_archive_final.py
import os
import json
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# Налаштування
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)
DATA_FILE = "data.json"
DATE_FORMAT = "%d.%m.%Y %H:%M"

DEFAULT_DATA = {
    "stores": ["It Center", "Леся", "Особисті"],
    "current_week_key": None,
    "weeks": {},
    "archive": {}
}

# =======================
# Завантаження / збереження даних
# =======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return init_data()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
        except json.JSONDecodeError:
            return init_data()
    if "phones" in d and ("weeks" not in d or "archive" not in d):
        d = migrate_old_flat_data(d)
    for k in DEFAULT_DATA:
        if k not in d:
            d[k] = DEFAULT_DATA[k] if k != "current_week_key" else None
    if not d.get("current_week_key"):
        d["current_week_key"] = get_week_label_for_date(datetime.now().date())
    if d["current_week_key"] not in d.get("weeks", {}):
        d["weeks"][d["current_week_key"]] = []
    save_data(d)
    return d

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def init_data():
    d = DEFAULT_DATA.copy()
    current_key = get_week_label_for_date(datetime.now().date())
    d["current_week_key"] = current_key
    d["weeks"] = {current_key: []}
    save_data(d)
    return d

def migrate_old_flat_data(d_old):
    d = DEFAULT_DATA.copy()
    if "stores" in d_old:
        d["stores"] = d_old["stores"]
    current_key = get_week_label_for_date(datetime.now().date())
    d["current_week_key"] = current_key
    d["weeks"] = {current_key: d_old.get("phones", [])}
    save_data(d)
    return d

# =======================
# Допоміжні функції дати / тижні
# =======================
def get_week_start(date_obj):
    weekday = date_obj.weekday()
    return date_obj - timedelta(days=weekday)

def get_week_end(date_obj):
    return get_week_start(date_obj) + timedelta(days=6)

def date_to_str(d):
    return d.strftime("%d.%m.%Y")

def get_week_label_for_date(date_obj):
    start = get_week_start(date_obj)
    end = get_week_end(date_obj)
    return f"Тиждень {date_to_str(start)} — {date_to_str(end)}"

def ensure_current_week_exists(data):
    cur_key = data.get("current_week_key")
    if not cur_key:
        cur_key = get_week_label_for_date(datetime.now().date())
        data["current_week_key"] = cur_key
    if cur_key not in data.get("weeks", {}):
        data["weeks"][cur_key] = []
    return data

# =======================
# Стан користувача
# =======================
user_state = {}  # chat_id -> {"stack": [], "tmp": {}}

def ensure_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"stack": [], "tmp": {}}

def push_state(chat_id, state_name):
    ensure_state(chat_id)
    user_state[chat_id]["stack"].append(state_name)

def pop_state(chat_id):
    ensure_state(chat_id)
    if user_state[chat_id]["stack"]:
        return user_state[chat_id]["stack"].pop()
    return None

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# Keyboards
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📱 Додати телефон", "📋 Переглянути телефони")
    kb.row("📊 Підсумок за тиждень", "📅 Підсумок за місяць")
    kb.row("✏️ Редагувати / 🗑 Видалити", "🧹 Почати новий тиждень")
    kb.row("🏪 Магазини")
    return kb

def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

def stores_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in data["stores"]:
        kb.add(s)
    kb.add("➕ Додати магазин")
    kb.add("⬅️ Назад")
    return kb

def edit_action_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✏️ Редагувати", "🗑 Видалити")
    kb.add("⬅️ Назад")
    return kb

def edit_field_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Магазин", "Модель", "Проблема", "Ціна")
    kb.add("⬅️ Назад")
    return kb

def confirm_delete_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Так", "❌ Ні")
    return kb

def view_choice_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📅 Поточний тиждень", "📦 Архів")
    kb.add("⬅️ Назад")
    return kb

# =======================
# Завантажуємо дані
# =======================
data = load_data()
ensure_current_week_exists(data)

# =======================
# Функції підсумків та архіву
# =======================
def summarize_week(chat_id, week_label, phones):
    if not phones:
        bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
        return
    total = sum(p["price"] for p in phones)
    count = len(phones)
    stores_summary = {}
    for p in phones:
        stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
    store_text = "\n".join(f"• {s}: {v:.2f} грн" for s, v in stores_summary.items())
    bot.send_message(chat_id,
                     f"📊 Підсумок — {week_label}\n🔢 Кількість: {count}\n💰 Сума: {total:.2f} грн\n\n<b>По магазинах:</b>\n{store_text}",
                     parse_mode="HTML", reply_markup=main_menu())

def summarize_month(chat_id):
    now = datetime.now().date()
    month = now.month
    year = now.year
    total = 0
    count = 0
    stores_summary = {}
    for week_label, phones in {**data.get("archive", {}), data["current_week_key"]: data["weeks"].get(data["current_week_key"], [])}.items():
        try:
            start_str = week_label.split("—")[0].replace("Тиждень ", "").strip()
            start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
            if start_date.month == month and start_date.year == year:
                for p in phones:
                    total += p["price"]
                    count += 1
                    stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
        except:
            continue
    if count == 0:
        bot.send_message(chat_id, "📭 Немає записів за поточний місяць.", reply_markup=main_menu())
        return
    store_text = "\n".join(f"• {s}: {v:.2f} грн" for s, v in stores_summary.items())
    bot.send_message(chat_id,
                     f"📅 Підсумок за {now.strftime('%B %Y')}\n🔢 Кількість: {count}\n💰 Сума: {total:.2f} грн\n\n<b>По магазинах:</b>\n{store_text}",
                     parse_mode="HTML", reply_markup=main_menu())

def show_archive_weeks(chat_id):
    if not data.get("archive"):
        bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
        clear_state(chat_id)
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    entries = []
    for week_label, phones in data.get("archive", {}).items():
        cnt = len(phones)
        total = sum(p["price"] for p in phones) if phones else 0
        entries.append((week_label, cnt, total))
    def parse_start(label):
        try:
            start_str = label.split("—")[0].replace("Тиждень ", "").strip()
            return datetime.strptime(start_str, "%d.%m.%Y")
        except:
            return datetime.min
    entries.sort(key=lambda x: parse_start(x[0]), reverse=True)
    for week_label, cnt, total in entries:
        kb.add(f"{week_label} — {cnt} од., {int(total)} грн")
    kb.add("⬅️ Назад")
    push_state(chat_id, "archive_list")
    bot.send_message(chat_id, "Виберіть тиждень (короткий звіт):", reply_markup=kb)

def show_archive_details(chat_id, week_label):
    phones = data["archive"].get(week_label, [])
    if not phones:
        bot.send_message(chat_id, f"📦 {week_label} — порожньо", reply_markup=main_menu())
        return
    text = f"📦 <b>{week_label}</b>:\n\n"
    for i, p in enumerate(phones, 1):
        text += (f"{i}. {p['model']} ({p['store']})\n"
                 f"🔧 {p['problem']}\n"
                 f"💰 {p['price']:.2f} грн\n"
                 f"🕒 {p['date']}\n\n")
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())

# =======================
# START
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

# =======================
# Далі йде generic_handler і всі стани
# =======================
# (Тут можна вставити логіку додавання, редагування, перегляду та видалення,
# як у попередньому коді, але вже структуровано та з підтримкою архіву)

# =======================
# Запуск бота
# =======================
if __name__ == "__main__":
    print("Бот запущено...")
    bot.infinity_polling()