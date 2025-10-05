from telebot import TeleBot, types
from flask import Flask, request
import json
import os

# =======================
# Ваш токен Telegram
# =======================
TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

# =======================
# Завантаження та збереження дани
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
# Стан користувача
# =======================
user_state = {}

def ensure_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"stack": [], "tmp": {}}

def push_state(chat_id, name):
    ensure_state(chat_id)
    user_state[chat_id]["stack"].append(name)

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
# Меню
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

# =======================
# Старт
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

# =======================
# Додавання та редагування телефонів
# =======================
@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    chat_id = message.chat.id
    txt = message.text
    state = current_state(chat_id)

    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємося в меню.", reply_markup=main_menu())
        return

    # 📱 Додати телефон
    if txt == "📱 Додати телефон":
        push_state(chat_id, "add_store")
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for s in data["stores"]:
            kb.add(s)
        kb.add("⬅️ Назад")
        bot.send_message(chat_id, "Виберіть магазин:", reply_markup=kb)
        return

    if state == "add_store":
        if txt not in data["stores"]:
            bot.send_message(chat_id, "❌ Невірний магазин", reply_markup=back_button())
            return
        user_state[chat_id]["tmp"]["store"] = txt
        push_state(chat_id, "add_model")
        bot.send_message(chat_id, "Введіть модель телефону:", reply_markup=back_button())
        return

    if state == "add_model":
        user_state[chat_id]["tmp"]["model"] = txt
        push_state(chat_id, "add_problem")
        bot.send_message(chat_id, "Опишіть проблему:", reply_markup=back_button())
        return

    if state == "add_problem":
        user_state[chat_id]["tmp"]["problem"] = txt
        push_state(chat_id, "add_price")
        bot.send_message(chat_id, "Введіть ціну ремонту:", reply_markup=back_button())
        return

    if state == "add_price":
        try:
            price = float(txt)
        except:
            bot.send_message(chat_id, "❌ Введіть число.", reply_markup=back_button())
            return
        user_state[chat_id]["tmp"]["price"] = price
        phone = {
            "store": user_state[chat_id]["tmp"]["store"],
            "model": user_state[chat_id]["tmp"]["model"],
            "problem": user_state[chat_id]["tmp"]["problem"],
            "price": price
        }
        data["phones"].append(phone)
        save_data(data)
        bot.send_message(chat_id, f"✅ Телефон {phone['model']} додано!", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # 📋 Переглянути телефони
    if txt == "📋 Переглянути телефони":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Список порожній.", reply_markup=main_menu())
            return
        msg = ""
        for i, p in enumerate(data["phones"], 1):
            msg += f"{i}. [{p['store']}] {p['model']} - {p['problem']} ({p['price']}₴)\n"
        bot.send_message(chat_id, msg, reply_markup=main_menu())
        return

    # ✏️ Редагувати / 🗑 Видалити
    if txt == "✏️ Редагувати / 🗑 Видалити":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Список порожній.", reply_markup=main_menu())
            return
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for i, p in enumerate(data["phones"], 1):
            kb.add(f"{i}. {p['model']}")
        kb.add("⬅️ Назад")
        push_state(chat_id, "edit_select")
        bot.send_message(chat_id, "Оберіть телефон для редагування/видалення:", reply_markup=kb)
        return

    if state == "edit_select":
        try:
            index = int(txt.split(".")[0]) - 1
            phone = data["phones"][index]
            user_state[chat_id]["tmp"]["edit_index"] = index
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            kb.add("Магазин", "Модель")
            kb.add("Проблема", "Ціна")
            kb.add("🗑 Видалити", "⬅️ Назад")
            push_state(chat_id, "edit_field")
            bot.send_message(chat_id, f"Оберіть дію для {phone['model']}:", reply_markup=kb)
        except:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

    if state == "edit_field":
        index = user_state[chat_id]["tmp"]["edit_index"]
        phone = data["phones"][index]
        field_map = {
            "Магазин": "store",
            "Модель": "model",
            "Проблема": "problem",
            "Ціна": "price"
        }
        if txt in field_map:
            user_state[chat_id]["tmp"]["edit_field"] = field_map[txt]
            push_state(chat_id, "edit_input")
            bot.send_message(chat_id, f"Введіть нове значення для {txt}:", reply_markup=back_button())
            return
        elif txt == "🗑 Видалити":
            data["phones"].pop(index)
            save_data(data)
            bot.send_message(chat_id, "✅ Телефон видалено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        else:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

    if state == "edit_input":
        index = user_state[chat_id]["tmp"]["edit_index"]
        field = user_state[chat_id]["tmp"]["edit_field"]
        if field == "price":
            try:
                value = float(txt)
            except:
                bot.send_message(chat_id, "❌ Введіть число.", reply_markup=back_button())
                return
        else:
            value = txt
        data["phones"][index][field] = value
        save_data(data)
        bot.send_message(chat_id, f"✅ {field} оновлено!", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # 📊 Підсумок
    if txt == "📊 Підсумок":
        total = sum(p["price"] for p in data["phones"])
        count = len(data["phones"])
        bot.send_message(chat_id, f"📊 Кількість телефонів: {count}\n💰 Загальна сума: {total}₴", reply_markup=main_menu())
        return

    # 🏪 Магазини
    if txt == "🏪 Магазини":
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        for s in data["stores"]:
            kb.add(s)
        kb.add("➕ Додати новий магазин")
        kb.add("⬅️ Назад")
        push_state(chat_id, "stores_menu")
        bot.send_message(chat_id, "Магазини:", reply_markup=kb)
        return

    if state == "stores_menu":
        if txt == "➕ Додати новий магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt in data["stores"]:
            bot.send_message(chat_id, f"Магазин: {txt}", reply_markup=main_menu())
            return
        else:
            bot.send_message(chat_id, "❌ Невірна опція", reply_markup=back_button())
            return

    if state == "add_new_store":
        data["stores"].append(txt)
        save_data(data)
        bot.send_message(chat_id, f"✅ Магазин {txt} додано!", reply_markup=main_menu())
        clear_state(chat_id)
        return

# =======================
# Webhook
# =======================
@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    json_str = request.get_data().decode("utf-8")
    update = types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return ""