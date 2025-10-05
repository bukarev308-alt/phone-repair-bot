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
# МАГАЗИНИ: ДОДАТИ / РЕДАГУВАТИ / ВИДАЛИТИ
# =======================
@bot.message_handler(func=lambda m: m.text == "🏪 Магазини")
def handle_stores(message):
    chat_id = message.chat.id
    text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"{i+1}. {s}" for i, s in enumerate(data["stores"]))
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, s in enumerate(data["stores"], 1):
        kb.add(f"✏️ {i}. {s}", f"🗑 {i}. {s}")
    kb.add("➕ Додати магазин")
    kb.add("⬅️ Назад")
    push_state(chat_id, "store_menu")
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "store_menu")
def store_menu_handler(message):
    chat_id = message.chat.id
    txt = message.text

    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return

    if txt == "➕ Додати магазин":
        push_state(chat_id, "add_new_store")
        bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
        return

    if txt.startswith("✏️"):
        try:
            idx = int(txt.split()[1].replace(".", "")) - 1
            user_state[chat_id]["tmp"]["edit_store_idx"] = idx
            push_state(chat_id, "edit_store_name")
            bot.send_message(chat_id, f"Введіть нову назву магазину «{data['stores'][idx]}»:", reply_markup=back_button())
        except:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

    if txt.startswith("🗑"):
        try:
            idx = int(txt.split()[1].replace(".", "")) - 1
            store_name = data["stores"][idx]
            user_state[chat_id]["tmp"]["delete_store_idx"] = idx
            push_state(chat_id, "confirm_delete_store")
            bot.send_message(chat_id, f"Видалити магазин «{store_name}»?", reply_markup=confirm_delete_menu())
        except:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "edit_store_name")
def edit_store_name_handler(message):
    chat_id = message.chat.id
    new_name = message.text.strip()
    idx = user_state[chat_id]["tmp"]["edit_store_idx"]

    if new_name and new_name not in data["stores"]:
        old_name = data["stores"][idx]
        data["stores"][idx] = new_name
        save_data(data)
        bot.send_message(chat_id, f"✅ Магазин «{old_name}» перейменовано на «{new_name}».", reply_markup=main_menu())
        clear_state(chat_id)
    else:
        bot.send_message(chat_id, "❌ Назва пуста або вже існує.", reply_markup=back_button())

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "confirm_delete_store")
def delete_store_handler(message):
    chat_id = message.chat.id
    txt = message.text
    idx = user_state[chat_id]["tmp"]["delete_store_idx"]

    if txt == "✅ Так":
        store_name = data["stores"].pop(idx)
        save_data(data)
        bot.send_message(chat_id, f"🗑 Магазин «{store_name}» видалено.", reply_markup=main_menu())
    else:
        bot.send_message(chat_id, "❌ Скасовано.", reply_markup=main_menu())
    clear_state(chat_id)

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

def show_edit_selection(chat_id):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(data["phones"], 1):
        kb.add(f"{i}. {p['model']} ({p['store']})")
    kb.add("⬅️ Назад")
    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", reply_markup=kb)

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text
    state = current_state(chat_id)

    if txt == "⬅️ Назад":
        pop_state(chat_id)
        state = current_state(chat_id)
        if not state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        elif state == "add_store":
            bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())
        elif state and state.startswith("edit"):
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
    # ДОДАВАННЯ ТЕЛЕФОНУ
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
            bot.send_message(chat_id, f"✅ Магазин «{store_name}» додано!", reply_markup=main_menu())
            clear_state(chat_id)
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста.", reply_markup=back_button())
        pop_state(chat_id)
        return

    if state == "add_model":
        user_state[chat_id]["tmp"]["model"] = txt
        push_state(chat_id, "add_problem")
        bot.send_message(chat_id, "Опишіть проблему телефону:", reply_markup=back_button())
        return

    if state == "add_problem":
        user_state[chat_id]["tmp"]["problem"] = txt
        push_state(chat_id, "add_price")
        bot.send_message(chat_id, "Вкажіть ціну ремонту:", reply_markup=back_button())
        return

    if state == "add_price":
        try:
            price = float(txt)
            user_state[chat_id]["tmp"]["price"] = price
            phone = {
                "store": user_state[chat_id]["tmp"]["store"],
                "model": user_state[chat_id]["tmp"]["model"],
                "problem": user_state[chat_id]["tmp"]["problem"],
                "price": price,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            data["phones"].append(phone)
            save_data(data)
            bot.send_message(chat_id, "✅ Телефон додано!", reply_markup=main_menu())
            clear_state(chat_id)
        except ValueError:
            bot.send_message(chat_id, "❌ Введіть правильне число.", reply_markup=back_button())
        return

# =======================
# ЗАПУСК БОТА
# =======================
bot.infinity_polling()