import telebot
from telebot import types
import json
import os

# ==================== Налаштування ====================
TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
DATA_FILE = "data.json"
bot = telebot.TeleBot(TOKEN)

# ==================== Завантаження даних ====================
if os.path.exists(DATA_FILE):
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {"stores": {}}

def save_data():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# ==================== Типи ремонту ====================
REPAIR_TYPES = ["🔧 Замінити екран", "🔋 Заміна батареї", "🧩 Інше"]

# ==================== Клавіатури ====================
def main_markup():
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🏪 Магазини", callback_data="stores"))
    markup.add(types.InlineKeyboardButton("📱 Телефони", callback_data="phones"))
    markup.add(types.InlineKeyboardButton("📊 Підсумки", callback_data="summary"))
    return markup

def stores_markup():
    markup = types.InlineKeyboardMarkup()
    for store in data["stores"]:
        markup.add(types.InlineKeyboardButton(f"🗑️ {store}", callback_data=f"delstore|{store}"))
    markup.add(types.InlineKeyboardButton("➕ Додати магазин", callback_data="addstore"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return markup

def phones_markup():
    markup = types.InlineKeyboardMarkup()
    for store in data["stores"]:
        markup.add(types.InlineKeyboardButton(f"📂 {store}", callback_data=f"store|{store}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="back"))
    return markup

def store_phones_markup(store):
    markup = types.InlineKeyboardMarkup()
    for i, phone in enumerate(data["stores"][store]):
        text = f"{phone['name']} {phone['model']} {phone['problem']} {phone['type']} 💰{phone['price']}₴"
        markup.add(types.InlineKeyboardButton(f"✏️ {text}", callback_data=f"editphone|{store}|{i}"))
        markup.add(types.InlineKeyboardButton(f"🗑️ {text}", callback_data=f"delphone|{store}|{i}"))
    markup.add(types.InlineKeyboardButton("➕ Додати телефон", callback_data=f"addphone|{store}"))
    markup.add(types.InlineKeyboardButton("⬅️ Назад", callback_data="phones"))
    return markup

def repair_type_markup():
    markup = types.InlineKeyboardMarkup()
    for rtype in REPAIR_TYPES:
        markup.add(types.InlineKeyboardButton(rtype, callback_data=f"rtype|{rtype}"))
    return markup

# ==================== Старт ====================
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "👋 Ласкаво просимо до персонального бота управління телефонами!", reply_markup=main_markup())

# ==================== Callback Handler ====================
@bot.callback_query_handler(func=lambda call: True)
def callback_inline(call):
    try:
        if call.data == "back":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="🏠 Головне меню", reply_markup=main_markup())
        elif call.data == "stores":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="🏪 Магазини", reply_markup=stores_markup())
        elif call.data.startswith("delstore|"):
            _, store = call.data.split("|")
            if store in data["stores"]:
                del data["stores"][store]
                save_data()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="🏪 Магазини", reply_markup=stores_markup())
        elif call.data == "addstore":
            msg = bot.send_message(call.message.chat.id, "Введіть назву нового магазину:")
            bot.register_next_step_handler(msg, add_store_step)
        elif call.data == "phones":
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text="📱 Виберіть магазин", reply_markup=phones_markup())
        elif call.data.startswith("store|"):
            _, store = call.data.split("|")
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"📱 Телефони у {store}", reply_markup=store_phones_markup(store))
        elif call.data.startswith("addphone|"):
            _, store = call.data.split("|")
            msg = bot.send_message(call.message.chat.id, "Введіть назву телефону:")
            bot.register_next_step_handler(msg, add_phone_name, store)
        elif call.data.startswith("delphone|"):
            _, store, idx = call.data.split("|")
            idx = int(idx)
            data["stores"][store].pop(idx)
            save_data()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=f"📱 Телефони у {store}", reply_markup=store_phones_markup(store))
        elif call.data.startswith("editphone|"):
            _, store, idx = call.data.split("|")
            idx = int(idx)
            msg = bot.send_message(call.message.chat.id, f"Редагуємо {data['stores'][store][idx]['name']} {data['stores'][store][idx]['model']}\nВведіть нову ціну:")
            bot.register_next_step_handler(msg, edit_phone_price, store, idx)
        elif call.data == "summary":
            summary_text = get_summary()
            bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                                  text=summary_text, reply_markup=main_markup())
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Сталася помилка: {str(e)}")

# ==================== Функції ====================
def add_store_step(message):
    name = message.text.strip()
    if name not in data["stores"]:
        data["stores"][name] = []
        save_data()
    bot.send_message(message.chat.id, f"🏪 Магазин '{name}' додано!", reply_markup=stores_markup())

def add_phone_name(message, store):
    name = message.text.strip()
    msg = bot.send_message(message.chat.id, "Введіть модель телефону:")
    bot.register_next_step_handler(msg, add_phone_model, store, name)

def add_phone_model(message, store, name):
    model = message.text.strip()
    msg = bot.send_message(message.chat.id, "Опишіть проблему телефону:")
    bot.register_next_step_handler(msg, add_phone_problem, store, name, model)

def add_phone_problem(message, store, name, model):
    problem = message.text.strip()
    markup = types.InlineKeyboardMarkup()
    for rtype in REPAIR_TYPES:
        markup.add(types.InlineKeyboardButton(rtype, callback_data=f"rtypeadd|{store}|{name}|{model}|{problem}|{rtype}"))
    bot.send_message(message.chat.id, "Виберіть тип ремонту:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("rtypeadd|"))
def add_phone_type(call):
    _, store, name, model, problem, rtype = call.data.split("|")
    msg = bot.send_message(call.message.chat.id, "Введіть ціну ремонту:")
    bot.register_next_step_handler(msg, add_phone_price, store, name, model, problem, rtype)

def add_phone_price(message, store, name, model, problem, rtype):
    try:
        price = int(message.text.strip())
    except:
        price = 0
    data["stores"][store].append({
        "name": name,
        "model": model,
        "problem": problem,
        "type": rtype,
        "price": price
    })
    save_data()
    bot.send_message(message.chat.id, f"📱 Телефон {name} {model} додано!", reply_markup=store_phones_markup(store))

def edit_phone_price(message, store, idx):
    try:
        price = int(message.text.strip())
        data["stores"][store][idx]["price"] = price
        save_data()
        bot.send_message(message.chat.id, "💰 Ціна оновлена!", reply_markup=store_phones_markup(store))
    except:
        bot.send_message(message.chat.id, "❌ Невірне значення!", reply_markup=store_phones_markup(store))

def get_summary():
    total = 0
    text = "📊 Підсумки:\n"
    for store, phones in data["stores"].items():
        store_total = sum(p["price"] for p in phones)
        total += store_total
        text += f"\n🏪 {store} - {len(phones)} телефонів, {store_total}₴"
    text += f"\n\n💵 Загальна сума: {total}₴"
    return text

# ==================== Запуск бота ====================
bot.infinity_polling()