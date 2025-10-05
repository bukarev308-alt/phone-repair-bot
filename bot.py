import os
import json
from datetime import datetime
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)
DATA_FILE = "data.json"

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"stores": ["It Center", "Леся", "Особисті"], "phones": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# =======================
# СТАН КОРИСТУВАЧА
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
        user_state[chat_id]["stack"].pop()

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# МАПА ПОЛІВ ДЛЯ РЕДАГУВАННЯ
# =======================
FIELD_MAP = {
    "Магазин": "store",
    "Модель": "model",
    "Проблема": "problem",
    "Ціна": "price"
}

# =======================
# КНОПКИ МЕНЮ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини")
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
    kb.add(*FIELD_MAP.keys())
    kb.add("⬅️ Назад")
    return kb

def confirm_delete_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Так", "❌ Ні")
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
# ОБРОБКА МАГАЗИНІВ
# =======================
@bot.message_handler(func=lambda m: m.text == "🏪 Магазини")
def handle_stores(message):
    chat_id = message.chat.id
    text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text
    state = current_state(chat_id)

    # -----------------------
    # Назад
    # -----------------------
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        state = current_state(chat_id)
        if not state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        elif state == "add_store":
            bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())
        elif state.startswith("edit"):
            show_edit_selection(chat_id)
        return

    # -----------------------
    # Головне меню
    # -----------------------
    if txt == "📋 Переглянути телефони":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        text = "📋 <b>Список телефонів:</b>\n\n"
        for i, p in enumerate(data["phones"], 1):
            text += (f"{i}. {p['model']} ({p['store']})\n"
                     f"🔧 {p['problem']}\n"
                     f"💰 {p['price']} грн\n"
                     f"🕒 {p['date']}\n\n")
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    if txt == "📊 Підсумок":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return

        text = "📊 <b>Підсумок по магазинах:</b>\n\n"
        store_summary = {}
        total_count = 0
        total_sum = 0

        for p in data["phones"]:
            store = p["store"]
            price = p["price"]
            if store not in store_summary:
                store_summary[store] = {"count": 0, "sum": 0}
            store_summary[store]["count"] += 1
            store_summary[store]["sum"] += price
            total_count += 1
            total_sum += price

        for store, info in store_summary.items():
            text += f"🏪 {store}:\n🔢 Телефонів: {info['count']}\n💰 Сума: {info['sum']} грн\n\n"

        text += f"💼 <b>Загалом:</b>\n🔢 Телефонів: {total_count}\n💰 Сума: {total_sum} грн"
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    if txt == "✏️ Редагувати / 🗑 Видалити":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        push_state(chat_id, "edit_select")
        show_edit_selection(chat_id)
        return

    # -----------------------
    # СТАНИ ДОДАВАННЯ ТЕЛЕФОНУ
    # -----------------------
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
        elif txt in data["stores"]:
            user_state[chat_id]["tmp"]["store"] = txt
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, "Введіть модель телефону:", reply_markup=back_button())
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку або додайте новий.", reply_markup=stores_menu())
        return

    if state == "add_new_store":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"].append(store_name)
            save_data(data)
           