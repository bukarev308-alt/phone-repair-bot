import telebot
from telebot import types
import json
from datetime import datetime
import os

# 🔐 ВСТАВ СВІЙ ТОКЕН СЮДИ
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"

bot = telebot.TeleBot(TOKEN)

DATA_FILE = "data.json"


# === ЗАВАНТАЖЕННЯ ТА ЗБЕРЕЖЕННЯ ДАНИХ ===
def load_data():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, "w") as f:
            json.dump({"stores": ["It Center", "Леся", "Особисті"], "phones": []}, f)
    with open(DATA_FILE, "r") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


data = load_data()


# === ГОЛОВНЕ МЕНЮ ===
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("🏪 Магазини", "📊 Підсумок")
    return kb


# === ПОВЕРНЕННЯ НАЗАД ===
def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb


# === СТАРТ ===
@bot.message_handler(commands=["start"])
def start(message):
    bot.send_message(
        message.chat.id,
        "Привіт 👋\nЦей бот допоможе вести облік телефонів у ремонті.",
        reply_markup=main_menu(),
    )


# === ДОДАВАННЯ ТЕЛЕФОНУ ===
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_step1(message):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for store in data["stores"]:
        kb.add(store)
    kb.add("➕ Додати магазин")
    kb.add("⬅️ Назад")
    msg = bot.send_message(
        message.chat.id, "📍 Вибери магазин або додай новий:", reply_markup=kb
    )
    bot.register_next_step_handler(msg, add_phone_store_selected)


def add_phone_store_selected(message):
    if message.text == "⬅️ Назад":
        bot.send_message(message.chat.id, "🔙 Назад у головне меню", reply_markup=main_menu())
        return

    if message.text == "➕ Додати магазин":
        msg = bot.send_message(message.chat.id, "🏪 Введи назву нового магазину:", reply_markup=back_button())
        bot.register_next_step_handler(msg, add_new_store)
        return

    if message.text not in data["stores"]:
        bot.send_message(message.chat.id, "❌ Обери магазин зі списку або додай новий.")
        return

    store = message.text
    msg = bot.send_message(message.chat.id, "📱 Введи модель телефону:", reply_markup=back_button())
    bot.register_next_step_handler(msg, add_phone_model, store)


def add_new_store(message):
    if message.text == "⬅️ Назад":
        bot.send_message(message.chat.id, "🔙 Назад", reply_markup=main_menu())
        return

    store_name = message.text.strip()
    if store_name not in data["stores"]:
        data["stores"].append(store_name)
        save_data(data)
        bot.send_message(message.chat.id, f"✅ Магазин «{store_name}» додано!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "⚠️ Такий магазин уже існує.", reply_markup=main_menu())


def add_phone_model(message, store):
    if message.text == "⬅️ Назад":
        bot.send_message(message.chat.id, "🔙 Назад", reply_markup=main_menu())
        return
    model = message.text
    msg = bot.send_message(message.chat.id, "🔧 Опиши проблему:", reply_markup=back_button())
    bot.register_next_step_handler(msg, add_phone_problem, store, model)


def add_phone_problem(message, store, model):
    if message.text == "⬅️ Назад":
        bot.send_message(message.chat.id, "🔙 Назад", reply_markup=main_menu())
        return
    problem = message.text
    msg = bot.send_message(message.chat.id, "💰 Вкажи ціну ремонту:", reply_markup=back_button())
    bot.register_next_step_handler(msg, add_phone_price, store, model, problem)


def add_phone_price(message, store, model, problem):
    if message.text == "⬅️ Назад":
        bot.send_message(message.chat.id, "🔙 Назад", reply_markup=main_menu())
        return
    try:
        price = float(message.text)
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введи число (наприклад, 1200).", reply_markup=back_button())
        return
    phone = {
        "store": store,
        "model": model,
        "problem": problem,
        "price": price,
        "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
    }
    data["phones"].append(phone)
    save_data(data)
    bot.send_message(message.chat.id, "✅ Телефон додано!", reply_markup=main_menu())


# === ПЕРЕГЛЯД ТЕЛЕФОНІВ ===
@bot.message_handler(func=lambda m: m.text == "📋 Переглянути телефони")
def view_phones(message):
    if not data["phones"]:
        bot.send_message(message.chat.id, "📭 Немає телефонів у базі.", reply_markup=main_menu())
        return
    text = "📋 <b>Список телефонів:</b>\n\n"
    for i, phone in enumerate(data["phones"], 1):
        text += (
            f"{i}. {phone['model']} ({phone['store']})\n"
            f"🔧 {phone['problem']}\n"
            f"💰 {phone['price']} грн\n"
            f"🕒 {phone['date']}\n\n"
        )
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())


# === ПІДСУМОК ===
@bot.message_handler(func=lambda m: m.text == "📊 Підсумок")
def summary(message):
    total = sum(p["price"] for p in data["phones"])
    count = len(data["phones"])
    bot.send_message(
        message.chat.id,
        f"📊 <b>Підсумок:</b>\n🔢 Кількість телефонів: {count}\n💰 Загальна сума: {total} грн",
        parse_mode="HTML",
        reply_markup=main_menu(),
    )


# === МАГАЗИНИ ===
@bot.message_handler(func=lambda m: m.text == "🏪 Магазини")
def stores_list(message):
    text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
    bot.send_message(message.chat.id, text, parse_mode="HTML", reply_markup=main_menu())


print("✅ Бот запущено!")
bot.infinity_polling()