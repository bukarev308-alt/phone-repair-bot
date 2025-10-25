import os
import json
import threading
import re
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
DATA_FILE = "data.json"
ARCHIVE_FILE = "archive.json"

bot = TeleBot(TOKEN)
data_lock = threading.Lock()

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ
# =======================
def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            return {"stores": ["It Center", "Леся", "Особисті"], "phones": []}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_data(d):
    with data_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

def load_archive():
    with data_lock:
        if not os.path.exists(ARCHIVE_FILE):
            return []
        with open(ARCHIVE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_archive(a):
    with data_lock:
        with open(ARCHIVE_FILE, "w", encoding="utf-8") as f:
            json.dump(a, f, ensure_ascii=False, indent=2)

data = load_data()
archive = load_archive()

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
    if not user_state[chat_id]["stack"]:
        user_state[chat_id]["tmp"] = {}

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# УТИЛІТИ
# =======================
def fmt_price(p):
    try:
        if int(p) == p:
            return f"{int(p)}"
    except Exception:
        pass
    return f"{p}"

def phone_display(p):
    return (f"{p['model']} ({p['store']})\n"
            f"🔧 {p['problem']}\n"
            f"💰 {fmt_price(p['price'])} грн\n"
            f"🕒 {p['date']}")

def phone_short(p):
    return f"{p['model']} ({p['store']})"

# =======================
# КЛАВІАТУРИ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини", "🗂 Архів")
    kb.add("📝 Перенести тиждень в архів", "📊 Звіт")
    return kb

def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

def stores_menu(include_add=True):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in data["stores"]:
        kb.add(s)
    if include_add:
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
    kb.add("Магазин", "Модель")
    kb.add("Проблема", "Ціна")
    kb.add("⬅️ Назад")
    return kb

def confirm_delete_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Так", "❌ Ні")
    return kb

def phones_list_keyboard(phones):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {phone_short(p)}")
    kb.add("⬅️ Назад")
    return kb

def archive_week_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for w in archive:
        kb.add(w["week"])
    kb.add("⬅️ Назад")
    return kb

def archive_view_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔽 Показати телефони", "🔼 Відновити тиждень")
    kb.add("📤 Відновити телефон", "❌ Видалити телефон з архіву")
    kb.add("🗑 Видалити тиждень", "⬅️ Назад")
    return kb

def archive_report_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("По тижню", "По місяцю")
    kb.add("⬅️ Назад")
    return kb

def archive_report_type_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("💰 Суми", "📱 Суми + телефони")
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
# ТУТ ВСТАВ ЛИШЕ ВСІ ФУНКЦІЇ ТВОГО ПОПЕРЕДНЬОГО КОДУ
# (додавання, редагування, архів, видалення, перенесення тижня)
# =======================

# =======================
# ЗВІТИ
# =======================
@bot.message_handler(func=lambda m: m.text == "📊 Звіт")
def report_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "report_period")
    bot.send_message(chat_id, "Виберіть період для звіту:", reply_markup=archive_report_menu())

@bot.message_handler(func=lambda m: current_state(m.chat.id) in ["report_period", "report_week_select", "report_month_select", "report_type"])
def report_handler(message):
    chat_id = message.chat.id
    txt = message.text.strip()
    state = current_state(chat_id)

    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємось у головне меню.", reply_markup=main_menu())
        return

    # Обираємо період
    if state == "report_period":
        if txt == "По тижню":
            if not archive:
                bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
                clear_state(chat_id)
                return
            push_state(chat_id, "report_week_select")
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for w in archive:
                kb.add(w["week"])
            kb.add("⬅️ Назад")
            bot.send_message(chat_id, "Оберіть тиждень для звіту:", reply_markup=kb)
        elif txt == "По місяцю":
            push_state(chat_id, "report_month_select")
            bot.send_message(chat_id, "Введіть місяць у форматі YYYY-MM:", reply_markup=back_button())
        else:
            bot.send_message(chat_id, "❌ Оберіть варіант з меню.", reply_markup=archive_report_menu())
        return

    # Вибір тижня
    if state == "report_week_select":
        weeks = [w["week"] for w in archive]
        if txt not in weeks:
            bot.send_message(chat_id, "❌ Оберіть тиждень зі списку.", reply_markup=archive_week_menu())
            return
        idx = weeks.index(txt)
        user_state[chat_id]["tmp"]["report_week_index"] = idx
        push_state(chat_id, "report_type")
        bot.send_message(chat_id, "Виберіть формат звіту:", reply_markup=archive_report_type_menu())
        return

    # Вибір місяця
    if state == "report_month_select":
        try:
            month_date = datetime.strptime(txt + "-01", "%Y-%m-%d")
            user_state[chat_id]["tmp"]["report_month"] = month_date
            push_state(chat_id, "report_type")
            bot.send_message(chat_id, "Виберіть формат звіту:", reply_markup=archive_report_type_menu())
        except:
            bot.send_message(chat_id, "❌ Невірний формат. Використайте YYYY-MM.", reply_markup=back_button())
        return

    # Вибір типу звіту
    if state == "report_type":
        report_format = txt
        tmp = user_state[chat_id]["tmp"]

        # Звіт по тижню
        if "report_week_index" in tmp:
            week = archive[tmp["report_week_index"]]
            phones = week.get("phones", [])
        # Звіт по місяцю
        elif "report_month" in tmp:
            month = tmp["report_month"]
            phones = []
            for w in archive:
                for p in w.get("phones", []):
                    p_date = datetime.strptime(p["date"].split()[0], "%d.%m.%Y")
                    if p_date.year == month.year and p_date.month == month.month:
                        phones.append(p)
        else:
            bot.send_message(chat_id, "❌ Неможливо сформувати звіт.", reply_markup=main_menu())
            clear_state(chat_id)
            return

        total = sum(float(p["price"]) for p in phones)
        text = f"📊 Звіт:\n🔢 Кількість телефонів: {len(phones)}\n💰 Загальна сума: {fmt_price(total)} грн\n\n"

        if report_format == "📱 Суми + телефони":
            for i, p in enumerate(phones, 1):
                text += f"{i}. {phone_display(p)}\n\n"

        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        clear_state(chat_id)
        return

# =======================
# СТАРТ БОТА
# =======================
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()