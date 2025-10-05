import json
from telebot import TeleBot
from flask import Flask, request

TOKEN = "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)
app = Flask(__name__)

DATA_FILE = "data.json"

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

@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(message.chat.id, "Вітаю! Напиши /add для додавання телефону або /list для перегляду.")

@bot.message_handler(commands=["add"])
def add_phone(message):
    msg = bot.send_message(message.chat.id, "Введи модель телефону:")
    bot.register_next_step_handler(msg, add_price)

def add_price(message):
    model = message.text
    msg = bot.send_message(message.chat.id, "Введи ціну ремонту:")
    bot.register_next_step_handler(msg, lambda m: save_phone(m, model))

def save_phone(message, model):
    try:
        price = float(message.text)
    except:
        msg = bot.send_message(message.chat.id, "Введи число для ціни:")
        bot.register_next_step_handler(msg, lambda m: save_phone(m, model))
        return
    data["phones"].append({"model": model, "price": price})
    save_data(data)
    bot.send_message(message.chat.id, f"Телефон {model} додано за {price}₴!")

@bot.message_handler(commands=["list"])
def list_phones(message):
    if not data["phones"]:
        bot.send_message(message.chat.id, "Телефонів поки немає.")
        return
    text = ""
    for idx, p in enumerate(data["phones"], start=1):
        text += f"{idx}. {p['model']} — {p['price']}₴\n"
    bot.send_message(message.chat.id, text)

bot.polling()
