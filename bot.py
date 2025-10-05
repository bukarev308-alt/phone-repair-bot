import telebot
from telebot import types
import json

TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
DATA_FILE = "data.json"
bot = telebot.TeleBot(TOKEN)

# Завантаження даних
try:
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
except:
    data = {"stores": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

# Головне меню
def main_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏪 Магазини", callback_data="stores"))
    markup.add(types.InlineKeyboardButton("📱 Телефони", callback_data="phones"))
    markup.add(types.InlineKeyboardButton("📊 Підсумки", callback_data="summary"))
    return markup

# Меню магазинів
def stores_markup():
    markup = types.InlineKeyboardMarkup()
    for store in data["stores"]:
        markup.add(types.InlineKeyboardButton(f"🗑️ {store}", callback_data=f"delstore|{store}"))
    markup.add(types.InlineKeyboardButton("➕ Додати магазин", callback_data="addstore"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return markup

# Меню вибору магазинів для телефонів
def phones_markup():
    markup = types.InlineKeyboardMarkup()
    for store in data["stores"]:
        markup.add(types.InlineKeyboardButton(f"📂 {store}", callback_data=f"store|{store}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return markup

# Меню телефонів у магазині
def store_phones_markup(store):
    markup = types.InlineKeyboardMarkup()
    for i, phone in enumerate(data["stores"][store]):
        text = f"{phone['name']} {phone['model']} 💰{phone['price']}₴"
        markup.add(types.InlineKeyboardButton(f"✏️ Редагувати {text}", callback_data=f"editphone|{store}|{i}"))
        markup.add(types.InlineKeyboardButton(f"🗑️ Видалити {text}", callback_data=f"delphone|{store}|{i}"))
    markup.add(types.InlineKeyboardButton("➕ Додати телефон", callback_data=f"addphone|{store}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="phones"))
    return markup

# Підсумки
def summary_text():
    total_count = 0
    total_sum = 0
    msg = "📊 Підсумки по магазинах:\n\n"
    for store, phones in data["stores"].items():
        count = len(phones)
        summ = sum(p['price'] for p in phones)
        total_count += count
        total_sum += summ
        msg += f"🏪 {store}: {count} телефонів, 💰{summ}₴\n"
    msg += f"\n📈 Загалом: {total_count} телефонів, 💰{total_sum}₴"
    return msg

# === Хендлер команд ===
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Вітаю! Обери дію:", reply_markup=main_markup())

# === Callback Query Handler ===
@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    global temp_store, temp_phone_idx
    data_text = call.data.split("|")
    
    if call.data == "back":
        bot.edit_message_text("Головне меню:", call.message.chat.id, call.message.message_id, reply_markup=main_markup())
    
    elif call.data == "stores":
        bot.edit_message_text("Магазини:", call.message.chat.id, call.message.message_id, reply_markup=stores_markup())
    
    elif call.data == "phones":
        bot.edit_message_text("Оберіть магазин:", call.message.chat.id, call.message.message_id, reply_markup=phones_markup())
    
    elif call.data == "summary":
        bot.edit_message_text(summary_text(), call.message.chat.id, call.message.message_id, reply_markup=main_markup())
    
    # Додати магазин
    elif call.data == "addstore":
        msg = bot.send_message(call.message.chat.id, "Введи назву нового магазину:")
        bot.register_next_step_handler(msg, add_store_step)
    
    # Видалити магазин
    elif data_text[0] == "delstore":
        store = data_text[1]
        if store in data["stores"]:
            del data["stores"][store]
            save_data()
            bot.edit_message_text(f"Магазин '{store}' видалено ✅", call.message.chat.id, call.message.message_id, reply_markup=stores_markup())
    
    # Вибір магазину для перегляду телефонів
    elif data_text[0] == "store":
        store = data_text[1]
        temp_store = store
        bot.edit_message_text(f"Телефони у {store}:", call.message.chat.id, call.message.message_id, reply_markup=store_phones_markup(store))
    
    # Додати телефон
    elif data_text[0] == "addphone":
        store = data_text[1]
        temp_store = store
        msg = bot.send_message(call.message.chat.id, "Введи дані телефону у форматі:\nНазва, Модель, Проблема, Ціна")
        bot.register_next_step_handler(msg, add_phone_step)
    
    # Видалити телефон
    elif data_text[0] == "delphone":
        store = data_text[1]
        idx = int(data_text[2])
        del data["stores"][store][idx]
        save_data()
        bot.edit_message_text(f"Телефон видалено ✅", call.message.chat.id, call.message.message_id, reply_markup=store_phones_markup(store))
    
    # Редагувати телефон
    elif data_text[0] == "editphone":
        store = data_text[1]
        idx = int(data_text[2])
        temp_store = store
        temp_phone_idx = idx
        phone = data["stores"][store][idx]
        msg = bot.send_message(call.message.chat.id, f"Редагуй телефон у форматі:\nНазва, Модель, Проблема, Ціна\nПоточні: {phone}")
        bot.register_next_step_handler(msg, edit_phone_step)

# === Функції додавання/редагування ===
def add_store_step(message):
    name = message.text.strip()
    if name and name not in data["stores"]:
        data["stores"][name] = []
        save_data()
        bot.send_message(message.chat.id, f"Магазин '{name}' додано ✅", reply_markup=stores_markup())
    else:
        bot.send_message(message.chat.id, "Магазин вже існує або пустий ❌", reply_markup=stores_markup())

def add_phone_step(message):
    try:
        name, model, problem, price = [x.strip() for x in message.text.split(",")]
        price = int(price)
        data["stores"][temp_store].append({"name": name, "model": model, "problem": problem, "price": price})
        save_data()
        bot.send_message(message.chat.id, "Телефон додано ✅", reply_markup=store_phones_markup(temp_store))
    except:
        bot.send_message(message.chat.id, "Помилка формату ❌", reply_markup=store_phones_markup(temp_store))

def edit_phone_step(message):
    try:
        name, model, problem, price = [x.strip() for x in message.text.split(",")]
        price = int(price)
        data["stores"][temp_store][temp_phone_idx] = {"name": name, "model": model, "problem": problem, "price": price}
        save_data()
        bot.send_message(message.chat.id, "Телефон відредаговано ✅", reply_markup=store_phones_markup(temp_store))
    except:
        bot.send_message(message.chat.id, "Помилка формату ❌", reply_markup=store_phones_markup(temp_store))

# Запуск
temp_store = ""
temp_phone_idx = 0
bot.infinity_polling()