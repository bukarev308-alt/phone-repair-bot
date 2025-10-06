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
# МЕНЮ
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
    kb.add("Магазин", "Модель", "Проблема", "Ціна")
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
# ДОДАВАННЯ ТЕЛЕФОНУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

# =======================
# РЕДАГУВАННЯ / ВИДАЛЕННЯ ТЕЛЕФОНІВ
# =======================
@bot.message_handler(func=lambda m: m.text == "✏️ Редагувати / 🗑 Видалити")
def edit_phone_start(message):
    chat_id = message.chat.id
    if not data["phones"]:
        bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(data["phones"], 1):
        kb.add(f"{i}. {p['model']} ({p['store']})")
    kb.add("⬅️ Назад")
    push_state(chat_id, "edit_select")
    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", reply_markup=kb)

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text
    state = current_state(chat_id)

    # -----------------------
    # КНОПКИ ГОЛОВНОГО МЕНЮ
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

    elif txt == "📊 Підсумок":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        total = sum(p["price"] for p in data["phones"])
        count = len(data["phones"])
        stores_summary = {}
        for p in data["phones"]:
            stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
        store_text = "\n".join(f"• {s}: {v} грн" for s, v in stores_summary.items())
        bot.send_message(chat_id,
                         f"📊 Підсумок:\n🔢 Кількість телефонів: {count}\n💰 Загальна сума: {total} грн\n\n<b>По магазинах:</b>\n{store_text}",
                         parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "🏪 Магазини":
        text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    # -----------------------
    # НАЗАД
    # -----------------------
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        state = current_state(chat_id)
        if not state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return

    # =======================
    # ДОДАВАННЯ ТЕЛЕФОНУ
    # =======================
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt in data["stores"]:
            user_state[chat_id]["tmp"]["store"] = txt
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, "Введіть модель телефону:", reply_markup=back_button())
            return
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
    # РЕДАГУВАННЯ / ВИДАЛЕННЯ
    # =======================
    field_map = {"Магазин": "store", "Модель": "model", "Проблема": "problem", "Ціна": "price"}

    if state == "edit_select":
        try:
            idx = int(txt.split(".")[0]) - 1
            if 0 <= idx < len(data["phones"]):
                user_state[chat_id]["tmp"]["edit_idx"] = idx
                push_state(chat_id, "edit_action")
                bot.send_message(chat_id, "Обрати дію:", reply_markup=edit_action_menu())
            else:
                bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        except:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

    if state == "edit_action":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        if txt == "✏️ Редагувати":
            push_state(chat_id, "edit_field")
            bot.send_message(chat_id, "Що редагуємо?", reply_markup=edit_field_menu())
        elif txt == "🗑 Видалити":
            push_state(chat_id, "confirm_delete")
            bot.send_message(chat_id, f"Видалити {data['phones'][idx]['model']}?", reply_markup=confirm_delete_menu())
        return

    if state == "edit_field":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        user_state[chat_id]["tmp"]["field"] = txt
        push_state(chat_id, "edit_enter")
        bot.send_message(chat_id, f"Введіть нове значення для {txt}:", reply_markup=back_button())
        return

    if state == "edit_enter":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        field = user_state[chat_id]["tmp"]["field"]
        value = txt
        if field == "Ціна":
            try:
                value = float(value)
            except:
                bot.send_message(chat_id, "❌ Введіть число.", reply_markup=back_button())
                return
        elif field == "Магазин":
            if value not in data["stores"]:
                data["stores"].append(value)
        key = field_map[field]
        data["phones"][idx][key] = value
        save_data(data)
        bot.send_message(chat_id, f"✅ {field} оновлено!", reply_markup=main_menu())
        clear_state(chat_id)
        return

    if state == "confirm_delete":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        if txt == "✅ Так":
            removed = data["phones"].pop(idx)
            save_data(data)
            bot.send_message(chat_id, f"🗑 Телефон {removed['model']} видалено!", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❌ Скасовано.", reply_markup=main_menu())
        clear_state(chat_id)
        return

# =======================
# СТАРТ БОТА
# =======================
bot.infinity_polling()