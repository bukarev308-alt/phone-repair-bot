import os
import json
import threading
import re
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
DATA_FILE = "data.json"

bot = TeleBot(TOKEN)
data_lock = threading.Lock()

# =======================
# КИЇВСЬКИЙ ЧАС
# =======================
def get_kiev_time():
    return datetime.utcnow() + timedelta(hours=3)

def format_kiev_date(date=None):
    if date is None:
        date = get_kiev_time()
    return date.strftime("%d.%m.%Y %H:%M")

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            default_data = {
                "stores": {
                    "It Center": {"percentage": 70},
                    "Леся": {"percentage": 80}, 
                    "Особисті": {"percentage": 100}
                },
                "phones": [],
                "archive": []
            }
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(default_data, f, ensure_ascii=False, indent=2)
            return default_data
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Помилка завантаження даних: {e}")
            return {
                "stores": {
                    "It Center": {"percentage": 70},
                    "Леся": {"percentage": 80},
                    "Особисті": {"percentage": 100}
                },
                "phones": [],
                "archive": []
            }

def save_data(d):
    with data_lock:
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Помилка збереження даних: {e}")

# Завантажуємо дані при старті
data = load_data()

# =======================
# СТАН КОРИСТУВАЧА
# =======================
user_state = {}

def ensure_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"stack": [], "tmp": {}}

def push_state(chat_id, state_name):
    ensure_state(chat_id)
    user_state[chat_id]["stack"].append(state_name)

def pop_state(chat_id):
    ensure_state(chat_id)
    if user_state[chat_id]["stack"]:
        user_state[chat_id]["stack"].pop()
    if not user_state[chat_id]["stack"]:
        user_state[chat_id]["tmp"] = {}

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    if chat_id in user_state:
        user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# УТИЛІТИ ВІДОБРАЖЕННЯ ТА РОЗРАХУНКИ
# =======================
def fmt_price(p):
    try:
        if int(p) == p:
            return f"{int(p)}"
    except Exception:
        pass
    return f"{p}"

def calculate_net_price(price, store_name):
    """Розраховує чистий заробіток з урахуванням відсотка магазину"""
    if store_name in data["stores"]:
        percentage = data["stores"][store_name]["percentage"]
        net_price = price * (percentage / 100)
        return round(net_price, 2)
    return price

def phone_display(p):
    store = p['store']
    price = float(p['price'])
    net_price = calculate_net_price(price, store)
    percentage = data["stores"][store]["percentage"]
    
    return (f"{p['model']} ({store})\n"
            f"🔧 {p['problem']}\n"
            f"💰 {fmt_price(price)} грн (чисті: {fmt_price(net_price)} грн)\n"
            f"📊 {percentage}% від магазину\n"
            f"🕒 {p['date']}")

def phone_short(p):
    return f"{p['model']} ({p['store']})"

# =======================
# КЛАВІАТУРИ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини", "🗂 Архів")
    kb.add("📝 Перенести тиждень в архів")
    return kb

def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

def stores_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for store_name, store_data in data["stores"].items():
        percentage = store_data["percentage"]
        kb.add(f"{store_name} ({percentage}%)")
    kb.add("➕ Додати магазин", "📊 Змінити відсоток")
    kb.add("⬅️ Назад")
    return kb

def phones_list_keyboard(phones):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {phone_short(p)}")
    kb.add("⬅️ Назад")
    return kb

# =======================
# ОСНОВНІ КОМАНДИ
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

@bot.message_handler(func=lambda m: m.text == "🏪 Магазини")
def manage_stores(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "stores_management")
    
    text = "🏪 <b>Управління магазинами:</b>\n\n"
    for store_name, store_data in data["stores"].items():
        percentage = store_data["percentage"]
        text += f"• {store_name}: {percentage}%\n"
    
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=stores_menu())

@bot.message_handler(func=lambda m: m.text == "📋 Переглянути телефони")
def show_phones(message):
    chat_id = message.chat.id
    if not data["phones"]:
        bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
        return
    
    text = "📋 <b>Список телефонів:</b>\n\n"
    for i, p in enumerate(data["phones"], 1):
        text += (f"{i}. {phone_display(p)}\n\n")
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📊 Підсумок")
def show_summary(message):
    chat_id = message.chat.id
    if not data["phones"]:
        bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
        return
    
    total_revenue = sum(float(p["price"]) for p in data["phones"])
    total_net_revenue = sum(calculate_net_price(float(p["price"]), p["store"]) for p in data["phones"])
    count = len(data["phones"])
    
    stores_summary = {}
    for p in data["phones"]:
        store = p["store"]
        price = float(p["price"])
        net_price = calculate_net_price(price, store)
        
        if store not in stores_summary:
            stores_summary[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
        
        stores_summary[store]["revenue"] += price
        stores_summary[store]["net_revenue"] += net_price
        stores_summary[store]["count"] += 1
    
    store_text = "\n".join(
        f"• {s}: {fmt_price(v['revenue'])} грн (чисті: {fmt_price(v['net_revenue'])} грн)" 
        for s, v in stores_summary.items()
    )
    
    bot.send_message(chat_id,
                     f"📊 Підсумок:\n"
                     f"🔢 Кількість телефонів: {count}\n"
                     f"💰 Загальна сума: {fmt_price(total_revenue)} грн\n"
                     f"💵 Чистий заробіток: {fmt_price(total_net_revenue)} грн\n\n"
                     f"<b>По магазинах:</b>\n{store_text}",
                     parse_mode="HTML", reply_markup=main_menu())

# =======================
# ОБРОБНИК СТАНІВ
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text.strip() if message.text else ""
    state = current_state(chat_id)

    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return

    # ДОДАВАННЯ ТЕЛЕФОНУ
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        
        # Обробка вибору магазину
        for store_name in data["stores"]:
            if txt.startswith(store_name):
                user_state[chat_id]["tmp"]["store"] = store_name
                push_state(chat_id, "add_model")
                percentage = data["stores"][store_name]["percentage"]
                bot.send_message(chat_id, f"Магазин: {store_name} ({percentage}%)\nВведіть модель телефону:", reply_markup=back_button())
                return
        
        bot.send_message(chat_id, "❌ Оберіть магазин зі списку.", reply_markup=stores_menu())
        return

    if state == "add_new_store":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"][store_name] = {"percentage": 100}  # За замовчуванням 100%
            save_data(data)
            user_state[chat_id]["tmp"]["store"] = store_name
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, f"✅ Магазин додано!\nВведіть модель телефону:", reply_markup=back_button())
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста.")
        return

    if state == "add_model":
        user_state[chat_id]["tmp"]["model"] = txt
        push_state(chat_id, "add_problem")
        bot.send_message(chat_id, "Опишіть проблему телефону:", reply_markup=back_button())
        return

    if state == "add_problem":
        user_state[chat_id]["tmp"]["problem"] = txt
        push_state(chat_id, "add_price")
        bot.send_message(chat_id, "Вкажіть ціну ремонту (числом):", reply_markup=back_button())
        return

    if state == "add_price":
        try:
            price = float(txt.replace(",", "."))
            tmp = user_state[chat_id]["tmp"]
            store_name = tmp["store"]
            net_price = calculate_net_price(price, store_name)
            
            phone = {
                "store": store_name,
                "model": tmp["model"],
                "problem": tmp["problem"],
                "price": price,
                "date": format_kiev_date()
            }
            
            data["phones"].append(phone)
            save_data(data)
            
            percentage = data["stores"][store_name]["percentage"]
            bot.send_message(chat_id, 
                           f"✅ Телефон додано!\n"
                           f"💰 Сума: {price} грн\n"
                           f"💵 Чисті ({percentage}%): {net_price} грн", 
                           reply_markup=main_menu())
            clear_state(chat_id)
        except:
            bot.send_message(chat_id, "❌ Введіть правильне число.")
        return

    # УПРАВЛІННЯ МАГАЗИНАМИ
    if state == "stores_management":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store_management")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        
        if txt == "📊 Змінити відсоток":
            push_state(chat_id, "select_store_for_percentage")
            bot.send_message(chat_id, "Оберіть магазин для зміни відсотка:", reply_markup=stores_menu())
            return
        
        # Показати інформацію про магазин
        for store_name in data["stores"]:
            if txt.startswith(store_name):
                percentage = data["stores"][store_name]["percentage"]
                bot.send_message(chat_id, f"🏪 {store_name}\n📊 Відсоток: {percentage}%", reply_markup=stores_menu())
                return
        
        bot.send_message(chat_id, "❌ Оберіть дію з меню.", reply_markup=stores_menu())
        return

    if state == "add_new_store_management":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"][store_name] = {"percentage": 100}
            save_data(data)
            bot.send_message(chat_id, f"✅ Магазин «{store_name}» додано!", reply_markup=main_menu())
            clear_state(chat_id)
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста.")
        return

    if state == "select_store_for_percentage":
        for store_name in data["stores"]:
            if txt.startswith(store_name):
                user_state[chat_id]["tmp"]["store_for_percentage"] = store_name
                push_state(chat_id, "enter_percentage")
                current_percentage = data["stores"][store_name]["percentage"]
                bot.send_message(chat_id, f"Магазин: {store_name}\nПоточний відсоток: {current_percentage}%\nВведіть новий відсоток (0-100):", reply_markup=back_button())
                return
        
        bot.send_message(chat_id, "❌ Оберіть магазин зі списку.", reply_markup=stores_menu())
        return

    if state == "enter_percentage":
        try:
            percentage = float(txt.replace(",", "."))
            if 0 <= percentage <= 100:
                store_name = user_state[chat_id]["tmp"]["store_for_percentage"]
                data["stores"][store_name]["percentage"] = percentage
                save_data(data)
                bot.send_message(chat_id, f"✅ Відсоток для {store_name} змінено на {percentage}%", reply_markup=main_menu())
                clear_state(chat_id)
            else:
                bot.send_message(chat_id, "❌ Відсоток повинен бути від 0 до 100.")
        except:
            bot.send_message(chat_id, "❌ Введіть коректне число.")
        return

    bot.send_message(chat_id, "Оберіть дію з меню.", reply_markup=main_menu())

# =======================
# СТАРТ БОТА
# =======================
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()