import json
from telebot import TeleBot, types

TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)

DATA_FILE = "data.json"

# ===================== Завантаження та збереження даних =====================
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

# ===================== Головне меню =====================
def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("📱 Додати телефон", "📋 Список телефонів")
    markup.add("🏬 Додати магазин", "🗑️ Видалити магазин")
    markup.add("📊 Підсумок")
    return markup

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Вітаю! Обери дію:", reply_markup=main_menu())

# ===================== Додавання телефону =====================
@bot.message_handler(func=lambda m: m.text=="📱 Додати телефон")
def add_phone_step1(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for store in data["stores"]:
        markup.add(f"🏪 {store}")
    markup.add("↩️ Назад")
    msg = bot.send_message(message.chat.id, "Вибери магазин:", reply_markup=markup)
    bot.register_next_step_handler(msg, add_phone_step2)

def add_phone_step2(message):
    if message.text=="↩️ Назад":
        bot.send_message(message.chat.id, "Головне меню:", reply_markup=main_menu())
        return
    store = message.text.replace("🏪 ", "")
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
    bot.send_message(message.chat.id, f"✅ Телефон {model} додано до {store} за {price}₴", reply_markup=main_menu())

# ===================== Додавання магазину =====================
@bot.message_handler(func=lambda m: m.text=="🏬 Додати магазин")
def add_store(message):
    msg = bot.send_message(message.chat.id, "Введи назву нового магазину:")
    bot.register_next_step_handler(msg, save_store)

def save_store(message):
    store_name = message.text
    if store_name not in data["stores"]:
        data["stores"].append(store_name)
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Магазин {store_name} додано!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "⚠️ Такий магазин вже існує.", reply_markup=main_menu())

# ===================== Видалення магазину =====================
@bot.message_handler(func=lambda m: m.text=="🗑️ Видалити магазин")
def delete_store_menu(message):
    if not data["stores"]:
        bot.send_message(message.chat.id, "Магазинів немає.", reply_markup=main_menu())
        return
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True)
    for store in data["stores"]:
        markup.add(f"🗑️ {store}")
    markup.add("↩️ Назад")
    msg = bot.send_message(message.chat.id, "Вибери магазин для видалення:", reply_markup=markup)
    bot.register_next_step_handler(msg, delete_store_step)

def delete_store_step(message):
    if message.text=="↩️ Назад":
        bot.send_message(message.chat.id, "Головне меню:", reply_markup=main_menu())
        return
    store_name = message.text.replace("🗑️ ", "")
    if store_name in data["stores"]:
        data["stores"].remove(store_name)
        # Видалити телефони цього магазину
        data["phones"] = [p for p in data["phones"] if p["store"]!=store_name]
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Магазин {store_name} видалено разом з його телефонами!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "⚠️ Щось пішло не так.", reply_markup=main_menu())

# ===================== Список телефонів =====================
@bot.message_handler(func=lambda m: m.text=="📋 Список телефонів")
def list_phones(message):
    if not data["phones"]:
        bot.send_message(message.chat.id, "Телефонів ще немає.", reply_markup=main_menu())
        return
    markup = types.InlineKeyboardMarkup()
    for i, p in enumerate(data["phones"]):
        btn = types.InlineKeyboardButton(f"📱 {p['model']} ({p['store']})", callback_data=f"view_{i}")
        markup.add(btn)
    bot.send_message(message.chat.id, "Телефони:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("view_"))
def view_phone(call):
    idx = int(call.data.split("_")[1])
    phone = data["phones"][idx]
    text = f"🏪 {phone['store']}\n📱 {phone['model']}\n⚠️ {phone['problem']}\n💰 {phone['price']}₴"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✏️ Редагувати", callback_data=f"edit_{idx}"))
    markup.add(types.InlineKeyboardButton("🗑️ Видалити", callback_data=f"delete_{idx}"))
    markup.add(types.InlineKeyboardButton("↩️ Назад", callback_data="back_main"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=text, reply_markup=markup)

# ===================== Редагування телефону =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_"))
def edit_phone(call):
    idx = int(call.data.split("_")[1])
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Модель 📱", callback_data=f"edit_model_{idx}"))
    markup.add(types.InlineKeyboardButton("Проблема ⚠️", callback_data=f"edit_problem_{idx}"))
    markup.add(types.InlineKeyboardButton("Ціна 💰", callback_data=f"edit_price_{idx}"))
    markup.add(types.InlineKeyboardButton("↩️ Назад", callback_data=f"view_{idx}"))
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id,
                          text="Що хочеш редагувати?", reply_markup=markup)

def register_edit_handler(idx, field_name, prompt, convert=lambda x:x):
    msg = bot.send_message(call.message.chat.id, prompt)
    bot.register_next_step_handler(msg, lambda m: save_edit(m, idx, field_name, convert))

def save_edit(message, idx, field_name, convert):
    try:
        new_value = convert(message.text)
    except:
        msg = bot.send_message(message.chat.id, "Невірний формат, спробуй ще раз:")
        bot.register_next_step_handler(msg, lambda m: save_edit(m, idx, field_name, convert))
        return
    data["phones"][idx][field_name] = new_value
    save_data(data)
    bot.send_message(message.chat.id, "✅ Оновлено!", reply_markup=main_menu())

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_model_"))
def edit_model(call):
    idx = int(call.data.split("_")[2])
    msg = bot.send_message(call.message.chat.id, "Введи нову модель:")
    bot.register_next_step_handler(msg, lambda m: save_edit(m, idx, "model"))

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_problem_"))
def edit_problem(call):
    idx = int(call.data.split("_")[2])
    msg = bot.send_message(call.message.chat.id, "Введи нову проблему:")
    bot.register_next_step_handler(msg, lambda m: save_edit(m, idx, "problem"))

@bot.callback_query_handler(func=lambda call: call.data.startswith("edit_price_"))
def edit_price(call):
    idx = int(call.data.split("_")[2])
    msg = bot.send_message(call.message.chat.id, "Введи нову ціну:")
    bot.register_next_step_handler(msg, lambda m: save_edit(m, idx, "price", float))

# ===================== Видалення телефону =====================
@bot.callback_query_handler(func=lambda call: call.data.startswith("delete_"))
def delete_phone(call):
    idx = int(call.data.split("_")[1])
    removed = data["phones"].pop(idx)
    save_data(data)
    bot.answer_callback_query(call.id, f"🗑️ {removed['model']} видалено!")
    list_phones(call.message)

# ===================== Повернення в меню =====================
@bot.callback_query_handler(func=lambda call: call.data=="back_main")
def back_main(call):
    bot.send_message(call.message.chat.id, "Головне меню:", reply_markup=main_menu())

# ===================== Підсумок =====================
@bot.message_handler(func=lambda m: m.text=="📊 Підсумок")
def summary(message):
    total = sum(p["price"] for p in data["phones"])
    count = len(data["phones"])
    bot.send_message(message.chat.id, f"📊 Кількість телефонів: {count}\n💰 Загальна сума: {total}₴", reply_markup=main_menu())

# ===================== Запуск =====================
bot.infinity_polling()