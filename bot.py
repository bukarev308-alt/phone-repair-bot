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

bot = TeleBot(TOKEN)
data_lock = threading.Lock()

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            return {"stores": ["It Center", "Леся", "Особисті"], "phones": [], "archive": []}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_data(d):
    with data_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

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
    kb.add("📝 Перенести тиждень в архів")
    kb.add("📑 Звіт по архіву / місяцю")
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

def archive_week_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weeks = [w["week"] for w in data.get("archive", [])]
    for w in weeks:
        kb.add(w)
    kb.add("⬅️ Назад")
    return kb

def archive_view_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔽 Показати телефони", "🔼 Відновити тиждень")
    kb.add("📤 Відновити телефон", "❌ Видалити телефон з архіву")
    kb.add("🗑 Видалити тиждень", "⬅️ Назад")
    return kb

def phones_list_keyboard(phones):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {phone_short(p)}")
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
# Тут залишається весь твій оригінальний код до архіву
# … (650+ рядків твого коду) …
# =======================

# =======================
# НОВЕ: ЗВІТ ПО АРХІВУ / МІСЯЦЮ
# =======================
@bot.message_handler(func=lambda m: m.text == "📑 Звіт по архіву / місяцю")
def report_menu(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "report_choose")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📅 Звіт по тижню", "📆 Звіт за місяць", "⬅️ Назад")
    bot.send_message(chat_id, "Оберіть тип звіту:", reply_markup=kb)

@bot.message_handler(func=lambda m: True)
def generic_handler_reports(message):
    chat_id = message.chat.id
    txt = message.text.strip() if message.text else ""
    state = current_state(chat_id)

    # -----------------------
    # Звіт по архіву/місяцю
    # -----------------------
    if state == "report_choose":
        if txt == "📅 Звіт по тижню":
            weeks = [w["week"] for w in data.get("archive", [])]
            if not weeks:
                bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
                clear_state(chat_id)
                return
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            for w in weeks:
                kb.add(w)
            kb.add("⬅️ Назад")
            push_state(chat_id, "report_week_select")
            bot.send_message(chat_id, "Оберіть тиждень для звіту:", reply_markup=kb)
            return

        elif txt == "📆 Звіт за місяць":
            push_state(chat_id, "report_month_select")
            bot.send_message(chat_id, "Введіть місяць у форматі ММ.РРРР (наприклад: 10.2025):", reply_markup=back_button())
            return

        elif txt == "⬅️ Назад":
            pop_state(chat_id)
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
            return

    # -----------------------
    # Звіт по тижню
    # -----------------------
    if state == "report_week_select":
        weeks = [w["week"] for w in data.get("archive", [])]
        if txt in weeks:
            idx = weeks.index(txt)
            week = data["archive"][idx]
            phones = week.get("phones", [])
            total = sum(p["price"] for p in phones)
            text = f"📋 Звіт за тиждень {week['week']}:\n💰 Загальна сума: {fmt_price(total)} грн\n\nТелефони:\n"
            for p in phones:
                text += f"• {phone_display(p)}\n"
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
            clear_state(chat_id)
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть тиждень зі списку.", reply_markup=archive_week_menu())
            return

    # -----------------------
    # Звіт за місяць
    # -----------------------
    if state == "report_month_select":
        try:
            month_str = txt
            month_dt = datetime.strptime(month_str, "%m.%Y")
            # збираємо всі телефони з archive та поточних
            phones_all = []
            for w in data.get("archive", []):
                for p in w.get("phones", []):
                    dt = datetime.strptime(p["date"], "%d.%m.%Y %H:%M")
                    if dt.year == month_dt.year and dt.month == month_dt.month:
                        phones_all.append(p)
            for p in data.get("phones", []):
                dt = datetime.strptime(p["date"], "%d.%m.%Y %H:%M")
                if dt.year == month_dt.year and dt.month == month_dt.month:
                    phones_all.append(p)
            if not phones_all:
                bot.send_message(chat_id, "📭 За цей місяць телефонів немає.", reply_markup=main_menu())
                clear_state(chat_id)
                return
            total = sum(p["price"] for p in phones_all)
            text = f"📋 Звіт за місяць {month_str}:\n💰 Загальна сума: {fmt_price(total)} грн\n\nТелефони:\n"
            for p in phones_all:
                text += f"• {phone_display(p)}\n"
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
            clear_state(chat_id)
        except Exception:
            bot.send_message(chat_id, "❌ Невірний формат. Введіть ММ.РРРР", reply_markup=back_button())
        return

# =======================
# СТАРТ БОТА
# =======================
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()