# bot_weekly_archive.py
import os
import json
from datetime import datetime, timedelta
from telebot import TeleBot, types

# =======================
# НАЛАШТУВАННЯ
# =======================
TOKEN = os.getenv("BOT_TOKEN") or "8494392250:AAFpY_MbOCw0psxn6yefA3b-s_83gGPKoLc"
bot = TeleBot(TOKEN)
DATA_FILE = "data.json"
DATE_FORMAT = "%d.%m.%Y %H:%M"

# =======================
# Початкові дані за замовчуванням
# =======================
DEFAULT_DATA = {
    "stores": ["It Center", "Леся", "Особисті"],
    # current_week_key зберігає назву активного тижня "Тиждень dd.mm.yyyy — dd.mm.yyyy"
    "current_week_key": None,
    # weeks: словник, в якому ключ = current_week_key, значення = список телефонів (тільки активний)
    "weeks": {},
    # archive: містить всі завершені тижні { "Тиждень ...": [phones...] }
    "archive": {}
}

# =======================
# ЗАВАНТАЖЕННЯ / ЗБЕРЕЖЕННЯ ДАНИХ
# =======================
def load_data():
    if not os.path.exists(DATA_FILE):
        d = DEFAULT_DATA.copy()
        # Ініціалізувати поточний тиждень
        current_key = get_week_label_for_date(datetime.now().date())
        d["current_week_key"] = current_key
        d["weeks"] = {current_key: []}
        save_data(d)
        return d

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        try:
            d = json.load(f)
        except json.JSONDecodeError:
            # якщо файл пошкоджений — створити новий
            d = DEFAULT_DATA.copy()
            current_key = get_week_label_for_date(datetime.now().date())
            d["current_week_key"] = current_key
            d["weeks"] = {current_key: []}
            save_data(d)
            return d

    # Якщо старий формат (наприклад, є "phones" без розбиття) — мігруємо
    if "phones" in d and ("weeks" not in d and "archive" not in d):
        d = migrate_old_flat_data(d)
    # Забезпечити наявність всіх ключів
    for k in DEFAULT_DATA:
        if k not in d:
            d[k] = DEFAULT_DATA[k] if k != "current_week_key" else None

    # Переконатися, що current_week_key існує і в weeks є цей ключ
    if not d.get("current_week_key"):
        current_key = get_week_label_for_date(datetime.now().date())
        d["current_week_key"] = current_key
    if d.get("current_week_key") not in d.get("weeks", {}):
        # створити порожній список для поточного тижня
        if "weeks" not in d:
            d["weeks"] = {}
        d["weeks"][d["current_week_key"]] = []

    save_data(d)
    return d

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def migrate_old_flat_data(d_old):
    """
    Міграція зі структури:
    { "stores": [...], "phones": [...] }
    в нову структуру DEFAULT_DATA з поточним тижнем.
    """
    d = DEFAULT_DATA.copy()
    # збережемо магазини якщо були
    if "stores" in d_old:
        d["stores"] = d_old["stores"]
    # Створюємо поточний тиждень
    current_key = get_week_label_for_date(datetime.now().date())
    d["current_week_key"] = current_key
    d["weeks"] = {current_key: []}
    d["archive"] = {}
    phones = d_old.get("phones", [])
    # помістити всі старі телефони в поточний тиждень
    d["weeks"][current_key] = phones
    save_data(d)
    return d

# =======================
# ДОПОМОЖНІ ФУНКЦІЇ ДАТ ТА ТИЖНІВ
# =======================
def get_week_start(date_obj):
    """
    Повертає дату початку тижня (понеділок) для given date_obj (date)
    """
    # date_obj - datetime.date
    weekday = date_obj.weekday()  # 0 = Monday
    start = date_obj - timedelta(days=weekday)
    return start

def get_week_end(date_obj):
    """
    Повертає дату кінця тижня (неділя) для given date_obj (date)
    """
    start = get_week_start(date_obj)
    end = start + timedelta(days=6)
    return end

def date_to_str(d):
    return d.strftime("%d.%m.%Y")

def get_week_label_for_date(date_obj):
    """
    Повертає рядок: "Тиждень dd.mm.yyyy — dd.mm.yyyy"
    для тижня, що містить date_obj
    """
    start = get_week_start(date_obj)
    end = get_week_end(date_obj)
    return f"Тиждень {date_to_str(start)} — {date_to_str(end)}"

def ensure_current_week_exists(data):
    """
    Перевіряє current_week_key і створює тиждень, якщо його немає.
    """
    cur_key = data.get("current_week_key")
    if not cur_key:
        cur_key = get_week_label_for_date(datetime.now().date())
        data["current_week_key"] = cur_key
    if cur_key not in data.get("weeks", {}):
        if "weeks" not in data:
            data["weeks"] = {}
        data["weeks"][cur_key] = []
    return data

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
        return user_state[chat_id]["stack"].pop()
    return None

def current_state(chat_id):
    ensure_state(chat_id)
    return user_state[chat_id]["stack"][-1] if user_state[chat_id]["stack"] else None

def clear_state(chat_id):
    user_state[chat_id] = {"stack": [], "tmp": {}}

# =======================
# ЗАВАНТАЖИМО ДАНІ В ПАМ'ЯТЬ
# =======================
data = load_data()
ensure_current_week_exists(data)

# =======================
# Keyboards
# =======================
def main_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.row("📱 Додати телефон", "📋 Переглянути телефони")
    kb.row("📊 Підсумок за тиждень", "📅 Підсумок за місяць")
    kb.row("✏️ Редагувати / 🗑 Видалити", "🧹 Почати новий тиждень")
    kb.row("🏪 Магазини")
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

def view_choice_menu():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📅 Поточний тиждень", "📦 Архів")
    kb.add("⬅️ Назад")
    return kb

# =======================
# START
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
    ensure_current_week_exists(data)
    push_state(chat_id, "add_store")
    bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())

# =======================
# РЕДАГУВАННЯ / ВИДАЛЕННЯ (тільки поточний тиждень)
# =======================
@bot.message_handler(func=lambda m: m.text == "✏️ Редагувати / 🗑 Видалити")
def edit_phone_start(message):
    chat_id = message.chat.id
    ensure_current_week_exists(data)
    cur_key = data["current_week_key"]
    phones = data["weeks"].get(cur_key, [])
    if not phones:
        bot.send_message(chat_id, "📭 Телефонів у поточному тижні немає.", reply_markup=main_menu())
        return
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for i, p in enumerate(phones, 1):
        kb.add(f"{i}. {p['model']} ({p['store']})")
    kb.add("⬅️ Назад")
    push_state(chat_id, "edit_select")
    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", reply_markup=kb)

# =======================
# ГЕНЕРИЧНИЙ ОБРОБНИК
# =======================
field_map = {"Магазин": "store", "Модель": "model", "Проблема": "problem", "Ціна": "price"}

@bot.message_handler(func=lambda m: True)
def generic_handler(message):
    chat_id = message.chat.id
    txt = message.text.strip() if message.text else ""
    state = current_state(chat_id)

    # ГОЛОВНЕ МЕНЮ КОМАНДИ
    if txt == "📋 Переглянути телефони":
        push_state(chat_id, "view_choice")
        bot.send_message(chat_id, "Показати телефони:", reply_markup=view_choice_menu())
        return

    if txt == "📊 Підсумок за тиждень":
        ensure_current_week_exists(data)
        cur_key = data["current_week_key"]
        phones = data["weeks"].get(cur_key, [])
        if not phones:
            bot.send_message(chat_id, "📭 Телефонів у поточному тижні немає.", reply_markup=main_menu())
            return
        total = sum(p["price"] for p in phones)
        count = len(phones)
        stores_summary = {}
        for p in phones:
            stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
        store_text = "\n".join(f"• {s}: {v} грн" for s, v in stores_summary.items())
        bot.send_message(chat_id,
                         f"📊 Підсумок — {cur_key}\n🔢 Кількість: {count}\n💰 Сума: {total} грн\n\n<b>По магазинах:</b>\n{store_text}",
                         parse_mode="HTML", reply_markup=main_menu())
        return

    if txt == "📅 Підсумок за місяць":
        ensure_current_week_exists(data)
        # збираємо всі телефони з archive + поточний тиждень, які відносяться до поточного місяця
        now = datetime.now().date()
        month = now.month
        year = now.year
        total = 0
        count = 0
        stores_summary = {}
        # архів
        for week_label, phones in data.get("archive", {}).items():
            # витягнути діапазон дат з ярлика "Тиждень dd.mm.yyyy — dd.mm.yyyy"
            try:
                dates_part = week_label.replace("Тиждень ", "")
                start_str, end_str = [s.strip() for s in dates_part.split("—")]
                start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
                # if any date in that week is in the month -> враховуємо весь тиждень
                if start_date.month == month and start_date.year == year:
                    for p in phones:
                        total += p["price"]
                        count += 1
                        stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
            except Exception:
                # якщо формат інший — просто ігноруємо
                continue
        # поточний тиждень
        cur_key = data["current_week_key"]
        if cur_key:
            # отримати старт тижня
            try:
                dates_part = cur_key.replace("Тиждень ", "")
                start_str, end_str = [s.strip() for s in dates_part.split("—")]
                start_date = datetime.strptime(start_str, "%d.%m.%Y").date()
                if start_date.month == month and start_date.year == year:
                    for p in data["weeks"].get(cur_key, []):
                        total += p["price"]
                        count += 1
                        stores_summary[p["store"]] = stores_summary.get(p["store"], 0) + p["price"]
            except Exception:
                pass

        if count == 0:
            bot.send_message(chat_id, "📭 Немає записів за поточний місяць.", reply_markup=main_menu())
            return
        store_text = "\n".join(f"• {s}: {v} грн" for s, v in stores_summary.items())
        bot.send_message(chat_id,
                         f"📅 Підсумок за {now.strftime('%B %Y')}\n🔢 Кількість: {count}\n💰 Сума: {total} грн\n\n<b>По магазинах:</b>\n{store_text}",
                         parse_mode="HTML", reply_markup=main_menu())
        return

    if txt == "🏪 Магазини":
        text = "🏪 <b>Список магазинів:</b>\n" + "\n".join(f"• {s}" for s in data["stores"])
        bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
        return

    if txt == "🧹 Почати новий тиждень":
        # перенести поточні телефони в archive під ключ "Тиждень dd.mm.yyyy — dd.mm.yyyy"
        ensure_current_week_exists(data)
        cur_key = data["current_week_key"]
        phones = data["weeks"].get(cur_key, [])
        # створити ярлик нового архівного ключа (вже cur_key)
        if phones:
            data["archive"][cur_key] = phones
        # створити новий current_week_key (для поточної дати)
        # Новий тиждень завжди починається з понеділка поточної дати
        today = datetime.now().date()
        new_key = get_week_label_for_date(today)
        # якщо new_key == cur_key (наприклад, переходиш в середині тижня) — треба наступний тиждень
        if new_key == cur_key:
            # пересунути вперед на 7 днів
            next_monday = get_week_start(today) + timedelta(days=7)
            new_key = get_week_label_for_date(next_monday)
        data["current_week_key"] = new_key
        data["weeks"][new_key] = []
        # видалити старий тиждень зі weeks (щоб weeks містив лише активний)
        if cur_key in data["weeks"]:
            data["weeks"].pop(cur_key, None)
        save_data(data)
        bot.send_message(chat_id, f"✅ Поточний тиждень збережено в архів як:\n<b>{cur_key}</b>\nСтворено новий тиждень:\n<b>{new_key}</b>", parse_mode="HTML", reply_markup=main_menu())
        return

    # -----------------------
    # НАЗАД
    # -----------------------
    if txt == "⬅️ Назад":
        prev = pop_state(chat_id)
        state = current_state(chat_id)
        # Відправити відповідну клавіатуру залежно від state
        if not state:
            bot.send_message(chat_id, "Повертаємося в головне меню.", reply_markup=main_menu())
        else:
            # якщо ми повернулись у вибір перегляду
            if state == "add_store":
                bot.send_message(chat_id, "Оберіть магазин:", reply_markup=stores_menu())
            elif state == "add_model":
                bot.send_message(chat_id, "Введіть модель телефону:", reply_markup=back_button())
            elif state == "edit_select":
                # показати список телефонів поточного тижня
                cur_key = data["current_week_key"]
                phones = data["weeks"].get(cur_key, [])
                if phones:
                    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    for i, p in enumerate(phones, 1):
                        kb.add(f"{i}. {p['model']} ({p['store']})")
                    kb.add("⬅️ Назад")
                    bot.send_message(chat_id, "Оберіть телефон для редагування або видалення:", reply_markup=kb)
                else:
                    bot.send_message(chat_id, "📭 Телефонів у поточному тижні немає.", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "Повернуто.", reply_markup=main_menu())
        return

    # =======================
    # ДОДАВАННЯ ТЕЛЕФОНУ (стани)
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
        bot.send_message(chat_id, "Вкажіть ціну ремонту (числом):", reply_markup=back_button())
        return

    if state == "add_price":
        try:
            # дозволяємо числа з десятковими або цілими
            price = float(txt.replace(",", "."))
            user_state[chat_id]["tmp"]["price"] = price
            # створюємо запис і додаємо до поточного тижня
            cur_key = data["current_week_key"]
            if not cur_key:
                cur_key = get_week_label_for_date(datetime.now().date())
                data["current_week_key"] = cur_key
            phone = {
                "store": user_state[chat_id]["tmp"]["store"],
                "model": user_state[chat_id]["tmp"]["model"],
                "problem": user_state[chat_id]["tmp"]["problem"],
                "price": price,
                "date": datetime.now().strftime(DATE_FORMAT)
            }
            if "weeks" not in data:
                data["weeks"] = {}
            if cur_key not in data["weeks"]:
                data["weeks"][cur_key] = []
            data["weeks"][cur_key].append(phone)
            save_data(data)
            bot.send_message(chat_id, "✅ Телефон додано!", reply_markup=main_menu())
            clear_state(chat_id)
        except ValueError:
            bot.send_message(chat_id, "❌ Введіть коректне число (наприклад 1200 або 1200.50).", reply_markup=back_button())
        return

    # =======================
    # ПЕРЕГЛЯД (вибір поточного тижня або архіву)
    # =======================
    if state == "view_choice":
        if txt == "📅 Поточний тиждень":
            ensure_current_week_exists(data)
            cur_key = data["current_week_key"]
            phones = data["weeks"].get(cur_key, [])
            if not phones:
                bot.send_message(chat_id, "📭 Телефонів у поточному тижні немає.", reply_markup=main_menu())
                clear_state(chat_id)
                return
            text = f"📋 <b>Телефони — {cur_key}:</b>\n\n"
            for i, p in enumerate(phones, 1):
                text += (f"{i}. {p['model']} ({p['store']})\n"
                         f"🔧 {p['problem']}\n"
                         f"💰 {p['price']} грн\n"
                         f"🕒 {p['date']}\n\n")
            bot.send_message(chat_id, text, parse_mode="HTML", reply_markup=main_menu())
            clear_state(chat_id)
            return
        elif txt == "📦 Архів":
            # показати короткий список тижнів (короткі звіти)
            if not data.get("archive"):
                bot.send_message(chat_id, "📭 Архів порожній.", reply_markup=main_menu())
                clear_state(chat_id)
                return
            kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
            # сортувати архів за датою початку (останній вгорі)
            entries = []
            for week_label, phones in data["archive"].items():
                # підрахунок
                cnt = len(phones)
                total = sum(p["price"] for p in phones) if phones else 0
                entries.append((week_label, cnt, total))
            # сортування по даті початку: розбір дати з рядка
            def parse_start(label):
                try:
                    dates_part = label.replace("Тиждень ", "")
                    start_str, _ = [s.strip() for s in dates_part.split("—")]
                    return datetime.strptime(start_str, "%d.%m.%Y")
                except:
                    return datetime.min
            entries.sort(key=lambda x: parse_start(x[0]), reverse=True)
            for week_label, cnt, total in entries:
                kb.add(f"{week_label} — {cnt} од., {int(total)} грн")
            kb.add("⬅️ Назад")
            push_state(chat_id, "archive_list")
            bot.send_message(chat_id, "Виберіть тиждень (короткий звіт):", reply_markup=kb)
            return
        else:
            bot.send_message(chat_id, "❌ Виберіть варіант.", reply_markup=view_choice_menu())
            return

    if state == "archive_list":
        # Коли користувач вибирає рядок архіву — показуємо короткий звіт без деталей
        # txt має формат "Тиждень dd.mm.yyyy — dd.mm.yyyy — X од., Y грн"
        parts = txt.split("—")
        if len(parts) >= 3:
            # знайдемо відповідний week_label у archive (пошук початкової частини)
            chosen_label = None
            for week_label in data.get("archive", {}):
                if week_label in txt:
                    chosen_label = week_label
                    break
            if chosen_label:
                phones = data["archive"][chosen_label]
                cnt = len(phones)
                total = sum(p["price"] for p in phones) if phones else 0
                # короткий звіт (без конкретних записів)
                bot.send_message(chat_id, f"📦 <b>{chosen_label}</b>\n🔢 Кількість: {cnt}\n💰 Сума: {int(total)} грн", parse_mode="HTML", reply_markup=main_menu())
                clear_state(chat_id)
                return
        bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # =======================
    # РЕДАГУВАННЯ / ВИДАЛЕННЯ (стани)
    # =======================
    if state == "edit_select":
        try:
            idx = int(txt.split(".")[0]) - 1
            cur_key = data["current_week_key"]
            phones = data["weeks"].get(cur_key, [])
            if 0 <= idx < len(phones):
                user_state[chat_id]["tmp"]["edit_idx"] = idx
                push_state(chat_id, "edit_action")
                bot.send_message(chat_id, "Обрати дію:", reply_markup=edit_action_menu())
            else:
                bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        except:
            bot.send_message(chat_id, "❌ Невірний вибір.", reply_markup=back_button())
        return

    if state == "edit_action":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        cur_key = data["current_week_key"]
        phones = data["weeks"].get(cur_key, [])
        if txt == "✏️ Редагувати":
            push_state(chat_id, "edit_field")
            bot.send_message(chat_id, "Що редагуємо?", reply_markup=edit_field_menu())
        elif txt == "🗑 Видалити":
            push_state(chat_id, "confirm_delete")
            bot.send_message(chat_id, f"Видалити {phones[idx]['model']}?", reply_markup=confirm_delete_menu())
        else:
            bot.send_message(chat_id, "❌ Оберіть дію.", reply_markup=edit_action_menu())
        return

    if state == "edit_field":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        user_state[chat_id]["tmp"]["field"] = txt
        push_state(chat_id, "edit_enter")
        bot.send_message(chat_id, f"Введіть нове значення для {txt}:", reply_markup=back_button())
        return

    if state == "edit_enter":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        field = user_state[chat_id]["tmp"]["field"]
        cur_key = data["current_week_key"]
        phones = data["weeks"].get(cur_key, [])
        if idx >= len(phones) or idx < 0:
            bot.send_message(chat_id, "❌ Телефон не знайдено.", reply_markup=main_menu())
            clear_state(chat_id)
            return
        value = txt
        if field == "Ціна":
            try:
                value_num = float(value.replace(",", "."))
                phones[idx]["price"] = value_num
            except:
                bot.send_message(chat_id, "❌ Введіть число.", reply_markup=back_button())
                return
        elif field == "Магазин":
            # якщо магазину немає в списку — додаємо
            if value not in data["stores"]:
                data["stores"].append(value)
            phones[idx]["store"] = value
        else:
            key = field_map.get(field)
            if key:
                phones[idx][key] = value
        # зберегти
        data["weeks"][cur_key] = phones
        save_data(data)
        bot.send_message(chat_id, f"✅ {field} оновлено!", reply_markup=main_menu())
        clear_state(chat_id)
        return

    if state == "confirm_delete":
        idx = user_state[chat_id]["tmp"]["edit_idx"]
        cur_key = data["current_week_key"]
        phones = data["weeks"].get(cur_key, [])
        if txt == "✅ Так":
            if 0 <= idx < len(phones):
                removed = phones.pop(idx)
                data["weeks"][cur_key] = phones
                save_data(data)
                bot.send_message(chat_id, f"🗑 Телефон {removed['model']} видалено!", reply_markup=main_menu())
            else:
                bot.send_message(chat_id, "❌ Телефон не знайдено.", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❌ Скасовано.", reply_markup=main_menu())
        clear_state(chat_id)
        return

    # Якщо нічого не спрацювало:
    bot.send_message(chat_id, "Я не зрозумів команду. Оберіть дію:", reply_markup=main_menu())

# =======================
# Запуск бота
# =======================
if __name__ == "__main__":
    print("Бот запущено...")
    bot.infinity_polling()