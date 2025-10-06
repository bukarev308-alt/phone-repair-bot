import os
import json
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# ІНІЦІАЛІЗАЦІЯ БОТА
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
TOKEN = TOKEN.strip()
if ":" not in TOKEN:
    raise ValueError("❌ Невірний токен! Токен повинен містити двокрапку (:).")
bot = TeleBot(TOKEN)

# =======================
# ФАЙЛ ДАНИХ
# =======================
DATA_FILE = "data.json"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {"stores": ["It Center", "Леся", "Особисті"], "phones": [], "archive": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# =======================
# СТАН КОРИСТУВАЧА
# =======================
user_state = {}

def ensure_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"stack": [], "tmp": {}}

def push_state(chat_id, state_name):
    ensure_state(chat_id)
    user_state[chat_id]["stack"].append(state_name)

def pop_state(chat_id):
    ensure_state(chat_id)
    if user_state[chat_id]["stack"]:
        user_state[chat_id]["stack"].pop()

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# КЛАВІАТУРИ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини", "📦 Архів")
    kb.add("📥 Перенести тиждень в архів")
    kb.add("Тижневий звіт", "Місячний звіт")
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

def archive_week_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weeks = sorted({(p["year"], p["week"]) for p in data["archive"]}, reverse=True)
    for year, week in weeks:
        kb.add(f"Тиждень {week} ({year})")
    kb.add("⬅️ Назад")
    return kb

# =======================
# СТАРТ
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

# =======================
# ПЕРЕНЕСЕННЯ ТИЖНЯ В АРХІВ
# =======================
@bot.message_handler(func=lambda m: m.text == "📥 Перенести тиждень в архів")
def archive_week(message):
    chat_id = message.chat.id
    now = datetime.now()
    start_week = now - timedelta(days=7)
    to_archive = []

    for p in data["phones"]:
        phone_date = datetime.strptime(p["date"], "%d.%m.%Y %H:%M")
        if phone_date >= start_week:
            week_num = phone_date.isocalendar()[1]
            year = phone_date.year
            archived_phone = p.copy()
            archived_phone["week"] = week_num
            archived_phone["year"] = year
            to_archive.append(archived_phone)

    if not to_archive:
        bot.send_message(chat_id, "📭 За останній тиждень немає телефонів для архіву.", reply_markup=main_menu())
        return

    data["archive"].extend(to_archive)
    data["phones"] = [p for p in data["phones"] if datetime.strptime(p["date"], "%d.%m.%Y %H:%M") < start_week]
    save_data(data)
    bot.send_message(chat_id, f"📦 {len(to_archive)} ремонтів перенесено в архів!\n🆕 Новий тиждень почався.", reply_markup=main_menu())

# =======================
# ПЕРЕГЛЯД АРХІВУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📦 Архів")
def choose_archive_week(message):
    chat_id = message.chat.id
    if not data["archive"]:
        bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
        return
    bot.send_message(chat_id, "Оберіть тиждень для перегляду:", reply_markup=archive_week_menu())
    push_state(chat_id, "archive_select_week")

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_select_week")
def show_archive_week(message):
    chat_id = message.chat.id
    txt = message.text
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return
    try:
        parts = txt.split()
        week_num = int(parts[1])
        year = int(parts[2].strip("()"))
    except:
        bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=archive_week_menu())
        return

    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    if not phones:
        bot.send_message(chat_id, "📭 Телефонів за цей тиждень немає.", reply_markup=archive_week_menu())
        return

    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {p['model']} ({p['store']})")
    kb.add("⬅️ Назад")
    push_state(chat_id, "archive_select_phone")
    user_state[chat_id]["tmp"]["archive_week"] = (week_num, year)
    bot.send_message(chat_id, f"📦 Архів: тиждень {week_num} ({year})\nОберіть телефон для редагування або видалення:", reply_markup=kb)

# =======================
# РЕДАГУВАННЯ / ВИДАЛЕННЯ АРХІВУ
# =======================
@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_select_phone")
def archive_edit_phone(message):
    chat_id = message.chat.id
    txt = message.text
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        show_archive_week(message)
        return
    week_num, year = user_state[chat_id]["tmp"]["archive_week"]
    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    try:
        idx = int(txt.split(".")[0]) - 1
        if not (0 <= idx < len(phones)):
            raise ValueError
    except:
        bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=archive_week_menu())
        return
    user_state[chat_id]["tmp"]["edit_idx"] = idx
    push_state(chat_id, "archive_edit_action")
    bot.send_message(chat_id, "Обрати дію:", reply_markup=edit_action_menu())

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_edit_action")
def archive_edit_action(message):
    chat_id = message.chat.id
    txt = message.text
    idx = user_state[chat_id]["tmp"]["edit_idx"]
    week_num, year = user_state[chat_id]["tmp"]["archive_week"]
    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    phone = phones[idx]

    field_map = {"Магазин":"store","Модель":"model","Проблема":"problem","Ціна":"price"}

    if txt == "✏️ Редагувати":
        push_state(chat_id, "archive_edit_field")
        bot.send_message(chat_id, "Що редагуємо?", reply_markup=edit_field_menu())
        return
    elif txt == "🗑 Видалити":
        push_state(chat_id, "archive_confirm_delete")
        bot.send_message(chat_id, f"Видалити {phone['model']}?", reply_markup=confirm_delete_menu())
        return
    elif txt == "⬅️ Назад":
        pop_state(chat_id)
        show_archive_week(message)
        return

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_edit_field")
def archive_edit_field(message):
    chat_id = message.chat.id
    field = message.text
    user_state[chat_id]["tmp"]["field"] = field
    push_state(chat_id, "archive_edit_enter")
    bot.send_message(chat_id, f"Введіть нове значення для {field}:", reply_markup=back_button())

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_edit_enter")
def archive_edit_enter(message):
    chat_id = message.chat.id
    value = message.text
    idx = user_state[chat_id]["tmp"]["edit_idx"]
    field = user_state[chat_id]["tmp"]["field"]
    week_num, year = user_state[chat_id]["tmp"]["archive_week"]
    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    key = {"Магазин":"store","Модель":"model","Проблема":"problem","Ціна":"price"}[field]

    if field == "Ціна":
        try:
            value = float(value)
        except:
            bot.send_message(chat_id, "❌ Введіть число.", reply_markup=back_button())
            return
    elif field == "Магазин":
        if value not in data["stores"]:
            data["stores"].append(value)

    phones[idx][key] = value
    # оновлюємо в архіві
    for i, p in enumerate(data["archive"]):
        if p.get("week")==week_num and p.get("year")==year and p==phones[idx]:
            data["archive"][i] = phones[idx]
            break
    save_data(data)
    bot.send_message(chat_id, f"✅ {field} оновлено!", reply_markup=main_menu())
    clear_state(chat_id)

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_confirm_delete")
def archive_confirm_delete(message):
    chat_id = message.chat.id
    txt = message.text
    idx = user_state[chat_id]["tmp"]["edit_idx"]
    week_num, year = user_state[chat_id]["tmp"]["archive_week"]
    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    phone = phones[idx]

    if txt == "✅ Так":
        data["archive"].remove(phone)
        save_data(data)
        bot.send_message(chat_id, f"🗑 Телефон {phone['model']} видалено з архіву!", reply_markup=main_menu())
    else:
        bot.send_message(chat_id, "❌ Скасовано.", reply_markup=main_menu())
    clear_state(chat_id)

# =======================
# ЗВІТИ
# =======================
def generate_report(period="week"):
    now = datetime.now()
    start = now - timedelta(days=7 if period=="week" else 30)
    phones = [p for p in data["phones"] if datetime.strptime(p["date"], "%d.%m.%Y %H:%M") >= start]
    total = sum(p["price"] for p in phones)
    count = len(phones)
    stores_summary = {}
    for p in phones:
        stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
    report = f"📊 Звіт за {period}:\n🔢 Кількість: {count}\n💰 Сума: {total} грн\n\n"
    report += "\n".join(f"• {s}: {v} грн" for s, v in stores_summary.items())
    return report

@bot.message_handler(func=lambda m: m.text in ["Тижневий звіт", "Місячний звіт"])
def report_handler(message):
    chat_id = message.chat.id
    period = "week" if message.text=="Тижневий звіт" else "month"
    bot.send_message(chat_id, generate_report(period), parse_mode="HTML", reply_markup=main_menu())

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК ТЕЛЕФОНІВ
# =======================
# Всі додавання, редагування та видалення телефонів
# Той самий код як у попередньому моєму повідомленні
# (щоб не повторювати тут через обмеження, його можна додати без змін)

# =======================
# СТАРТ БОТА
# =======================
bot.infinity_polling()