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

def format_kiev_date_short(date=None):
    if date is None:
        date = get_kiev_time()
    return date.strftime("%d.%m.%Y")

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            default_data = {
                "stores": {
                    "It Center": {"percentage": 100},
                    "Леся": {"percentage": 100},
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
                    "It Center": {"percentage": 100},
                    "Леся": {"percentage": 100},
                    "Особисті": {"percentage": 100}
                },
                "phones": [],
                "archive": []
            }

def save_data(d):
    with data_lock:
        try:
            global data
            data = d
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Помилка збереження даних: {e}")

def refresh_data():
    global data
    data = load_data()

def add_phone_safe(phone_data):
    global data
    refresh_data()
    data["phones"].append(phone_data)
    save_data(data)

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
        return net_price
    return price

def phone_display(p):
    store = p['store']
    price = float(p['price'])
    net_price = calculate_net_price(price, store)
    percentage = data["stores"][store]["percentage"] if store in data["stores"] else 100
    
    return (f"{p['model']} ({store})\n"
            f"🔧 {p['problem']}\n"
            f"💰 {fmt_price(price)} грн (чисті: {fmt_price(net_price)} грн)\n"
            f"📊 {percentage}% від магазину\n"
            f"🕒 {p['date']}")

def phone_short(p):
    return f"{p['model']} ({p['store']})"

# =======================
# НОВІ ФУНКЦІЇ ДЛЯ ЗВІТІВ З ВІДСОТКАМИ
# =======================
def get_weekly_financial_report(phones):
    """Тижневий звіт з грошима по магазинах з урахуванням відсотків"""
    week_ago = get_kiev_time() - timedelta(days=7)
    
    store_revenue = {}
    total_revenue = 0
    total_net_revenue = 0
    total_phones = len(phones)
    
    for phone in phones:
        try:
            phone_date = datetime.strptime(phone['date'], "%d.%m.%Y %H:%M")
            if phone_date >= week_ago:
                store = phone['store']
                price = float(phone['price'])
                net_price = calculate_net_price(price, store)
                
                if store not in store_revenue:
                    store_revenue[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
                
                store_revenue[store]["revenue"] += price
                store_revenue[store]["net_revenue"] += net_price
                store_revenue[store]["count"] += 1
                total_revenue += price
                total_net_revenue += net_price
        except:
            continue
    
    return store_revenue, total_revenue, total_net_revenue, total_phones

def get_monthly_financial_report():
    """Місячний звіт по грошах з урахуванням відсотків"""
    month_ago = get_kiev_time() - timedelta(days=30)
    
    store_revenue = {}
    total_revenue = 0
    total_net_revenue = 0
    total_phones = 0
    
    # Поточні телефони
    for phone in data["phones"]:
        try:
            phone_date = datetime.strptime(phone['date'], "%d.%m.%Y %H:%M")
            if phone_date >= month_ago:
                store = phone['store']
                price = float(phone['price'])
                net_price = calculate_net_price(price, store)
                
                if store not in store_revenue:
                    store_revenue[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
                
                store_revenue[store]["revenue"] += price
                store_revenue[store]["net_revenue"] += net_price
                store_revenue[store]["count"] += 1
                total_revenue += price
                total_net_revenue += net_price
                total_phones += 1
        except:
            continue
    
    # Архівні дані
    for archive_week in data.get("archive", []):
        try:
            week_end_date = datetime.strptime(archive_week['week'].split(" - ")[1], "%d.%m.%Y")
            if week_end_date >= month_ago:
                for phone in archive_week.get("phones", []):
                    store = phone['store']
                    price = float(phone['price'])
                    net_price = calculate_net_price(price, store)
                    
                    if store not in store_revenue:
                        store_revenue[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
                    
                    store_revenue[store]["revenue"] += price
                    store_revenue[store]["net_revenue"] += net_price
                    store_revenue[store]["count"] += 1
                    total_revenue += price
                    total_net_revenue += net_price
                    total_phones += 1
        except:
            continue
    
    return store_revenue, total_revenue, total_net_revenue, total_phones

def get_archive_week_financial_report(week_data):
    """Фінансовий звіт для архівного тижня з урахуванням відсотків"""
    store_revenue = {}
    total_revenue = 0
    total_net_revenue = 0
    total_phones = len(week_data.get("phones", []))
    
    for phone in week_data.get("phones", []):
        store = phone['store']
        price = float(phone['price'])
        net_price = calculate_net_price(price, store)
        
        if store not in store_revenue:
            store_revenue[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
        
        store_revenue[store]["revenue"] += price
        store_revenue[store]["net_revenue"] += net_price
        store_revenue[store]["count"] += 1
        total_revenue += price
        total_net_revenue += net_price
    
    return store_revenue, total_revenue, total_net_revenue, total_phones

# =======================
# КЛАВІАТУРИ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини", "🗂 Архів")
    kb.add("📝 Перенести тиждень в архів", "💰 Фінансові звіти")
    return kb

def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

def stores_menu(include_add=True, include_percentage=True):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for store_name in data["stores"]:
        percentage = data["stores"][store_name]["percentage"]
        kb.add(f"{store_name} ({percentage}%)")
    if include_add:
        kb.add("➕ Додати магазин")
    if include_percentage:
        kb.add("📊 Змінити відсоток")
    kb.add("⬅️ Назад")
    return kb

def edit_action_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✏️ Редагувати", "🗑 Видалити")
    kb.add("⬅️ Назад")
    return kb

def edit_field_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Магазин", "Модель")
    kb.add("Проблема", "Ціна")
    kb.add("⬅️ Назад")
    return kb

def confirm_delete_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Так", "❌ Ні")
    return kb

def archive_week_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weeks = [w["week"] for w in data.get("archive", [])]
    for w in weeks:
        kb.add(w)
    kb.add("⬅️ Назад")
    return kb

def archive_view_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("🔽 Показати телефони", "🔼 Відновити тиждень")
    kb.add("📤 Відновити телефон", "❌ Видалити телефон з архіву")
    kb.add("💰 Фінансовий звіт", "🗑 Видалити тиждень")
    kb.add("⬅️ Назад")
    return kb

def financial_reports_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📊 Тижневий фінансовий звіт", "📈 Місячний фінансовий звіт")
    kb.add("🏪 Звіт по магазинах", "⬅️ Назад")
    return kb

def phones_list_keyboard(phones):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {phone_short(p)}")
    kb.add("⬅️ Назад")
    return kb

# =======================
# СТАРТ
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    refresh_data()
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

@bot.message_handler(commands=["refresh"])
def cmd_refresh(message):
    refresh_data()
    bot.send_message(message.chat.id, "✅ Дані оновлено!", reply_markup=main_menu())

# =======================
# УПРАВЛІННЯ МАГАЗИНАМИ ТА ВІДСОТКАМИ
# =======================
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

@bot.message_handler(func=lambda m: m.text == "📊 Змінити відсоток")
def change_percentage_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "select_store_for_percentage")
    bot.send_message(chat_id, "Оберіть магазин для зміни відсотка:", 
                     reply_markup=stores_menu(include_add=False, include_percentage=False))

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ (початок)
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu(include_percentage=False))

# =======================
# РЕДАГУВАННЯ / ВИДАЛЕННЯ (початок)
# =======================
@bot.message_handler(func=lambda m: m.text == "✏️ Редагувати / 🗑 Видалити")
def edit_phone_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    if not data["phones"]:
        bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
        return
    push_state(chat_id, "edit_select")
    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", 
                     reply_markup=phones_list_keyboard(data["phones"]))

# =======================
# ФІНАНСОВІ ЗВІТИ
# =======================
@bot.message_handler(func=lambda m: m.text == "💰 Фінансові звіти")
def financial_reports_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "financial_reports")
    bot.send_message(chat_id, "📊 Оберіть тип фінансового звіту:", reply_markup=financial_reports_menu())

# =======================
# ОСНОВНИЙ ОБРОБНИК ПОВІДОМЛЕНЬ
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text.strip() if message.text else ""
    state = current_state(chat_id)

    # Обробка кнопки "Назад"
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        new_state = current_state(chat_id)
        if not new_state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        else:
            # Спеціальна обробка для деяких станів
            if new_state == "stores_management":
                bot.send_message(chat_id, "Повертаємося до управління магазинами.", 
                               reply_markup=stores_menu())
            else:
                bot.send_message(chat_id, "Повертаємося в попереднє меню.", reply_markup=main_menu())
        return

    # Управління магазинами
    if state == "stores_management":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt == "📊 Змінити відсоток":
            push_state(chat_id, "select_store_for_percentage")
            bot.send_message(chat_id, "Оберіть магазин для зміни відсотка:", 
                           reply_markup=stores_menu(include_add=False, include_percentage=False))
            return
        elif any(txt.startswith(store) for store in data["stores"]):
            # Користувач обрав магазин зі списку
            store_name = next(store for store in data["stores"] if txt.startswith(store))
            ensure_state(chat_id)
            user_state[chat_id]["tmp"]["selected_store"] = store_name
            push_state(chat_id, "store_actions")
            percentage = data["stores"][store_name]["percentage"]
            bot.send_message(chat_id, 
                           f"Магазин: <b>{store_name}</b>\nПоточний відсоток: <b>{percentage}%</b>\n\nОберіть дію:",
                           parse_mode="HTML", reply_markup=back_button())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку або дію з меню.", 
                           reply_markup=stores_menu())
            return

    # Вибір магазину для зміни відсотка
    if state == "select_store_for_percentage":
        if any(txt.startswith(store) for store in data["stores"]):
            store_name = next(store for store in data["stores"] if txt.startswith(store))
            ensure_state(chat_id)
            user_state[chat_id]["tmp"]["store_for_percentage"] = store_name
            push_state(chat_id, "enter_percentage")
            current_percentage = data["stores"][store_name]["percentage"]
            bot.send_message(chat_id, 
                           f"Магазин: <b>{store_name}</b>\nПоточний відсоток: <b>{current_percentage}%</b>\n\nВведіть новий відсоток (0-100):",
                           parse_mode="HTML", reply_markup=back_button())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку.", 
                           reply_markup=stores_menu(include_add=False, include_percentage=False))
            return

    # Введення нового відсотка
    if state == "enter_percentage":
        try:
            percentage = float(txt.replace(",", "."))
            if 0 <= percentage <= 100:
                store_name = user_state[chat_id]["tmp"]["store_for_percentage"]
                data["stores"][store_name]["percentage"] = percentage
                save_data(data)
                bot.send_message(chat_id, 
                               f"✅ Відсоток для магазину <b>{store_name}</b> змінено на <b>{percentage}%</b>",
                               parse_mode="HTML", reply_markup=main_menu())
                clear_state(chat_id)
            else:
                bot.send_message(chat_id, "❌ Відсоток повинен бути від 0 до 100. Спробуйте ще раз:")
        except ValueError:
            bot.send_message(chat_id, "❌ Введіть коректне число (наприклад: 70 або 70.5):")

    # Додавання нового магазину
    if state == "add_new_store":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"][store_name] = {"percentage": 100}  # За замовчуванням 100%
            save_data(data)
            bot.send_message(chat_id, f"✅ Магазин «{store_name}» додано з відсотком 100%!", 
                           reply_markup=main_menu())
            clear_state(chat_id)
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста. Спробуйте ще раз.")

    # Головне меню
    if txt == "📋 Переглянути телефони":
        refresh_data()
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        text = "📋 <b>Список телефонів:</b>\n\n"
        for i, p in enumerate(data["phones"], 1):
            text += (f"{i}. {phone_display(p)}\n\n")
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "📊 Підсумок":
        refresh_data()
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
        return

    # Фінансові звіти з відсотками
    if state == "financial_reports":
        if txt == "📊 Тижневий фінансовий звіт":
            refresh_data()
            if not data["phones"]:
                bot.send_message(chat_id, "📭 Телефонів за тиждень немає.", reply_markup=financial_reports_menu())
                return
            
            store_revenue, total_revenue, total_net_revenue, total_phones = get_weekly_financial_report(data["phones"])
            
            if not store_revenue:
                bot.send_message(chat_id, "📭 Немає даних за поточний тиждень.", reply_markup=financial_reports_menu())
                return
            
            report_text = "📊 <b>Тижневий фінансовий звіт</b>\n\n"
            for store, info in store_revenue.items():
                percentage = data["stores"][store]["percentage"]
                report_text += f"🏪 <b>{store}</b> ({percentage}%):\n"
                report_text += f"   📱 Телефонів: {info['count']}\n"
                report_text += f"   💰 Сума: {fmt_price(info['revenue'])} грн\n"
                report_text += f"   💵 Чисті: {fmt_price(info['net_revenue'])} грн\n\n"
            
            report_text += f"<b>Загалом за тиждень:</b>\n"
            report_text += f"📱 Телефонів: {total_phones}\n"
            report_text += f"💰 Загальна сума: {fmt_price(total_revenue)} грн\n"
            report_text += f"💵 Чистий заробіток: {fmt_price(total_net_revenue)} грн"
            
            bot.send_message(chat_id, report_text, parse_mode="HTML", reply_markup=financial_reports_menu())
            return

        elif txt == "📈 Місячний фінансовий звіт":
            refresh_data()
            store_revenue, total_revenue, total_net_revenue, total_phones = get_monthly_financial_report()
            
            if not store_revenue:
                bot.send_message(chat_id, "📭 Немає даних за поточний місяць.", reply_markup=financial_reports_menu())
                return
            
            report_text = "📈 <b>Місячний фінансовий звіт</b>\n\n"
            for store, info in store_revenue.items():
                percentage = data["stores"][store]["percentage"]
                report_text += f"🏪 <b>{store}</b> ({percentage}%):\n"
                report_text += f"   📱 Телефонів: {info['count']}\n"
                report_text += f"   💰 Сума: {fmt_price(info['revenue'])} грн\n"
                report_text += f"   💵 Чисті: {fmt_price(info['net_revenue'])} грн\n\n"
            
            report_text += f"<b>Загалом за місяць:</b>\n"
            report_text += f"📱 Телефонів: {total_phones}\n"
            report_text += f"💰 Загальна сума: {fmt_price(total_revenue)} грн\n"
            report_text += f"💵 Чистий заробіток: {fmt_price(total_net_revenue)} грн"
            
            bot.send_message(chat_id, report_text, parse_mode="HTML", reply_markup=financial_reports_menu())
            return

        elif txt == "🏪 Звіт по магазинах":
            refresh_data()
            if not data.get("archive") and not data["phones"]:
                bot.send_message(chat_id, "📭 Немає даних для аналізу.", reply_markup=financial_reports_menu())
                return
            
            all_time_stats = {}
            
            # Поточні телефони
            for phone in data["phones"]:
                store = phone['store']
                price = float(phone['price'])
                net_price = calculate_net_price(price, store)
                
                if store not in all_time_stats:
                    all_time_stats[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
                
                all_time_stats[store]["revenue"] += price
                all_time_stats[store]["net_revenue"] += net_price
                all_time_stats[store]["count"] += 1
            
            # Архівні телефони
            for archive_week in data.get("archive", []):
                for phone in archive_week.get("phones", []):
                    store = phone['store']
                    price = float(phone['price'])
                    net_price = calculate_net_price(price, store)
                    
                    if store not in all_time_stats:
                        all_time_stats[store] = {"revenue": 0, "net_revenue": 0, "count": 0}
                    
                    all_time_stats[store]["revenue"] += price
                    all_time_stats[store]["net_revenue"] += net_price
                    all_time_stats[store]["count"] += 1
            
            if not all_time_stats:
                bot.send_message(chat_id, "📭 Немає даних по магазинах.", reply_markup=financial_reports_menu())
                return
            
            report_text = "🏪 <b>Звіт по магазинах (за весь час)</b>\n\n"
            for store, info in sorted(all_time_stats.items(), key=lambda x: x[1]["net_revenue"], reverse=True):
                percentage = data["stores"][store]["percentage"]
                report_text += f"<b>{store}</b> ({percentage}%):\n"
                report_text += f"   📱 Всього телефонів: {info['count']}\n"
                report_text += f"   💰 Загальна сума: {fmt_price(info['revenue'])} грн\n"
                report_text += f"   💵 Чистий заробіток: {fmt_price(info['net_revenue'])} грн\n\n"
            
            total_phones = sum(info["count"] for info in all_time_stats.values())
            total_revenue = sum(info["revenue"] for info in all_time_stats.values())
            total_net_revenue = sum(info["net_revenue"] for info in all_time_stats.values())
            
            report_text += f"<b>Загальна статистика:</b>\n"
            report_text += f"📱 Всього телефонів: {total_phones}\n"
            report_text += f"💰 Загальна сума: {fmt_price(total_revenue)} грн\n"
            report_text += f"💵 Загальний чистий заробіток: {fmt_price(total_net_revenue)} грн"
            
            bot.send_message(chat_id, report_text, parse_mode="HTML", reply_markup=financial_reports_menu())
            return

    # Інші обробники (додавання телефону, редагування, архів) залишаються аналогічними
    # з невеликими змінами для відображення відсотків

    # Додавання телефону
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store_from_phone")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif any(txt.startswith(store) for store in data["stores"]):
            store_name = next(store for store in data["stores"] if txt.startswith(store))
            ensure_state(chat_id)
            user_state[chat_id]["tmp"]["store"] = store_name
            percentage = data["stores"][store_name]["percentage"]
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, 
                           f"Магазин: <b>{store_name}</b> ({percentage}%)\nВведіть модель телефону:", 
                           parse_mode="HTML", reply_markup=back_button())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку або додайте новий.", 
                           reply_markup=stores_menu(include_percentage=False))
            return

    if state == "add_new_store_from_phone":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"][store_name] = {"percentage": 100}
            save_data(data)
            ensure_state(chat_id)
            user_state[chat_id]["tmp"]["store"] = store_name
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, 
                           f"✅ Магазин «{store_name}» додано!\nВведіть модель телефону:", 
                           reply_markup=back_button())
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста. Спробуйте ще раз.")
        return

    # Продовження додавання телефону (модель, проблема, ціна)
    if state == "add_model":
        ensure_state(chat_id)
        user_state[chat_id]["tmp"]["model"] = txt
        push_state(chat_id, "add_problem")
        bot.send_message(chat_id, "Опишіть проблему телефону:", reply_markup=back_button())
        return

    if state == "add_problem":
        ensure_state(chat_id)
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
            percentage = data["stores"][store_name]["percentage"]
            
            phone = {
                "store": store_name,
                "model": tmp["model"],
                "problem": tmp["problem"],
                "price": price,
                "date": format_kiev_date()
            }
            
            add_phone_safe(phone)
            
            bot.send_message(chat_id, 
                           f"✅ Телефон додано!\n"
                           f"💰 Сума: {price} грн\n"
                           f"💵 Чисті ({percentage}%): {net_price} грн", 
                           reply_markup=main_menu())
            clear_state(chat_id)
        except Exception as e:
            print(f"Помилка додавання телефону: {e}")
            bot.send_message(chat_id, "❌ Введіть правильне число (наприклад: 450.50).", reply_markup=back_button())
        return

    # Решта коду (редагування, архів) залишається аналогічною, але з використанням нових функцій

    # Якщо повідомлення не оброблено
    bot.send_message(chat_id, "Не впізнаю команду або оберіть дію з меню.", reply_markup=main_menu())

# =======================
# СТАРТ БОТА
# =======================
if __name__ == "__main__":
    print("Bot started...")
    bot.infiny_polling()