import os
import json
import threading
import re
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"  # <-- твій токен
DATA_FILE = "data.json"

bot = TeleBot(TOKEN)
data_lock = threading.Lock()

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ (з блокуванням)
# =======================
def load_data():
    with data_lock:
        if not os.path.exists(DATA_FILE):
            return {"stores": ["It Center", "Леся", "Особисті"], "phones": [], "archive": []}
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)

def save_data(d):
    with data_lock:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

data = load_data()

# =======================
# СТАН КОРИСТУВАЧА
# =======================
user_state = {}  # chat_id -> {"stack": [], "tmp": {}}
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
    # clear tmp if stack empty
    if not user_state[chat_id]["stack"]:
        user_state[chat_id]["tmp"] = {}

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# УТИЛІТИ ВІДОБРАЖЕННЯ
# =======================
def fmt_price(p):
    # показувати як ціле, якщо воно ціле
    try:
        if int(p) == p:
            return f"{int(p)}"
    except Exception:
        pass
    return f"{p}"

def phone_display(p):
    return (f"{p['model']} ({p['store']})\n"
            f"🔧 {p['problem']}\n"
            f"💰 {fmt_price(p['price'])} грн\n"
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

def stores_menu(include_add=True):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for s in data["stores"]:
        kb.add(s)
    if include_add:
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
    kb.add("🗑 Видалити тиждень", "⬅️ Назад")
    return kb

# клавіатура списку телефонів (для вибору по індексу)
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
    bot.send_message(chat_id, "Привіт! 👋\nОберіть дію:", reply_markup=main_menu())

# =======================
# ДОДАВАННЯ ТЕЛЕФОНУ (початок)
# =======================
@bot.message_handler(func=lambda m: m.text == "📱 Додати телефон")
def add_phone_start(message):
    chat_id = message.chat.id
    clear_state(chat_id)
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

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
    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", reply_markup=phones_list_keyboard(data["phones"]))

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК
# =======================
@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text.strip() if message.text else ""
    state = current_state(chat_id)

    # -----------------------
    # КНОПКИ ГОЛОВНОГО МЕНЮ
    # -----------------------
    if txt == "📋 Переглянути телефони":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        text = "📋 <b>Список телефонів:</b>\n\n"
        for i, p in enumerate(data["phones"], 1):
            text += (f"{i}. {phone_display(p)}\n\n")
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "📊 Підсумок":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає.", reply_markup=main_menu())
            return
        total = sum(float(p["price"]) for p in data["phones"])
        count = len(data["phones"])
        stores_summary = {}
        for p in data["phones"]:
            stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + float(p["price"])
        store_text = "\n".join(f"• {s}: {fmt_price(v)} грн" for s, v in stores_summary.items())
        bot.send_message(chat_id,
                         f"📊 Підсумок:\n🔢 Кількість телефонів: {count}\n💰 Загальна сума: {fmt_price(total)} грн\n\n<b>По магазинах:</b>\n{store_text}",
                         parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "🏪 Магазини":
        text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    elif txt == "🗂 Архів":
        if not data.get("archive"):
            bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
            return
        clear_state(chat_id)
        push_state(chat_id, "archive_select_week")
        bot.send_message(chat_id, "Оберіть тиждень:", reply_markup=archive_week_menu())
        return

    elif txt == "📝 Перенести тиждень в архів":
        if not data["phones"]:
            bot.send_message(chat_id, "📭 Телефонів немає для архіву.", reply_markup=main_menu())
            return
        week_str = datetime.now().strftime("%d.%m.%Y") + " - " + (datetime.now() + timedelta(days=6)).strftime("%d.%m.%Y")
        data.setdefault("archive", []).append({"week": week_str, "phones": data["phones"].copy()})
        data["phones"].clear()
        save_data(data)
        bot.send_message(chat_id, f"✅ Телефони перенесено в архів за тиждень {week_str}", reply_markup=main_menu())
        return

    # -----------------------
    # НАЗАД (універсально)
    # -----------------------
    if txt == "⬅️ Назад":
        pop_state(chat_id)
        new_state = current_state(chat_id)
        # якщо немає попереднього стану — показати головне меню
        if not new_state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "Повертаємося в попереднє меню.", reply_markup=main_menu())
            # (додаткової логіки не потрібно — користувач може почати заново)
        return

    # =======================
    # ДОДАВАННЯ ТЕЛЕФОНУ (ПОСТУПОВО)
    # =======================
    if state == "add_store":
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt in data["stores"]:
            ensure_state(chat_id)
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
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста. Спробуйте ще раз.", reply_markup=back_button())
        pop_state(chat_id)
        return

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
            phone = {
                "store": tmp["store"],
                "model": tmp["model"],
                "problem": tmp["problem"],
                "price": price,
                "date": datetime.now().strftime("%d.%m.%Y %H:%M")
            }
            data["phones"].append(phone)
            save_data(data)
            bot.send_message(chat_id, "✅ Телефон додано!", reply_markup=main_menu())
            clear_state(chat_id)
        except Exception:
            bot.send_message(chat_id, "❌ Введіть правильне число (наприклад: 450.50).", reply_markup=back_button())
        return

    # =======================
    # РЕДАГУВАННЯ / ВИДАЛЕННЯ (ВИБІР ТЕЛЕФОНУ)
    # =======================
    if state == "edit_select":
        # очікуємо вибір типу "1. Model (store)"
        m = re.match(r'^\s*(\d+)', txt)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(data["phones"]):
                ensure_state(chat_id)
                user_state[chat_id]["tmp"]["sel_index"] = idx
                push_state(chat_id, "edit_action")
                p = data["phones"][idx]
                bot.send_message(chat_id, f"Оберіть дію для:\n{phone_display(p)}", reply_markup=edit_action_menu())
            else:
                bot.send_message(chat_id, "❌ Невірний індекс. Оберіть телефон зі списку.", reply_markup=phones_list_keyboard(data["phones"]))
        else:
            bot.send_message(chat_id, "❌ Оберіть телефон зі списку (натисніть рядок зі списку).", reply_markup=phones_list_keyboard(data["phones"]))
        return

    # =======================
    # РЕДАГУВАННЯ / ВИДАЛЕННЯ (ДІЇ)
    # =======================
    if state == "edit_action":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if idx is None or idx >= len(data["phones"]):
            bot.send_message(chat_id, "❌ Помилка: телефон не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return

        if txt == "✏️ Редагувати":
            push_state(chat_id, "edit_field")
            bot.send_message(chat_id, f"Оберіть поле для редагування:\n{phone_display(data['phones'][idx])}", reply_markup=edit_field_menu())
            return

        if txt == "🗑 Видалити":
            push_state(chat_id, "confirm_delete")
            bot.send_message(chat_id, f"Ви дійсно хочете видалити цей телефон?\n{phone_display(data['phones'][idx])}", reply_markup=confirm_delete_menu())
            return

        if txt == "⬅️ Назад":
            pop_state(chat_id)
            pop_state(chat_id)
            bot.send_message(chat_id, "Повертаємось в головне меню.", reply_markup=main_menu())
            return

        bot.send_message(chat_id, "❌ Оберіть дію з клавіатури.", reply_markup=edit_action_menu())
        return

    # =======================
    # ПІДТВЕРДЖЕННЯ ВИДАЛЕННЯ З ГОЛОВНОГО СПИСКУ
    # =======================
    if state == "confirm_delete":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if txt == "✅ Так":
            if idx is not None and 0 <= idx < len(data["phones"]):
                removed = data["phones"].pop(idx)
                save_data(data)
                bot.send_message(chat_id, f"🗑 Телефон видалено:\n{phone_short(removed)}", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "❌ Помилка: телефон не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        elif txt == "❌ Ні":
            pop_state(chat_id)
            pop_state(chat_id)
            bot.send_message(chat_id, "Скасовано.", reply_markup=main_menu())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть ✅ Так або ❌ Ні.", reply_markup=confirm_delete_menu())
            return

    # =======================
    # РЕДАГУВАННЯ ПОЛІВ
    # =======================
    if state == "edit_field":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if txt == "Магазин":
            push_state(chat_id, "edit_field_store")
            bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())
            return
        if txt == "Модель":
            push_state(chat_id, "edit_field_model")
            bot.send_message(chat_id, "Введіть нову модель:", reply_markup=back_button())
            return
        if txt == "Проблема":
            push_state(chat_id, "edit_field_problem")
            bot.send_message(chat_id, "Опишіть нову проблему:", reply_markup=back_button())
            return
        if txt == "Ціна":
            push_state(chat_id, "edit_field_price")
            bot.send_message(chat_id, "Введіть нову ціну (числом):", reply_markup=back_button())
            return
        if txt == "⬅️ Назад":
            pop_state(chat_id)
            pop_state(chat_id)
            bot.send_message(chat_id, "Повертаємось в головне меню.", reply_markup=main_menu())
            return
        bot.send_message(chat_id, "❌ Оберіть поле з клавіатури.", reply_markup=edit_field_menu())
        return

    # редагування магазину (вибір або додати)
    if state == "edit_field_store":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if txt == "➕ Додати магазин":
            push_state(chat_id, "add_new_store_edit")
            bot.send_message(chat_id, "Введіть назву нового магазину:", reply_markup=back_button())
            return
        elif txt in data["stores"]:
            if idx is not None and 0 <= idx < len(data["phones"]):
                data["phones"][idx]["store"] = txt
                save_data(data)
                bot.send_message(chat_id, f"✅ Магазин оновлено для телефону:\n{phone_short(data['phones'][idx])}", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "❌ Помилка: телефон не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть магазин зі списку або додайте новий.", reply_markup=stores_menu())
            return

    # додавання нового магазину під час редагування
    if state == "add_new_store_edit":
        store_name = txt.strip()
        if store_name and store_name not in data["stores"]:
            data["stores"].append(store_name)
            # одразу оновлюємо магазин у вибраному телефоні
            idx = user_state[chat_id]["tmp"].get("sel_index")
            if idx is not None and 0 <= idx < len(data["phones"]):
                data["phones"][idx]["store"] = store_name
            save_data(data)
            bot.send_message(chat_id, f"✅ Магазин «{store_name}» додано і застосовано до телефону!", reply_markup=main_menu())
            clear_state(chat_id)
        else:
            bot.send_message(chat_id, "❌ Магазин вже існує або назва пуста. Введіть іншу назву.", reply_markup=back_button())
        return

    # редагування моделі
    if state == "edit_field_model":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if idx is not None and 0 <= idx < len(data["phones"]):
            data["phones"][idx]["model"] = txt
            save_data(data)
            bot.send_message(chat_id, f"✅ Модель оновлено:\n{phone_short(data['phones'][idx])}", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❌ Помилка при оновленні.", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # редагування проблеми
    if state == "edit_field_problem":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        if idx is not None and 0 <= idx < len(data["phones"]):
            data["phones"][idx]["problem"] = txt
            save_data(data)
            bot.send_message(chat_id, f"✅ Проблему оновлено:\n{phone_display(data['phones'][idx])}", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❌ Помилка при оновленні.", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # редагування ціни
    if state == "edit_field_price":
        idx = user_state[chat_id]["tmp"].get("sel_index")
        try:
            price = float(txt.replace(",", "."))
            if idx is not None and 0 <= idx < len(data["phones"]):
                data["phones"][idx]["price"] = price
                save_data(data)
                bot.send_message(chat_id, f"✅ Ціну оновлено:\n{phone_display(data['phones'][idx])}", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "❌ Помилка при оновленні.", reply_markup=main_menu())
        except Exception:
            bot.send_message(chat_id, "❌ Введіть правильне число (наприклад: 450 або 450.50).", reply_markup=back_button())
        clear_state(chat_id)
        return

    # =======================
    # РОБОТА З АРХІВОМ
    # =======================
    if state == "archive_select_week":
        # користувач обрав назву тижня
        weeks = [w["week"] for w in data.get("archive", [])]
        if txt in weeks:
            idx = weeks.index(txt)
            ensure_state(chat_id)
            user_state[chat_id]["tmp"]["archive_week_index"] = idx
            push_state(chat_id, "archive_view")
            bot.send_message(chat_id, f"Тиждень: {txt}\nОберіть дію:", reply_markup=archive_view_menu())
        else:
            bot.send_message(chat_id, "❌ Оберіть тиждень зі списку.", reply_markup=archive_week_menu())
        return

    if state == "archive_view":
        a_idx = user_state[chat_id]["tmp"].get("archive_week_index")
        if a_idx is None or a_idx >= len(data.get("archive", [])):
            bot.send_message(chat_id, "❌ Помилка: тиждень не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        week = data["archive"][a_idx]
        if txt == "🔽 Показати телефони":
            phones = week.get("phones", [])
            if not phones:
                bot.send_message(chat_id, "📭 Телефонів в цьому тижні немає.", reply_markup=archive_view_menu())
                return
            text = f"📋 <b>Телефони за тиждень {week['week']}:</b>\n\n"
            for i, p in enumerate(phones, 1):
                text += (f"{i}. {phone_display(p)}\n\n")
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=archive_view_menu())
            return

        if txt == "🔼 Відновити тиждень":
            phones = week.get("phones", [])
            data["phones"].extend(phones)
            # видалити тиждень з архіву
            data["archive"].pop(a_idx)
            save_data(data)
            bot.send_message(chat_id, f"✅ Тиждень {week['week']} відновлено повністю в поточний список.", reply_markup=main_menu())
            clear_state(chat_id)
            return

        if txt == "📤 Відновити телефон":
            phones = week.get("phones", [])
            if not phones:
                bot.send_message(chat_id, "📭 Телефонів для відновлення немає.", reply_markup=archive_view_menu())
                return
            push_state(chat_id, "archive_restore_select")
            bot.send_message(chat_id, "Оберіть телефон для відновлення:", reply_markup=phones_list_keyboard(phones))
            return

        if txt == "❌ Видалити телефон з архіву":
            phones = week.get("phones", [])
            if not phones:
                bot.send_message(chat_id, "📭 Телефонів для видалення немає.", reply_markup=archive_view_menu())
                return
            push_state(chat_id, "archive_delete_phone_select")
            bot.send_message(chat_id, "Оберіть телефон, який бажаєте видалити з архіву:", reply_markup=phones_list_keyboard(phones))
            return

        if txt == "🗑 Видалити тиждень":
            push_state(chat_id, "archive_delete_confirm")
            bot.send_message(chat_id, f"Ви дійсно хочете видалити тиждень {week['week']} з архіву? Це незворотньо.", reply_markup=confirm_delete_menu())
            return

        if txt == "⬅️ Назад":
            pop_state(chat_id)
            pop_state(chat_id)
            bot.send_message(chat_id, "Повертаємось в головне меню.", reply_markup=main_menu())
            return

        bot.send_message(chat_id, "❌ Оберіть дію з клавіатури.", reply_markup=archive_view_menu())
        return

    # відновлення одного телефону з архіву
    if state == "archive_restore_select":
        a_idx = user_state[chat_id]["tmp"].get("archive_week_index")
        if a_idx is None or a_idx >= len(data.get("archive", [])):
            bot.send_message(chat_id, "❌ Помилка: тиждень не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        week = data["archive"][a_idx]
        phones = week.get("phones", [])
        m = re.match(r'^\s*(\d+)', txt)
        if m:
            p_idx = int(m.group(1)) - 1
            if 0 <= p_idx < len(phones):
                phone = phones.pop(p_idx)
                data["phones"].append(phone)
                # якщо тиждень залишився порожнім - видаляємо його
                if not phones:
                    data["archive"].pop(a_idx)
                save_data(data)
                bot.send_message(chat_id, f"✅ Телефон відновлено:\n{phone_short(phone)}", reply_markup=main_menu())
                clear_state(chat_id)
            else:
                bot.send_message(chat_id, "❌ Невірний індекс. Оберіть телефон зі списку.", reply_markup=phones_list_keyboard(phones))
        else:
            bot.send_message(chat_id, "❌ Оберіть телефон зі списку (натисніть рядок).", reply_markup=phones_list_keyboard(phones))
        return

    # видалення одного телефону з архіву
    if state == "archive_delete_phone_select":
        a_idx = user_state[chat_id]["tmp"].get("archive_week_index")
        if a_idx is None or a_idx >= len(data.get("archive", [])):
            bot.send_message(chat_id, "❌ Помилка: тиждень не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        week = data["archive"][a_idx]
        phones = week.get("phones", [])
        m = re.match(r'^\s*(\d+)', txt)
        if m:
            p_idx = int(m.group(1)) - 1
            if 0 <= p_idx < len(phones):
                removed = phones.pop(p_idx)
                # якщо порожній тиждень - видалити його
                if not phones:
                    data["archive"].pop(a_idx)
                save_data(data)
                bot.send_message(chat_id, f"🗑 Телефон видалено з архіву:\n{phone_short(removed)}", reply_markup=main_menu())
                clear_state(chat_id)
            else:
                bot.send_message(chat_id, "❌ Невірний індекс. Оберіть телефон зі списку.", reply_markup=phones_list_keyboard(phones))
        else:
            bot.send_message(chat_id, "❌ Оберіть телефон зі списку (натисніть рядок).", reply_markup=phones_list_keyboard(phones))
        return

    # підтвердження видалення тижня
    if state == "archive_delete_confirm":
        a_idx = user_state[chat_id]["tmp"].get("archive_week_index")
        if txt == "✅ Так":
            if a_idx is not None and 0 <= a_idx < len(data.get("archive", [])):
                removed = data["archive"].pop(a_idx)
                save_data(data)
                bot.send_message(chat_id, f"🗑 Тиждень видалено з архіву: {removed['week']}", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "❌ Помилка: тиждень не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        elif txt == "❌ Ні":
            pop_state(chat_id)
            pop_state(chat_id)
            bot.send_message(chat_id, "Скасовано.", reply_markup=main_menu())
            return
        else:
            bot.send_message(chat_id, "❌ Оберіть ✅ Так або ❌ Ні.", reply_markup=confirm_delete_menu())
        return

    # якщо повідомлення не оброблено
    bot.send_message(chat_id, "Не впізнаю команду або оберіть дію з меню.", reply_markup=main_menu())

# =======================
# СТАРТ БОТА
# =======================
if __name__ == "__main__":
    print("Bot started...")
    bot.infinity_polling()