import os
import json
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "YOUR_BOT_TOKEN_HERE"
bot = TeleBot(TOKEN)
DATA_FILE = "data.json"

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    if not os.path.exists(DATA_FILE):
        return {"stores": ["It Center", "Леся", "Особисті"], "phones": [], "archive": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

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

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# МЕНЮ
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📱 Додати телефон", "📋 Переглянути телефони")
    kb.add("✏️ Редагувати / 🗑 Видалити", "📊 Підсумок")
    kb.add("🏪 Магазини", "📦 Архів")
    kb.add("📥 Перенести тиждень в архів")
    return kb

def back_button():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    return kb

def stores_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in data["stores"]:
        kb.add(s)
    kb.add("➕ Додати магазин")
    kb.add("⬅️ Назад")
    return kb

def edit_action_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✏️ Редагувати", "🗑 Видалити")
    kb.add("⬅️ Назад")
    return kb

def edit_field_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("Магазин", "Модель", "Проблема", "Ціна")
    kb.add("⬅️ Назад")
    return kb

def confirm_delete_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("✅ Так", "❌ Ні")
    return kb

def archive_week_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    weeks = sorted({(p["year"], p["week"]) for p in data["archive"]}, reverse=True)
    for year, week in weeks:
        kb.add(f"Тиждень {week} ({year})")
    kb.add("⬅️ Назад")
    return kb

# =======================
# СТАРТ
# =======================
@bot.message_handler(commands=["start"])
def cmd_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

# =======================
# ПЕРЕНЕСЕННЯ ТИЖНЯ В АРХІВ
# =======================
@bot.message_handler(func=lambda m: m.text == "📥 Перенести тиждень в архів")
def archive_week(message):
    chat_id = message.chat.id
    now = datetime.now()
    start_week = now - timedelta(days=7)

    to_archive = []
    for p in data["phones"]:
        phone_date = datetime.strptime(p["date"], "%d.%m.%Y %H:%M")
        if phone_date >= start_week:
            week_num = phone_date.isocalendar()[1]
            year = phone_date.year
            archived_phone = p.copy()
            archived_phone["week"] = week_num
            archived_phone["year"] = year
            to_archive.append(archived_phone)

    if not to_archive:
        bot.send_message(chat_id, "📭 За останній тиждень немає телефонів для архіву.", reply_markup=main_menu())
        return

    data["archive"].extend(to_archive)
    data["phones"] = [p for p in data["phones"] if datetime.strptime(p["date"], "%d.%m.%Y %H:%M") < start_week]
    save_data(data)

    bot.send_message(chat_id, f"📦 {len(to_archive)} ремонтів перенесено в архів!\n🆕 Новий тиждень почався.", reply_markup=main_menu())

# =======================
# ПЕРЕГЛЯД АРХІВУ
# =======================
@bot.message_handler(func=lambda m: m.text == "📦 Архів")
def choose_archive_week(message):
    chat_id = message.chat.id
    if not data["archive"]:
        bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
        return
    bot.send_message(chat_id, "Оберіть тиждень для перегляду:", reply_markup=archive_week_menu())
    push_state(chat_id, "archive_select_week")

@bot.message_handler(func=lambda m: current_state(m.chat.id) == "archive_select_week")
def show_archive_week(message):
    chat_id = message.chat.id
    txt = message.text
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return
    try:
        parts = txt.split()
        week_num = int(parts[1])
        year = int(parts[2].strip("()"))
    except:
        bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=archive_week_menu())
        return

    phones = [p for p in data["archive"] if p.get("week") == week_num and p.get("year") == year]
    if not phones:
        bot.send_message(chat_id, "📭 Телефонів за цей тиждень немає.", reply_markup=archive_week_menu())
        return

    text = f"📦 Архів: тиждень {week_num} ({year})\n\n"
    for i, p in enumerate(phones, 1):
        text += (f"{i}. {p['model']} ({p['store']})\n"
                 f"🔧 {p['problem']}\n"
                 f"💰 {p['price']} грн\n"
                 f"🕒 {p['date']}\n\n")
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("⬅️ Назад")
    bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "🗑 Очистити архів")
def clear_archive(message):
    chat_id = message.chat.id
    data["archive"].clear()
    save_data(data)
    bot.send_message(chat_id, "✅ Архів очищено.", reply_markup=main_menu())

# =======================
# ЗВІТИ
# =======================
def generate_report(period="week"):
    now = datetime.now()
    start = now - timedelta(days=7 if period=="week" else 30)
    phones = [p for p in data["phones"] if datetime.strptime(p["date"], "%d.%m.%Y %H:%M") >= start]
    total = sum(p["price"] for p in phones)
    count = len(phones)
    stores_summary = {}
    for p in phones:
        stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
    report = f"📊 Звіт за {period}:\n🔢 Кількість: {count}\n💰 Сума: {total} грн\n\n"
    report += "\n".join(f"• {s}: {v} грн" for s, v in stores_summary.items())
    return report

@bot.message_handler(func=lambda m: m.text in ["Тижневий звіт", "Місячний звіт"])
def report_handler(message):
    chat_id = message.chat.id
    period = "week" if message.text=="Тижневий звіт" else "month"
    bot.send_message(chat_id, generate_report(period), parse_mode="HTML", reply_markup=main_menu())

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК ТЕЛЕФОНІВ
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text
    state = current_state(chat_id)

    # -----------------------
    # ГОЛОВНЕ МЕНЮ
    # -----------------------
    if txt == "📋 Переглянути телефони":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        text = "📋 <b>Список телефонів:</b>\n\n"
        for i,p in enumerate(data["phones"],1):
            text += f"{i}. {p['model']} ({p['store']})\n🔧 {p['problem']}\n💰 {p['price']} грн\n🕒 {p['date']}\n\n"
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "🏪 Магазини":
        text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "⬅️ Назад":
        pop_state(chat_id)
        state = current_state(chat_id)
        if not state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        return

    # =======================
    # ДОДАВАННЯ
    # =======================
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt in data["stores"]:
            user_state[chat_id]["tmp"]["store"] = txt
            push_state(chat_id, "add_model")
            bot.send_message(chat_id, "Введіть модель телефону:", reply_markup=back_button())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку або додайте новий.", reply_markup=stores_menu())
            return

    if state == "add_new_store":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"].append(store_name)
            save_data(data)
            bot.send_message(chat_id, f"✅ Магазин «{store_name}» додано!", reply_markup=main_menu())
            clear_state(chat_id)
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста.", reply_markup=back_button())
        pop_state(chat_id)
        return

    if state == "add_model":
        user_state[chat_id]["tmp"]["model"] = txt
        push_state(chat_id, "add_problem")
        bot.send_message(chat_id, "Опишіть проблему телефону:", reply_markup=back_button())
        return

    if state == "add_problem":
        user_state[chat_id]["tmp"]["problem"] = txt
        push_state(chat_id, "add_price")
        bot.send_message(chat_id, "Вкажіть ціну ремонту:", reply_markup=back_button())
        return

    if state == "add_price":
        try:
            price = float(txt)
            user_state[chat_id]["tmp"]["price"] = price
            phone = {
                "store": user_state[chat_id]["tmp"]["store"],
                "model": user_state[chat_id]["tmp"]["model"],
                "problem": user_state[chat_id]["tmp"]["problem"],
                "price": price,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            data["phones"].append(phone)
            save_data(data)
            bot.send_message(chat_id, "✅ Телефон додано!", reply_markup=main_menu())
            clear_state(chat_id)
        except ValueError:
            bot.send_message(chat_id, "❌ Введіть правильне число.", reply_markup=back_button())
        return

    # =======================
    # РЕДАГУВАННЯ / ВИДАЛЕННЯ
    # =======================
    field_map = {"Магазин":"store","Модель":"model","Проблема":"problem","Ціна":"price"}

    if state == "edit_select":
        try:
            idx = int(txt.split(".")[0])-1
            if 0<=idx<len(data["phones"]):
                user_state[chat_id]["tmp"]["edit_idx"]=idx
                push_state(chat_id,"edit_action")
                bot.send_message(chat_id,"Обрати дію:", reply_markup=edit_action_menu())
            else:
                bot.send_message(chat_id,"❌ Невірний вибір.", reply_markup=back_button())
        except:
            bot.send_message(chat_id,"❌ Невірний вибір.", reply_markup=back_button())
        return

    if state=="edit_action":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        if txt=="✏️ Редагувати":
            push_state(chat_id,"edit_field")
            bot.send_message(chat_id,"Що редагуємо?", reply_markup=edit_field_menu())
        elif txt=="🗑 Видалити":
            push_state(chat_id,"confirm_delete")
            bot.send_message(chat_id,f"Видалити {data['phones'][idx]['model']}?", reply_markup=confirm_delete_menu())
        return

    if state=="edit_field":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        user_state[chat_id]["tmp"]["field"]=txt
        push_state(chat_id,"edit_enter")
        bot.send_message(chat_id,f"Введіть нове значення для {txt}:", reply_markup=back_button())
        return

    if state=="edit_enter":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        field = user_state[chat_id]["tmp"]["field"]
        value = txt
        if field=="Ціна":
            try:
                value=float(value)
            except:
                bot.send_message(chat_id,"❌ Введіть число.", reply_markup=back_button())
                return
        elif field=="Магазин":
            if value not in data["stores"]:
                data["stores"].append(value)
        key = field_map[field]
        data["phones"][idx][key]=value
        save_data(data)
        bot.send_message(chat_id,f"✅ {field} оновлено!", reply_markup=main_menu())
        clear_state(chat_id)
        return

    if state=="confirm_delete":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        if txt=="✅ Так":
            removed = data["phones"].pop(idx)
            save_data(data)
            bot.send_message(chat_id,f"🗑 Телефон {removed['model']} видалено!", reply_markup=main_menu())
        else:
            bot.send_message(chat_id,"❌ Скасовано.", reply_markup=main_menu())
        clear_state(chat_id)
        return

# =======================
# СТАРТ БОТА
# =======================
bot.infinity_polling()