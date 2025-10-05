import telebot
from telebot import types
import json

# === ТВОЇ НАЛАШТУВАННЯ ===
TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
ALLOWED_USER_ID = 123456789  # <- твій Telegram ID
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

# === Перевірка користувача ===
def is_allowed(message):
    return message.from_user.id == ALLOWED_USER_ID

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
        markup.add(f"✏️ {idx} {text}", f"🗑️ {idx} {text}")
    markup.row("➕ Додати телефон", "⬅️ Назад")
    return markup

# === Підсумки ===
def summary_text():
    total_count = 0
    total_sum = 0
    msg = ""
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
    if not is_allowed(message):
        return

    text = message.text

    if text == "/start":
        bot.send_message(message.chat.id, "Вибери дію:", reply_markup=main_menu())
    
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
        bot.send_message(message.chat.id, f"Телефони у {store_name}:", reply_markup=store_phones_menu(store_name))

    elif text.startswith("➕ Додати телефон"):
        bot.send_message(message.chat.id, "Введи дані у форматі:\nНазва, Модель, Проблема, Ціна")
        bot.register_next_step_handler(message, lambda m: add_phone_step(m, last_store))

    # Редагування або видалення телефону
    elif text.startswith("✏️") or text.startswith("🗑️"):
        try:
            parts = text.split(" ", 2)
            action = parts[0]
            idx = int(parts[1])
            store_name = last_store  # останній вибраний магазин
            if action == "🗑️":
                del data["stores"][store_name][idx]
                save_data()
                bot.send_message(message.chat.id, "Телефон видалено ✅", reply_markup=store_phones_menu(store_name))
            elif action == "✏️":
                phone = data["stores"][store_name][idx]
                msg = bot.send_message(message.chat.id, f"Редагуй телефон у форматі:\nНазва, Модель, Проблема, Ціна\nПоточні: {phone}")
                bot.register_next_step_handler(msg, lambda m: edit_phone_step(m, store_name, idx))
        except Exception as e:
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
last_store = ""  # для запам’ятовування останнього вибраного магазину
bot.infinity_polling()