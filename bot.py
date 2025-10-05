import telebot
from telebot import types
import json

# === ТВОЇ НАЛАШТУВАННЯ ===
TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
DATA_FILE = "data.json"

bot = telebot.TeleBot(TOKEN)

# === Завантаження даних ===
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except:
    data = {"stores": {}}

# === Збереження даних ===
def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# === Головне меню ===
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🏪 Магазини", "📱 Телефони")
    markup.row("📊 Підсумки")
    return markup

# === Магазини меню ===
def stores_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for store in data["stores"]:
        markup.add(f"🗑️ Видалити {store}")
    markup.row("➕ Додати магазин", "⬅️ Назад")
    return markup

# === Телефони меню (список магазинів) ===
def phones_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for store in data["stores"]:
        markup.add(f"📂 {store}")
    markup.row("⬅️ Назад")
    return markup

# === Телефони магазину (для редагування/видалення) ===
def store_phones_menu(store_name):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    phones = data["stores"].get(store_name, [])
    for idx, phone in enumerate(phones):
        text = f"{phone['name']} {phone['model']} 💰 {phone['price']} грн"
        markup.add(f"✏️ Редагувати {idx} {text}", f"🗑️ Видалити {idx} {text}")
    markup.row("➕ Додати телефон", "⬅️ Назад")
    return markup

# === Підсумки ===
def summary_text():
    total_count = 0
    total_sum = 0
    msg = "📊 Підсумки по магазинах:\n\n"
    for store, phones in data["stores"].items():
        count = len(phones)
        summ = sum([p["price"] for p in phones])
        total_count += count
        total_sum += summ
        msg += f"🏪 {store}: {count} телефонів, 💰 {summ} грн\n"
    msg += f"\n📈 Загалом: {total_count} телефонів, 💰 {total_sum} грн"
    return msg

# === Обробка повідомлень ===
@bot.message_handler(func=lambda m: True)
def handle_message(message):
    text = message.text
    global last_store

    if text == "/start":
        bot.send_message(message.chat.id, "Вітаю! Обери дію:", reply_markup=main_menu())
    
    # Магазини
    elif text == "🏪 Магазини":
        bot.send_message(message.chat.id, "Магазини:", reply_markup=stores_menu())
    
    elif text.startswith("➕ Додати магазин"):
        msg = bot.send_message(message.chat.id, "Введи назву нового магазину:")
        bot.register_next_step_handler(msg, add_store)
    
    elif text.startswith("🗑️ Видалити "):
        store_name = text.replace("🗑️ Видалити ", "")
        if store_name in data["stores"]:
            del data["stores"][store_name]
            save_data()
            bot.send_message(message.chat.id, f"Магазин '{store_name}' видалено ✅", reply_markup=stores_menu())
        else:
            bot.send_message(message.chat.id, "Магазин не знайдено ❌", reply_markup=stores_menu())

    # Телефони
    elif text == "📱 Телефони":
        bot.send_message(message.chat.id, "Оберіть магазин:", reply_markup=phones_menu())

    elif text.startswith("📂 "):
        store_name = text.replace("📂 ", "")
        last_store = store_name
        bot.send_message(message.chat.id, f"Телефони у {store_name}:", reply_markup=store_phones_menu(store_name))

    elif text.startswith("➕ Додати телефон"):
        msg = bot.send_message(message.chat.id, "Введи дані у форматі:\nНазва, Модель, Проблема, Ціна")
        bot.register_next_step_handler(msg, lambda m: add_phone_step(m, last_store))

    # Редагування або видалення телефону
    elif text.startswith("✏️ Редагувати") or text.startswith("🗑️ Видалити"):
        try:
            parts = text.split(" ", 3)
            action = parts[0] + " " + parts[1]
            idx = int(parts[2])
            store_name = last_store
            if action == "🗑️ Видалити":
                del data["stores"][store_name][idx]
                save_data()
                bot.send_message(message.chat.id, "Телефон видалено ✅", reply_markup=store_phones_menu(store_name))
            elif action == "✏️ Редагувати":
                phone = data["stores"][store_name][idx]
                msg = bot.send_message(message.chat.id, f"Редагуй телефон у форматі:\nНазва, Модель, Проблема, Ціна\nПоточні: {phone}")
                bot.register_next_step_handler(msg, lambda m: edit_phone_step(m, store_name, idx))
        except:
            bot.send_message(message.chat.id, "Помилка ❌", reply_markup=phones_menu())

    # Підсумки
    elif text == "📊 Підсумки":
        bot.send_message(message.chat.id, summary_text(), reply_markup=main_menu())
    
    # Назад
    elif text == "⬅️ Назад":
        bot.send_message(message.chat.id, "Повернувся в головне меню:", reply_markup=main_menu())
    
    else:
        bot.send_message(message.chat.id, "Невідома команда ❌", reply_markup=main_menu())

# === Додавання магазину ===
def add_store(message):
    store_name = message.text.strip()
    if store_name and store_name not in data["stores"]:
        data["stores"][store_name] = []
        save_data()
        bot.send_message(message.chat.id, f"Магазин '{store_name}' додано ✅", reply_markup=stores_menu())
    else:
        bot.send_message(message.chat.id, "Магазин вже існує або пустий ❌", reply_markup=stores_menu())

# === Додавання телефону ===
def add_phone_step(message, store_name):
    try:
        name, model, problem, price = [x.strip() for x in message.text.split(",")]
        price = int(price)
        data["stores"][store_name].append({
            "name": name,
            "model": model,
            "problem": problem,
            "price": price
        })
        save_data()
        bot.send_message(message.chat.id, "Телефон додано ✅", reply_markup=store_phones_menu(store_name))
    except:
        bot.send_message(message.chat.id, "Помилка формату ❌", reply_markup=store_phones_menu(store_name))

# === Редагування телефону ===
def edit_phone_step(message, store_name, idx):
    try:
        name, model, problem, price = [x.strip() for x in message.text.split(",")]
        price = int(price)
        data["stores"][store_name][idx] = {
            "name": name,
            "model": model,
            "problem": problem,
            "price": price
        }
        save_data()
        bot.send_message(message.chat.id, "Телефон відредаговано ✅", reply_markup=store_phones_menu(store_name))
    except:
        bot.send_message(message.chat.id, "Помилка формату ❌", reply_markup=store_phones_menu(store_name))

# === Запуск бота ===
last_store = ""
bot.infinity_polling()