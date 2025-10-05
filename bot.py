import json
from telebot import TeleBot, types

# ===== Токен бота =====
TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)

DATA_FILE = "data.json"

# ===== Завантаження та збереження даних =====
def load_data():
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"phones": [], "stores": ["It Center", "Леся", "Особисті"]}

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

data = load_data()

# ===== Головне меню =====
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("Додати телефон", "Список телефонів")
    markup.add("Додати магазин", "Підсумок")
    return markup

# ===== Додавання телефону =====
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Вітаю! Обери дію:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text=="Додати телефон")
def add_phone_step1(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for store in data["stores"]:
        markup.add(store)
    markup.add("Назад")
    msg = bot.send_message(message.chat.id, "Вибери магазин:", reply_markup=markup)
    bot.register_next_step_handler(msg, add_phone_step2)

def add_phone_step2(message):
    if message.text == "Назад":
        bot.send_message(message.chat.id, "Головне меню:", reply_markup=main_menu())
        return
    store = message.text
    msg = bot.send_message(message.chat.id, "Введи модель телефону:")
    bot.register_next_step_handler(msg, lambda m: add_phone_step3(m, store))

def add_phone_step3(message, store):
    model = message.text
    msg = bot.send_message(message.chat.id, "Введи проблему телефону:")
    bot.register_next_step_handler(msg, lambda m: add_phone_step4(m, store, model))

def add_phone_step4(message, store, model):
    problem = message.text
    msg = bot.send_message(message.chat.id, "Введи ціну ремонту:")
    bot.register_next_step_handler(msg, lambda m: add_phone_step5(m, store, model, problem))

def add_phone_step5(message, store, model, problem):
    try:
        price = float(message.text)
    except:
        msg = bot.send_message(message.chat.id, "Введи число для ціни:")
        bot.register_next_step_handler(msg, lambda m: add_phone_step5(m, store, model, problem))
        return
    data["phones"].append({"store": store, "model": model, "problem": problem, "price": price})
    save_data(data)
    bot.send_message(message.chat.id, f"Телефон {model} додано до {store} за {price}₴", reply_markup=main_menu())

# ===== Додати магазин =====
@bot.message_handler(func=lambda m: m.text=="Додати магазин")
def add_store(message):
    msg = bot.send_message(message.chat.id, "Введи назву нового магазину:")
    bot.register_next_step_handler(msg, save_store)

def save_store(message):
    store_name = message.text
    if store_name not in data["stores"]:
        data["stores"].append(store_name)
        save_data(data)
        bot.send_message(message.chat.id, f"Магазин {store_name} додано!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "Такий магазин вже існує.", reply_markup=main_menu())

# ===== Список телефонів + редагування/видалення =====
@bot.message_handler(func=lambda m: m.text=="Список телефонів")
def list_phones(message):
    if not data["phones"]:
        bot.send_message(message.chat.id, "Телефонів ще немає.", reply_markup=main_menu())
        return
    markup = types.InlineKeyboardMarkup()
    for i, p in enumerate(data["phones"]):
        btn = types.InlineKeyboardButton(f"{i+1}. {p['model']} ({p['store']})", callback_data=f"view_{i}")
        markup.add(btn)
    bot.send_message(message.chat.id, "Телефони:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_phone(call):
    idx = int(call.data.split("_")[1])
    phone = data["phones"][idx]
    text = f"Магазин: {phone['store']}\nМодель: {phone['model']}\nПроблема: {phone['problem']}\nЦіна: {phone['price']}₴"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Видалити", callback_data=f"delete_{idx}"))
    markup.add(types.InlineKeyboardButton("Назад", callback_data="back_main"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_phone(call):
    idx = int(call.data.split("_")[1])
    removed = data["phones"].pop(idx)
    save_data(data)
    bot.answer_callback_query(call.id, f"{removed['model']} видалено!")
    list_phones(call.message)

@bot.callback_query_handler(func=lambda call: call.data=="back_main")
def back_main(call):
    bot.send_message(call.message.chat.id, "Головне меню:", reply_markup=main_menu())

# ===== Підсумок =====
@bot.message_handler(func=lambda m: m.text=="Підсумок")
def summary(message):
    total = sum(p["price"] for p in data["phones"])
    count = len(data["phones"])
    bot.send_message(message.chat.id, f"Кількість телефонів: {count}\nЗагальна сума: {total}₴", reply_markup=main_menu())

# ===== Запуск бота =====
bot.infinity_polling()