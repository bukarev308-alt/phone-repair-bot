from telebot import TeleBot, types
from datetime import datetime

TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)

# Дані
phones = []
shops = {
    "It Center": "💙",
    "Леся": "💛",
    "Особисті": "💚"
}

# Емодзі для типу проблеми
problem_emojis = {
    "батарея": "🔋",
    "екран": "📱",
    "електроніка": "⚡",
    "інше": "🛠"
}

# Хелпери
def summary_text():
    total_money = sum(p["price"] for p in phones)
    total_phones = len(phones)
    return f"📊 Кількість телефонів: {total_phones}\n💰 Сума: {total_money} грн"

def make_phone_buttons(filtered=None):
    markup = types.InlineKeyboardMarkup()
    if filtered is None:
        filtered = phones
    for i, p in enumerate(filtered):
        emoji = problem_emojis.get(p.get("problem_type", "інше"), "🛠")
        shop_emoji = shops.get(p["shop"], "")
        markup.add(types.InlineKeyboardButton(f"{shop_emoji} {p['model']} {emoji} | {p['price']} грн", callback_data=f"phone_{i}"))
    return markup

def shop_buttons():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in shops:
        markup.add(f"{shops[s]} {s}")
    markup.add("➕ Додати магазин")
    return markup

def filter_shop_buttons():
    markup = types.InlineKeyboardMarkup()
    for s in shops:
        markup.add(types.InlineKeyboardButton(f"{shops[s]} {s}", callback_data=f"filter_{s}"))
    return markup

def sort_buttons(shop_name):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("💰 Ціна ↑", callback_data=f"sort_price_asc_{shop_name}"))
    markup.add(types.InlineKeyboardButton("💰 Ціна ↓", callback_data=f"sort_price_desc_{shop_name}"))
    markup.add(types.InlineKeyboardButton("🕒 Дата ↑", callback_data=f"sort_date_asc_{shop_name}"))
    markup.add(types.InlineKeyboardButton("🕒 Дата ↓", callback_data=f"sort_date_desc_{shop_name}"))
    return markup

# Старт
@bot.message_handler(commands=["start"])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("➕ Додати телефон", "📋 Переглянути телефони")
    markup.row("✏️ Редагувати/Видалити", "📊 Підсумок")
    bot.send_message(message.chat.id, "Привіт! Оберіть дію:", reply_markup=markup)

# Додати телефон
@bot.message_handler(func=lambda m: m.text=="➕ Додати телефон")
def add_phone(message):
    msg = bot.send_message(message.chat.id, "Виберіть магазин:", reply_markup=shop_buttons())
    bot.register_next_step_handler(msg, choose_shop)

def choose_shop(message):
    text = message.text.replace("💙","").replace("💛","").replace("💚","").strip()
    if text == "➕ Додати магазин":
        msg = bot.send_message(message.chat.id, "Введіть назву нового магазину:")
        bot.register_next_step_handler(msg, add_new_shop)
        return
    if text not in shops:
        bot.send_message(message.chat.id, "Некоректний магазин.")
        return
    shop = text
    msg = bot.send_message(message.chat.id, "Введіть назву телефону:")
    bot.register_next_step_handler(msg, lambda m: enter_model(m, shop))

def add_new_shop(message):
    new_shop = message.text.strip()
    if new_shop in shops or new_shop == "":
        bot.send_message(message.chat.id, "Магазин вже існує або ім'я порожнє.")
        return
    shops[new_shop] = "🧡"  # Нові магазини з оранжевим кольором
    bot.send_message(message.chat.id, f"✅ Магазин '{new_shop}' додано!")
    msg = bot.send_message(message.chat.id, "Виберіть магазин для нового телефону:", reply_markup=shop_buttons())
    bot.register_next_step_handler(msg, choose_shop)

def enter_model(message, shop):
    model = message.text
    msg = bot.send_message(message.chat.id, "Введіть проблему:")
    bot.register_next_step_handler(msg, lambda m: enter_problem(m, shop, model))

def enter_problem(message, shop, model):
    problem = message.text.lower()
    problem_type = "інше"
    for key in problem_emojis:
        if key in problem:
            problem_type = key
            break
    msg = bot.send_message(message.chat.id, "Введіть ціну ремонту (число):")
    bot.register_next_step_handler(msg, lambda m: enter_price(m, shop, model, problem, problem_type))

def enter_price(message, shop, model, problem, problem_type):
    try:
        price = int(message.text)
    except:
        bot.send_message(message.chat.id, "Ціна повинна бути числом.")
        return
    phones.append({
        "shop": shop,
        "model": model,
        "problem": problem,
        "problem_type": problem_type,
        "price": price,
        "date": datetime.now()
    })
    bot.send_message(message.chat.id, f"✅ Телефон додано!\n{shops[shop]} {model} {problem_emojis.get(problem_type,'🛠')} | {price} грн")

# Перегляд телефонів
@bot.message_handler(func=lambda m: m.text=="📋 Переглянути телефони")
def view_phones(message):
    if not phones:
        bot.send_message(message.chat.id, "Список порожній.")
        return
    bot.send_message(message.chat.id, "Оберіть магазин:", reply_markup=filter_shop_buttons())

# Фільтр та сортування
@bot.callback_query_handler(func=lambda c: c.data.startswith("filter_"))
def filter_phones(call):
    shop_name = call.data.split("_")[1]
    filtered = [p for p in phones if p["shop"] == shop_name]
    if not filtered:
        bot.send_message(call.message.chat.id, "Список порожній.")
        return
    bot.send_message(call.message.chat.id, f"Телефони для {shops.get(shop_name, '')} {shop_name}:", reply_markup=sort_buttons(shop_name))

@bot.callback_query_handler(func=lambda c: c.data.startswith("sort_"))
def sort_phones(call):
    parts = call.data.split("_")
    sort_type, order, shop_name = parts[1], parts[2], "_".join(parts[3:])
    filtered = [p for p in phones if p["shop"] == shop_name]
    if sort_type == "price":
        filtered.sort(key=lambda x: x["price"], reverse=(order=="desc"))
    elif sort_type == "date":
        filtered.sort(key=lambda x: x["date"], reverse=(order=="desc"))
    bot.send_message(call.message.chat.id, f"📋 Телефони для {shops.get(shop_name,'')} {shop_name}:", reply_markup=make_phone_buttons(filtered))

# Редагування / Видалення
@bot.callback_query_handler(func=lambda c: c.data.startswith("phone_"))
def phone_options(call):
    index = int(call.data.split("_")[1])
    p = phones[index]
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("✏️ Редагувати", callback_data=f"edit_{index}"))
    markup.add(types.InlineKeyboardButton("🗑 Видалити", callback_data=f"delete_{index}"))
    emoji = problem_emojis.get(p.get("problem_type", "інше"), "🛠")
    shop_emoji = shops.get(p["shop"], "")
    bot.edit_message_text(f"{shop_emoji} {p['model']} {emoji} | {p['price']} грн", call.message.chat.id, call.message.message_id, reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delete_"))
def delete_phone_callback(call):
    index = int(call.data.split("_")[1])
    deleted = phones.pop(index)
    bot.edit_message_text(f"🗑 Видалено: {deleted['shop']} | {deleted['model']}", call.message.chat.id, call.message.message_id)

# Редагування
@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_"))
def edit_phone_callback(call):
    index = int(call.data.split("_")[1])
    p = phones[index]
    bot.send_message(call.message.chat.id, f"Редагуємо {p['shop']} | {p['model']}\nВведіть нову назву телефону:")
    bot.register_next_step_handler(call.message, lambda m: edit_model(m, index))

def edit_model(message, index):
    phones[index]["model"] = message.text
    bot.send_message(message.chat.id, "Введіть нову проблему:")
    bot.register_next_step_handler(message, lambda m: edit_problem(m, index))

def edit_problem(message, index):
    problem = message.text.lower()
    problem_type = "інше"
    for key in problem_emojis:
        if key in problem:
            problem_type = key
            break
    phones[index]["problem"] = problem
    phones[index]["problem_type"] = problem_type
    bot.send_message(message.chat.id, "Введіть нову ціну:")
    bot.register_next_step_handler(message, lambda m: edit_price(m, index))

def edit_price(message, index):
    try:
        phones[index]["price"] = int(message.text)
    except:
        bot.send_message(message.chat.id, "Ціна повинна бути числом.")
        return
    p = phones[index]
    emoji = problem_emojis.get(p.get("problem_type","інше"), "🛠")
    shop_emoji = shops.get(p["shop"], "")
    bot.send_message(message.chat.id, f"✅ Оновлено: {shop_emoji} {p['model']} {emoji} | {p['price']} грн")

# Підсумок
@bot.message_handler(func=lambda m: m.text=="📊 Підсумок")
def summary(message):
    bot.send_message(message.chat.id, summary_text())

# Запуск
bot.infinity_polling()