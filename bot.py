import os
import sqlite3
from telebot import TeleBot, types

TOKEN = os.environ.get("BOT_TOKEN")
bot = TeleBot(TOKEN)

STORES = ["It Center", "Леся", "Особисті"]

conn = sqlite3.connect("phones.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS phones (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    store TEXT,
    model TEXT,
    problem TEXT,
    price REAL
)
""")
conn.commit()

def main_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("Додати телефон")
    markup.row("Переглянути телефони")
    markup.row("Редагувати / Видалити")
    markup.row("Підсумок")
    return markup

def stores_menu():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in STORES:
        markup.row(s)
    return markup

user_data = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привіт! Обирай дію:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "Додати телефон")
def add_phone_step1(message):
    bot.send_message(message.chat.id, "Оберіть магазин:", reply_markup=stores_menu())
    bot.register_next_step_handler(message, add_phone_step2)

def add_phone_step2(message):
    store = message.text
    if store not in STORES:
        bot.send_message(message.chat.id, "Будь ласка, оберіть магазин з меню.")
        return add_phone_step1(message)
    user_data[message.chat.id] = {"store": store}
    bot.send_message(message.chat.id, "Введіть модель телефону:")
    bot.register_next_step_handler(message, add_phone_step3)

def add_phone_step3(message):
    user_data[message.chat.id]["model"] = message.text
    bot.send_message(message.chat.id, "Введіть проблему телефону:")
    bot.register_next_step_handler(message, add_phone_step4)

def add_phone_step4(message):
    user_data[message.chat.id]["problem"] = message.text
    bot.send_message(message.chat.id, "Введіть ціну ремонту (числом):")
    bot.register_next_step_handler(message, add_phone_step5)

def add_phone_step5(message):
    try:
        price = float(message.text)
    except:
        bot.send_message(message.chat.id, "Будь ласка, введіть число для ціни.")
        bot.register_next_step_handler(message, add_phone_step5)
        return
    user_data[message.chat.id]["price"] = price
    data = user_data.pop(message.chat.id)
    cursor.execute("INSERT INTO phones (store, model, problem, price) VALUES (?, ?, ?, ?)",
                   (data["store"], data["model"], data["problem"], data["price"]))
    conn.commit()
    bot.send_message(message.chat.id, "Телефон додано!", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "Переглянути телефони")
def view_phones(message):
    phones = cursor.execute("SELECT id, store, model, problem, price FROM phones").fetchall()
    if not phones:
        bot.send_message(message.chat.id, "Немає телефонів.")
    else:
        text = ""
        for p in phones:
            text += f"ID: {p[0]}\nМагазин: {p[1]}\nМодель: {p[2]}\nПроблема: {p[3]}\nЦіна: {p[4]}\n\n"
        bot.send_message(message.chat.id, text)
    bot.send_message(message.chat.id, "Оберіть дію:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "Підсумок")
def summary(message):
    total_phones = cursor.execute("SELECT COUNT(*) FROM phones").fetchone()[0]
    total_price = cursor.execute("SELECT SUM(price) FROM phones").fetchone()[0] or 0
    text = f"Загальна кількість телефонів: {total_phones}\nЗагальна сума: {total_price} грн"
    bot.send_message(message.chat.id, text, reply_markup=main_menu())

bot.infinity_polling()
