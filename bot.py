import json
import random
import os, copy
import time
from collections import Counter
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    Updater,
    PreCheckoutQueryHandler,
    CommandHandler,
    CallbackContext,
    CallbackQueryHandler,
    MessageHandler,
    Filters,
    InlineQueryHandler
)
pending_boss_fights = {}
loot = [
    "Картинки с футами🖼️👩",
    "BUTTPLUG. ⚔️",
    "Банан🍌",
    "Ключ🔑",
    "WWWWW🇼🇼🇼",
    "DILDO. 🍌",
    "Помидор🍅",
    "Картошка 🥔"
]


legendaryItems = [
    "🐟 РЫБА МЕЧ.",
    "👣 НОГИ.",
    "🥛 СТАКАН С СЕМЕНЕМ.",
    "🦠 ВИЧ.",
    "🤹 ШАРЫ.",
    "🥚 ДЕСЯТОК ЯИЧЕК.",
    "🏹 ЛУК.",
]


FOOD_ITEMS = ["Помидор🍅","Банан🍌", "Картошка 🥔"]

shop_prices = {
    "Картинки с футами🖼️👩": 15,
    "BUTTPLUG. ⚔️": 25,
    "Банан🍌": 5,
    "Ключ🔑": 20,
    "WWWWW🇼🇼🇼": 10,
    "DILDO. 🍌": 18,
    "Помидор🍅": 3,
    "ГРИЛЛЬ АППЕНДИКС. 🍗": 10,
    "Ножки Querope. 👣" : 100,
    "Зелье против ШЛЮХИ. 🧪": 50,
    "Защита от спизживания. 🛡️":100,
    "🏹 ЛУК.":500,
    "🧪 Зелье здоровья":1000,
    "🍀 ОТВАР УДАЧИ.":30000,
    "😈 ПРОКЛЯТИЕ.":15000
}


DATA_FILE = "user_data.json"
USERNAMES_FILE = "usernames.json"
COOLDOWN_SECONDS = 1
SKILLS_FILE = "skills.json"
CLANS_FILE = "clans.json"



MONSTERS = [
    {"name": "Слизень", "hp": 30, "attack": 5},
    {"name": "Гоблинская шлюшка", "hp": 50, "attack": 8},
    {"name": "Жирдяй.", "hp":400, "attack": 10},
    {"name": "Бандит.", "hp":100, "attack":5},
    {"name": "Большой Сайгон.", "hp":50, "attack":50},
    {"name": "(BOSS FIGHT!) ERNEST ERNEST.", "hp":1000, "attack":75}
]


battles = {}
pve_battle_states = {}

last_travel_times = {}
gift_states = {}
sell_states = {}
shop_states = {}
SKILL_INFO = {
    "power_strike": {
        "name": "Мощный удар",
        "description": "Увеличивает урон атаки на 1 HP за уровень.",
        "max_level": 2,
    },
    "fast_heal": {
        "name": "Быстрое лечение",
        "description": "Увеличивает лечение на 1 HP за уровень.",
        "max_level": 3,
    },
    "satisfy_master": {
        "name": "Мастер удовлетворения",
        "description": "Повышает шанс успеха \"УДОВЛЕТВОРИТЬ\" на 2% за уровень.",
        "max_level": 10,
    },
    "zhir_tres": {
        "name": "ЖИРТРЕС",
        "description": "Тратит меньше голода при путешествии (5% меньше за уровень).",
        "max_level": 5,
    },
    "shustry_gandonets": {
        "name": "ШУСТРЫЙ ГАНДОНЕЦ",
        "description": "Повышает шанс сбежать и избежать ограбления на 10% за уровень.",
        "max_level": 10,
    },
    "kozhanie_futa_yaica": {
        "name": "Большие кожаные фута яйца",
        "description": "Позволяет собирать больше предметов в путешествии (+5 предметов за уровень).",
        "max_level": 5,
    },
}





import random

def remove_items(user_items: dict, amount_to_remove: int) -> dict:
    total_items = sum(user_items.values())
    amount_to_remove = min(amount_to_remove, total_items)
    
    removed = 0
    items = user_items.copy()
    
    while removed < amount_to_remove and items:
        item = random.choice(list(items.keys()))
        if items[item] > 0:
            items[item] -= 1
            removed += 1
            if items[item] == 0:
                del items[item]
    return items


def load_skills():
    if not os.path.exists(SKILLS_FILE):
        with open(SKILLS_FILE, "w") as f:
            json.dump({}, f)
    with open(SKILLS_FILE, "r") as f:
        return json.load(f)

def save_skills(skills_data):
    with open(SKILLS_FILE, "w") as f:
        json.dump(skills_data, f, indent=2)

def get_user_skill_level(user_id: str, skill_id: str) -> int:
    skills_data = load_skills()
    user_skills = skills_data.get(user_id, {})
    return user_skills.get(skill_id, 0)


def get_upgrade_cost(current_level: int) -> int:
    next_level = current_level + 1
    return 500 * next_level

def upgrade_skill(user_id: str, skill_id: str, user_balance: int) -> tuple[bool, str, int]:
    """
    Tries to upgrade skill, returns (success, message, new_balance)
    """

    if skill_id not in SKILL_INFO:
        return False, "Такого навыка не существует.", user_balance

    current_level = get_user_skill_level(user_id, skill_id)
    max_level = SKILL_INFO[skill_id]["max_level"]
    
    if current_level >= max_level:
        return False, f"{SKILL_INFO[skill_id]['name']} уже максимального уровня.", user_balance

    cost = get_upgrade_cost(current_level)

    if user_balance < cost:
        return False, f"Недостаточно монет. Нужно {cost} монет для улучшения.", user_balance

    # Deduct cost and upgrade skill
    set_user_skill_level(user_id, skill_id, current_level + 1)
    new_balance = user_balance - cost

    return True, f"Навык {SKILL_INFO[skill_id]['name']} улучшен до уровня {current_level + 1}.", new_balance


def set_user_skill_level(user_id: str, skill_id: str, level: int):
    skills_data = load_skills()
    if user_id not in skills_data:
        skills_data[user_id] = {}
    skills_data[user_id][skill_id] = level
    save_skills(skills_data)

def init_user_skills(user_id: str):
    skills_data = load_skills()
    if user_id not in skills_data:
        skills_data[user_id] = {
            "power_strike": 0,
            "shield_master": 0,
            "fast_heal": 0,
            "satisfy_master": 0,
            "zhir_tres": 0,
            "shustry_gandonets": 0,
            "kozhanie_futa_yaica": 0
        }
        save_skills(skills_data)

def load_clans():
    if not os.path.exists(CLANS_FILE):
        with open(CLANS_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(CLANS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_clans(data):
    with open(CLANS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_data(filename):
    try:
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_data(data, filename):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_user_data():
    return load_data(DATA_FILE)

def save_user_data(data):
    save_data(data, DATA_FILE)

def load_usernames():
    return load_data(USERNAMES_FILE)



def save_usernames(data):
    save_data(data, USERNAMES_FILE)

def register_user(update: Update):
    user = update.effective_user
    usernames = load_usernames()
    if user.username:
        usernames[user.username.lower()] = user.id
        save_usernames(usernames)


def get_user_data(user_id, data):
    user = data.get(user_id)

    # If user data missing or not a dict, initialize it
    if not isinstance(user, dict):
        # Handle legacy data: if user data is a list of items, preserve it
        old_items = user if isinstance(user, list) else []
        data[user_id] = {
            "items": old_items,
            "balance": 0,
            "hunger": 100,
        }
        save_user_data(data)
        user = data[user_id]

    # If hunger key missing, initialize it
    if "hunger" not in user:
        user["hunger"] = 100
        save_user_data(data)

    # Ensure items and balance keys exist with defaults
    if "items" not in user:
        user["items"] = []
        save_user_data(data)
    if "balance" not in user:
        user["balance"] = 0
        save_user_data(data)

    return user["items"], user["balance"]


def get_clan_mates(user_id: str, clans: dict) -> list[str]:
    for clan_name, clan_info in clans.items():
        if user_id in clan_info.get("members", []):
            return [member for member in clan_info["members"] if member != user_id]
    return []


def save_user_inventory_and_balance(data, user_id, items, balance):
    data[user_id]["items"] = items
    data[user_id]["balance"] = max(0, balance)

def get_loot(amount):
    return [random.choice(loot) for _ in range(amount)]


def bonus_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user = data.setdefault(user_id, {"items": {}, "balance": 0, "hunger": 100})

    if user.get("bonus_claimed", False):
        update.message.reply_text("❌ Вы уже получили свой стартовый бонус.")
        return

    # Starter items and coins
    starter_items = ["Банан🍌"] * 4 + ["Помидор🍅"] * 4 + ["Ключ🔑"]
    starter_coins = random.randint(90, 110)

    user_items = user.setdefault("items", {})
    for item in starter_items:
        user_items[item] = user_items.get(item, 0) + 1


    user["balance"] += starter_coins
    user["bonus_claimed"] = True

    save_user_data(data)

    # Create readable summary
    items_summary = {}
    for item in starter_items:
        items_summary[item] = items_summary.get(item, 0) + 1

    items_text = "\n".join(f"{item} x{count}" for item, count in items_summary.items())

    update.message.reply_text(
        f"🎉 Поздравляем! Вы получили стартовый бонус:\n"
        f"{items_text}\n"
        f"💰 Монеты: {starter_coins}"
    )





def start(update: Update, context: CallbackContext):
    register_user(update)
    update.message.reply_text(
        "👋Здравствуйте. Это игра от шлюшки василиски))))) \n🦶Здесь вы увидите футфетиш. И прочие. Игры.\nИспользуйте /travel, /gift, /sell и /backpack чтобы делать различные ВЕСЕЛУНДЕЛИ.\n"
        "⌚Не забывайте использовать /daily чтобы получить бесплатную награду!\n"
        "🆕Также используйте /bonus если вы новичок чтобы ебануть себе бесплатную награду бл@ть."
    )

def backpack_command(update: Update, context: CallbackContext):
    register_user(update)
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user = data.get(user_id, {"items": {}, "balance": 0, "hunger": 100})

    # Migrate list inventories to dict on the fly
    if isinstance(user.get("items"), list):
        from collections import Counter
        user["items"] = dict(Counter(user["items"]))
        save_user_data(data)  # Save back migrated data

    items = user.get("items", {})
    balance = user.get("balance", 0)

    if not items:
        update.message.reply_text(f"🎒 Ваш рюкзак пока пуст.\n🪙 Баланс: {balance} монет.")
        return

    response = "🎒 Ваш рюкзак содержит:\n"
    for item, count in items.items():
        response += f"{item} x{count}\n"

    response += f"\n🪙 Баланс: {balance} монет."
    update.message.reply_text(response)


lock_states = {}


def travel_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    now = time.time()

    last_time = last_travel_times.get(user_id, 0)
    elapsed = now - last_time

    if elapsed < COOLDOWN_SECONDS:
        wait = int(COOLDOWN_SECONDS - elapsed)
        update.message.reply_text(f"⌛ Подождите {wait} секунд перед следующим путешествием.")
        return

    last_travel_times[user_id] = now

    data = load_user_data()
    user = data.setdefault(user_id, {"items": {}, "balance": 0, "hunger": 100})
    user_items = user.setdefault("items", {})

    if user["hunger"] < 10:
        update.message.reply_text("😣 Вы слишком голодны, чтобы путешествовать. Используйте /eat.")
        return

    hunger_loss = random.randint(15, 30)
    skill_level = get_user_skill_level(user_id, "zhir_tres")
    reduction_factor = max(0, 1 - 0.15 * skill_level)
    hunger_loss = int(hunger_loss * reduction_factor)
    user["hunger"] = max(0, user["hunger"] - hunger_loss)

    if random.random() < 0.15:
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Открыть (-1x Ключ🔑)", callback_data=f"lock_open|{user_id}"),
                InlineKeyboardButton("Уйти", callback_data=f"lock_leave|{user_id}")
            ]
        ])
        update.message.reply_text("🔒 Вы встретили замок!", reply_markup=keyboard)
        lock_states[user_id] = {"attempts": 0}
        save_user_data(data)
        return

    if random.random() < 0.15:
        if user_items.get("Защита от спизживания. 🛡️", 0) > 0:
            update.message.reply_text("На вас хотел напасть монстр, но у вас оказалось зелье защиты.")
            user_items["Защита от спизживания. 🛡️"] -= 1
            if user_items["Защита от спизживания. 🛡️"] <= 0:
                del user_items["Защита от спизживания. 🛡️"]
            save_user_data(data)
            return

        chance = min(1.0, get_user_skill_level(user_id, "shustry_gandonets") * 0.1)
        if random.random() < chance:
            update.message.reply_text("🐉 Вы избежали ебучего дракона и сбежали!")
            return

        if user_items:
            steal_items = []
            potential_items = list(user_items.keys())
            steal_amount = min(random.randint(3, 6), len(potential_items))

            for _ in range(steal_amount):
                item = random.choice(potential_items)
                user_items[item] -= 1
                steal_items.append(item)
                if user_items[item] <= 0:
                    del user_items[item]
                    potential_items.remove(item)

            save_user_data(data)

            stolen_summary = "🐉 Монстр украл у вас:\n"
            for item, count in Counter(steal_items).items():
                stolen_summary += f"{count}x {item}\n"
            stolen_summary += "Вы потеряли эти вещи навсегда. 😶‍🌫️"
            update.message.reply_text(stolen_summary)
        else:
            update.message.reply_text("🐉 Вам повезло, монстр не нашёл ничего, чтобы украсть!")
        return

    if random.random() < 0.4:
        monster_template = random.choice(MONSTERS)
        monster = copy.deepcopy(monster_template)
        monster["current_hp"] = monster["hp"]
        pve_battle_states[user_id] = {
            "monster": monster,
            "players": [{"id": user_id, "hp": 100, "blocking": False}],
            "turn_index": 0,
            "log": [],
        }
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚔️ Сразиться", callback_data="pve_start_battle")],
            [InlineKeyboardButton("🏃 Убежать", callback_data="pve_flee")]
        ])
        update.message.reply_text(
            f"👾 Вы встретили {monster['name']}!\n"
            f"У него {monster['hp']} HP и {monster['attack']} урона от атаки.\n\n"
            f"Что вы будете делать?",
            reply_markup=keyboard
        )
        save_user_data(data)
        return

    amount = random.randint(1, 5)
    loot = get_loot(amount)
    skill_level = get_user_skill_level(user_id, "kozhanie_futa_yaica")
    bonus_items = get_loot(skill_level * 5)
    loot.extend(bonus_items)

    for item in loot:
        user_items[item] = user_items.get(item, 0) + 1

    save_user_data(data)

    summary = "🚶‍➡️ Во время путешествия вы нашли:\n"
    for item, count in Counter(loot).items():
        summary += f"{count}x {item}\n"
    summary += f"\nГолод: {user['hunger']}"

    update.message.reply_text(summary)

    if random.random() < 0.2:
        item = random.choice(legendaryItems)
        user_items[item] = user_items.get(item, 0) + 1
        save_user_data(data)
        update.message.reply_text(f"✨ Вы нашли легендарный предмет: {item}!")

    if random.random() < 0.1:
        if not user_items:
            update.message.reply_text("❓ По пути домой вы ничего не потеряли, так как у вас нет предметов.")
        else:
            lost_items = []
            available_items = list(user_items.keys())
            num_to_lose = min(random.randint(5, 10), len(available_items))

            for _ in range(num_to_lose):
                item = random.choice(available_items)
                user_items[item] -= 1
                lost_items.append(item)
                if user_items[item] <= 0:
                    del user_items[item]
                    available_items.remove(item)

            save_user_data(data)

            lost_summary = "❓ По пути домой вы случайно потеряли:\n"
            for item, count in Counter(lost_items).items():
                lost_summary += f"{count}x {item}\n"
            update.message.reply_text(lost_summary)

def start_pve_battle_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user = data.setdefault(user_id, {})
    user["hp"] = 100  

    monster = random.choice(MONSTERS).copy()
    monster["current_hp"] = monster["hp"]

    # Save battle state
    pve_battle_states[user_id] = {
        "monster": monster
    }
    save_user_data(data)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡️ Атаковать", callback_data="pve_attack"),
         InlineKeyboardButton("🛡️ Блок", callback_data="pve_block")],
        [InlineKeyboardButton("❤️ Лечение", callback_data="pve_heal"),
         InlineKeyboardButton("🏃 Убежать", callback_data="pve_run")]
    ])

    update.message.reply_text(
        f"⚔️ Вы встретили {monster['name']}!\n"
        f"HP монстра: {monster['current_hp']}/{monster['hp']}\n"
        f"Ваш HP: {user['hp']}/100\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )
def pve_travel_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if query.data == "pve_start_battle":
        state = pve_battle_states.get(user_id)
        if not state:
            query.answer("❌ Нет активной битвы.")
            return

        data = load_user_data()
        data[user_id]["hp"]=100
        user = data.get(user_id, {})
        user_hp = user.get("hp", 100)
        monster = state.get("monster", {})
        monster_hp = monster.get("current_hp", monster.get("hp", 0))

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🗡️ Атаковать", callback_data="pve_attack")],
            [InlineKeyboardButton("🛡️ Блокировать", callback_data="pve_block")],
            [InlineKeyboardButton("💊 Лечиться", callback_data="pve_heal")]
        ])
        query.edit_message_text(
            f"⚔️ Битва с {monster.get('name','монстром')} началась!\n"
            f"Ваш HP: {user_hp}\n"
            f"{monster.get('name','Монстр')} HP: {monster_hp}\n\n"
            f"Ваш ход, выберите действие:",
            reply_markup=keyboard
        )
    elif query.data == "pve_flee":
        pve_battle_states.pop(user_id, None)
        query.edit_message_text("🏃 Вы убежали от монстра.")


def pve_battle_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = load_user_data()
    user = data.setdefault(user_id, {"hp": 100, "items": {}, "balance": 0})
    state = pve_battle_states.get(user_id)

    if not state:
        query.answer("❌ Нет активной битвы.")
        return

    monster = state["monster"]

    action = query.data

    player_action_text = ""
    log = ""

    if action == "pve_attack":
        dmg = random.randint(8, 18)
        monster["current_hp"] -= dmg
        player_action_text = f"🗡️ Вы нанесли {dmg} урона {monster['name']}."
    elif action == "pve_heal":
        heal = random.randint(10, 20)
        user["hp"] = min(100, user.get("hp", 100) + heal)
        player_action_text = f"❤️ Вы восстановили {heal} HP."
    elif action == "pve_block":
        player_action_text = "🛡️ Вы приготовились блокировать следующую атаку."
        state["block"] = True
    elif action == "pve_run":
        items = user.get("items", {})
        items_to_remove = min(100, sum(items.values()))
        user["items"] = remove_items(items, 100)
        coins_to_remove = min(100, user.get("balance", 0))
        user["balance"] = user.get("balance", 0) - coins_to_remove
        save_user_data(data)
        del pve_battle_states[user_id]
        query.edit_message_text(
            f"🏃 Вы сбежали из боя, но потеряли {items_to_remove} предметов и {coins_to_remove} монет."
        )
        return

    if monster["current_hp"] <= 0:
        del pve_battle_states[user_id]
        user["hp"]=100
        query.edit_message_text(
            f"{player_action_text}\n\n"
            f"🎉 Вы победили {monster['name']}!"
            
        )
        save_user_data(data)
        return

    monster_action = random.choices(
        ["attack", "attack", "heal", "miss"], weights=[0.45, 0.45, 0.05, 0.05], k=1
    )[0]

    if monster_action == "attack":
        dmg = random.randint(int(monster["attack"] * 0.5), monster["attack"])
        if state.get("block"):
            dmg = int(dmg * 0.3)
            log += "🛡️ Вы заблокировали часть урона.\n"
            state["block"] = False
        user["hp"] = max(0, user.get("hp", 100) - dmg)
        log += f"💥 {monster['name']} нанес вам {dmg} урона.\n"
    elif monster_action == "heal":
        heal = random.randint(5, 15)
        monster["current_hp"] = min(monster["hp"], monster["current_hp"] + heal)
        log += f"❤️ {monster['name']} восстановил {heal} HP.\n"
    else:
        log += f"😵 {monster['name']} промахнулся.\n"

    if user["hp"] <= 0:
        items_to_remove = random.randint(50, 150)
        removed = 0
        items = user.get("items", {})
        for item in list(items.keys()):
            if removed >= items_to_remove:
                break
            qty = items[item]
            to_remove = min(qty, items_to_remove - removed)
            items[item] -= to_remove
            removed += to_remove
            if items[item] <= 0:
                del items[item]
        user["items"] = items
        user["balance"] = max(0, user.get("balance", 0) - 100)
        del pve_battle_states[user_id]
        query.edit_message_text(
            f"{player_action_text}\n\n"
            f"{log}\n"
            f"💀 Вы проиграли битву и потеряли {removed} предметов и 100 🪙."
        )
        save_user_data(data)
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🗡️ Атаковать", callback_data="pve_attack"),
         InlineKeyboardButton("🛡️ Блок", callback_data="pve_block")],
        [InlineKeyboardButton("❤️ Лечение", callback_data="pve_heal"),
         InlineKeyboardButton("🏃 Убежать", callback_data="pve_run")]
    ])

    query.edit_message_text(
        f"{player_action_text}\n\n"
        f"{log}\n"
        f"HP монстра: {monster['current_hp']}/{monster['hp']}\n"
        f"Ваш HP: {user.get('hp', 100)}/100\n\n"
        f"Выберите действие:",
        reply_markup=keyboard
    )
    save_user_data(data)




key_offer_states = {}

def keys_offer_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)

    if query.data == f"keys_accept|{user_id}":
        data = load_user_data()
        if user_id in key_offer_states:
            offered_keys = key_offer_states.pop(user_id)
            data[user_id]["items"] = []
            data[user_id]["balance"] += offered_keys
            save_user_data(data)
            query.answer()
            query.edit_message_text(
                f"Вы трахнули шлюху, но она вас обокрала. Однако вам дали {offered_keys} монет."
            )
        else:
            query.answer()
            query.edit_message_text("Срок действия предложения истёк или оно недействительно.")

    elif query.data == f"keys_decline|{user_id}":
        if user_id in key_offer_states:
            key_offer_states.pop(user_id)
            query.answer()
            query.edit_message_text("Вы отказались и шлюха была недовольна.")
        else:
            query.answer()
            query.edit_message_text("Срок действия предложения истёк или оно недействительно.")

def lock_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = load_user_data()

    if user_id not in lock_states:
        query.answer()
        query.edit_message_text("⏳Событие замка уже завершено или неактивно.")
        return

    action = query.data.split("|")[0]

    if action == "lock_leave":
        query.answer()
        query.edit_message_text("Вы ушли от замка.")
        lock_states.pop(user_id, None)
        return

    if action == "lock_open":
        # Check if user has a key
        if user_id not in data or data[user_id]["items"].get("Ключ🔑", 0) <= 0:
            query.answer("❌У вас нет ключей для открытия замка.")
            return

        # Remove one key
        data[user_id]["items"]["Ключ🔑"] -= 1
        if data[user_id]["items"]["Ключ🔑"] == 0:
            del data[user_id]["items"]["Ключ🔑"]
        save_user_data(data)

        # 25% chance to open
        if random.random() < 0.25:
            amount = random.randint(20, 50)
            acquired = get_loot(amount)
            for item in acquired:
                data[user_id]["items"][item] = data[user_id]["items"].get(item, 0) + 1
            save_user_data(data)

            summary = "🔓 Вы открыли секрет. 🥇\nВы получили:\n"
            for item, count in Counter(acquired).items():
                summary += f"{count}x {item}\n"

            query.answer()
            query.edit_message_text(summary)
            lock_states.pop(user_id, None)
            return

        # If failed
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Открыть (-1x Ключ🔑)", callback_data=f"lock_open|{user_id}"),
                InlineKeyboardButton("Уйти", callback_data=f"lock_leave|{user_id}")
            ]
        ])
        query.answer("Заперто🔒Попробуйте другой ключ🔑❗")
        query.edit_message_text("Заперто🔒Попробуйте другой ключ🔑❗", reply_markup=keyboard)




def gift_command(update: Update, context: CallbackContext):
    register_user(update)
    args = context.args
    if not args or not args[0].startswith("@"):
        update.message.reply_text(
            "🤖Пожалуйста, укажите имя пользователя через @. Например:\n/gift @username или /gift @username coins"
        )
        return
    target_username = args[0][1:].lower()
    usernames = load_usernames()
    if target_username not in usernames:
        update.message.reply_text("❓Пользователь не найден или он ещё не взаимодействовал с ботом.")
        return
    user_id = str(update.effective_user.id)
    target_id = str(usernames[target_username])
    if user_id == target_id:
        update.message.reply_text("❌Вы не можете подарить вещи или монеты самому себе.")
        return
    data = load_user_data()
    user_data = data.get(user_id, {"items": {}, "balance": 0})
    items = user_data.get("items", {})
    balance = user_data.get("balance", 0)

    if len(args) > 1 and args[1].lower() == "coins":
        gift_states[user_id] = {"target_id": target_id, "item_selected": "coins"}
        update.message.reply_text(f"⁉️Введите количество монет для подарка пользователю @{target_username}:")
        return

    if not items:
        update.message.reply_text("❌Ваш рюкзак пуст, нечего дарить.")
        return

    keyboard = [
        [InlineKeyboardButton(f"{count}x {item}", callback_data=f"gift_select|{i}|{target_id}")]
        for i, (item, count) in enumerate(items.items())
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(f"📃Выберите предмет для подарка пользователю @{target_username}:", reply_markup=reply_markup)


def gift_select_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    try:
        _, index_str, target_id = query.data.split("|")
        index = int(index_str)
    except Exception:
        query.answer("❌Ошибка в данных кнопки.")
        return

    data = load_user_data()
    user_data = data.get(user_id, {"items": {}})
    items = user_data.get("items", {})
    items_list = list(items.keys())

    if index >= len(items_list):
        query.answer("❌Неверный выбор предмета.")
        return

    item = items_list[index]
    gift_states[user_id] = {"target_id": target_id, "item_selected": item}
    query.answer()
    query.edit_message_text(f"✅Вы выбрали: {item}\n⁉️Введите количество для подарка:")


def gift_amount_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id not in gift_states:
        return
    state = gift_states[user_id]
    item = state["item_selected"]
    target_id = state["target_id"]
    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("❓Пожалуйста, введите числовое значение количества.")
        return
    amount = int(text)
    if amount <= 0:
        update.message.reply_text("❓Количество должно быть положительным числом.")
        return

    data = load_user_data()
    usernames = load_usernames()

    if item == "coins":
        user_data = data.get(user_id, {"balance": 0})
        balance = user_data.get("balance", 0)
        if balance < amount:
            update.message.reply_text("❓У вас недостаточно монет для подарка.")
            return
        if target_id not in data:
            data[target_id] = {"items": {}, "balance": 0}
        data[user_id]["balance"] = balance - amount
        data[target_id]["balance"] = data[target_id].get("balance", 0) + amount
        save_user_data(data)
        sender_username = update.effective_user.username or "unknown"
        recipient_username = next((uname for uname, uid in usernames.items() if str(uid) == target_id), "unknown")
        gift_states.pop(user_id)
        update.message.reply_text(f"💰Вы подарили {amount} монет пользователю @{recipient_username}.")
        try:
            context.bot.send_message(int(target_id), f"💰Вы получили {amount} монет от @{sender_username}.")
        except:
            pass
        return

    user_data = data.get(user_id, {"items": {}, "balance": 0})
    items = user_data.get("items", {})
    if item not in items or items[item] < amount:
        update.message.reply_text(f"❓У вас нет столько {item} для подарка.")
        gift_states.pop(user_id)
        return

    if target_id not in data:
        data[target_id] = {"items": {}, "balance": 0}
    # Remove from sender
    items[item] -= amount
    if items[item] <= 0:
        del items[item]
    # Add to recipient
    recipient_items = data[target_id].setdefault("items", {})
    recipient_items[item] = recipient_items.get(item, 0) + amount

    save_user_data(data)
    gift_states.pop(user_id)

    sender_username = update.effective_user.username or "unknown"
    recipient_username = next((uname for uname, uid in usernames.items() if str(uid) == target_id), "unknown")

    update.message.reply_text(f"📦Вы подарили {amount}x {item} пользователю @{recipient_username}.")
    try:
        context.bot.send_message(int(target_id), f"📦Вы получили {amount}x {item} от @{sender_username}.")
    except:
        pass

def sell_command(update: Update, context: CallbackContext):
    register_user(update)
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user = data.get(user_id, {})
    items = user.get("items", {})

    if not items:
        update.message.reply_text("❌Ваш рюкзак пуст, нечего продавать.")
        return

    keyboard = []
    for i, (item, count) in enumerate(items.items()):
        keyboard.append([InlineKeyboardButton(f"{count}x {item}", callback_data=f"sell_select|{i}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("📃Выберите предмет для продажи:", reply_markup=reply_markup)


def sell_select_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    try:
        _, index_str = query.data.split("|")
        index = int(index_str)
    except Exception:
        query.answer("❌Ошибка в данных кнопки.")
        return

    data = load_user_data()
    user = data.get(user_id, {})
    items = user.get("items", {})
    items_list = list(items.keys())

    if index >= len(items_list):
        query.answer("❌Неверный выбор предмета.")
        return

    item = items_list[index]
    sell_states[user_id] = {"item_selected": item}
    query.answer()
    query.edit_message_text(f"✅Вы выбрали: {item}\n⁉️Введите количество для продажи:")


def sell_amount_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id not in sell_states:
        return

    state = sell_states[user_id]
    item = state["item_selected"]

    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("Введите корректное число.")
        return

    amount = int(text)
    if amount <= 0:
        update.message.reply_text("Количество должно быть положительным.")
        return

    data = load_user_data()
    user = data.get(user_id, {})
    items = user.get("items", {})

    if items.get(item, 0) < amount:
        update.message.reply_text("У вас недостаточно предметов для продажи.")
        return

    curse_count = user.get("curse", 0)
    luck_count = user.get("luck", 0)

    if curse_count > 0:
        price_per_item = 0
        user["curse"] -= 1
        if user["curse"] <= 0:
            del user["curse"]

    elif luck_count > 0:
        price_per_item = 10  # max price per your original 0-10 range
        user["luck"] -= 1
        if user["luck"] <= 0:
            del user["luck"]

    else:
        price_per_item = random.randint(0, 10)
        if item in legendaryItems:
            price_per_item = 5000

    total_price = price_per_item * amount

    # Subtract sold items
    items[item] -= amount
    if items[item] <= 0:
        del items[item]

    user["balance"] = user.get("balance", 0) + total_price
    save_user_data(data)
    sell_states.pop(user_id)

    if price_per_item > 0:
        update.message.reply_text(
            f"💰 Вы продали {amount}x {item} по цене {price_per_item} 🪙 за штуку.\n"
            f"Итого получено: {total_price} 🪙.\n"
            f"Ваш новый баланс: {user['balance']} 🪙."
        )
    else:
        update.message.reply_text(
            f"🏃😢 Вас обокрали, и вы потеряли {amount}x {item}"
        )


def eat_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()

    if user_id not in data or not isinstance(data[user_id], dict):
        data[user_id] = {"items": {}, "balance": 0, "hunger": 100}
    else:
        if "items" not in data[user_id] or not isinstance(data[user_id]["items"], dict):
            data[user_id]["items"] = {}
        if "balance" not in data[user_id]:
            data[user_id]["balance"] = 0
        if "hunger" not in data[user_id]:
            data[user_id]["hunger"] = 100

    hunger = data[user_id]["hunger"]
    inventory = data[user_id]["items"]

    grill_item = "ГРИЛЛЬ АППЕНДИКС. 🍗"
    potato = "Картошка 🥔"
    tomato = "Помидор🍅"
    banana = "Банан🍌"

    if inventory.get(grill_item, 0) > 0:
        if hunger >= 100:
            update.message.reply_text("🤮 Вы больше не хотите есть.")
            return
        data[user_id]["hunger"] = min(100, hunger + 10)
        inventory[grill_item] -= 1
        if inventory[grill_item] <= 0:
            del inventory[grill_item]
        save_user_data(data)
        update.message.reply_text("🔥 Вы использовали ГРИЛЛЬ АППЕНДИКС и восстановили 10 голода.")
        return

    # Otherwise try tomato or banana
    food_used = None
    if inventory.get(tomato, 0) > 0:
        food_used = tomato
    elif inventory.get(banana, 0) > 0:
        food_used = banana
    elif inventory.get(potato, 0) > 0:
        food_used = potato

    if food_used is None:
        update.message.reply_text("🍽️ У вас нет еды для восстановления голода (бананы или помидоры).")
        return

    restore_amount = random.randint(2, 5)
    new_hunger = min(100, hunger + restore_amount)

    if new_hunger == 100 and hunger < 100:
        # Overeat scenario
        if inventory:
            thrown_item = random.choice(list(inventory.keys()))
            inventory[thrown_item] -= 1
            if inventory[thrown_item] <= 0:
                del inventory[thrown_item]
            update.message.reply_text(
                f"😵‍💫 Вы переели и выбросили {thrown_item}."
            )
        else:
            update.message.reply_text("😵‍💫 Вы переели, но у вас нечего выбросить.")
    else:
        # Consume food item
        inventory[food_used] -= 1
        if inventory[food_used] <= 0:
            del inventory[food_used]
        data[user_id]["hunger"] = new_hunger
        update.message.reply_text(f"🍽️ Вы съели {food_used} и восстановили {new_hunger - hunger} голода. Текущий голод : {new_hunger}")

    save_user_data(data)



def remove_one_item(items_list, item_name):
    for i, itm in enumerate(items_list):
        if itm == item_name:
            del items_list[i]
            break


def text_router(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id in gift_states:
        gift_amount_handler(update, context)
    elif user_id in sell_states:
        sell_amount_handler(update, context)
    elif user_id in shop_states:
        shop_amount_handler(update, context)



def shop_command(update: Update, context: CallbackContext):
    register_user(update)
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user_balance = data[user_id].get("balance", 0)

    keyboard = []
    for item, price in shop_prices.items():
        keyboard.append([InlineKeyboardButton(f"{item} — {price} 🪙", callback_data=f"shop_buy|{item}")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text(
        f"🛍️ Магазин\nВаш баланс: {user_balance} 🪙\nВыберите предмет для покупки:",
        reply_markup=reply_markup
    )
    update.message.reply_text("P.S. если ищите лутбоксы, они тут : /lootbox")

def shop_buy_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)

    try:
        _, item = query.data.split("|", 1)
    except Exception:
        query.answer("❌ Ошибка в данных кнопки.")
        return

    # Save user's intent to buy
    shop_states[user_id] = {"item_selected": item}
    query.answer()
    query.edit_message_text(
        f"🛍️ Вы выбрали: {item}\nВведите количество для покупки:"
    )

def shop_amount_handler(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    if user_id not in shop_states:
        return

    state = shop_states[user_id]
    item = state["item_selected"]
    price = shop_prices.get(item, 0)

    text = update.message.text.strip()
    if not text.isdigit():
        update.message.reply_text("Введите корректное число.")
        return

    amount = int(text)
    if amount <= 0:
        update.message.reply_text("Количество должно быть положительным.")
        return

    data = load_user_data()
    user = data[user_id]

    total_price = price * amount

    if user.get("balance", 0) < total_price:
        update.message.reply_text(
            f"У вас недостаточно 🪙. Нужно {total_price} 🪙, у вас {user.get('balance', 0)} 🪙."
        )
        return

    # Deduct coins
    user["balance"] = user.get("balance", 0) - total_price

    # Initialize items dict if not exists
    if "items" not in user or not isinstance(user["items"], dict):
        user["items"] = {}

    # Add purchased items
    user["items"][item] = user["items"].get(item, 0) + amount

    save_user_data(data)
    shop_states.pop(user_id)

    update.message.reply_text(
        f"✅ Вы купили {amount}x {item} за {total_price} 🪙.\n"
        f"Ваш новый баланс: {user['balance']} 🪙."
    )

def info_cmd(update: Update, context: CallbackContext):
    with open("usernames.json", 'r') as f:
        data = json.load(f)

    if isinstance(data, dict):
        count = len(data.keys())
    elif isinstance(data, list):
        count = len(data)
    else:
        print("Unsupported data type in usernames.json")
        return

    # Load user data to count total items
    with open("user_data.json", 'r', encoding='utf-8') as f:
        user_data = json.load(f)

    total_items = 0
    total_balance = 0
    for user_id, udata in user_data.items():
        items = udata.get("items", [])
        total_items += sum(items.values())
        total_balance += udata.get("balance", 0)

    update.message.reply_text(
        f"👥 Всего пользователей: {count}\n"
        f"🎒 Всего предметов у всех пользователей: {total_items}\n"
        f"💰 Общий баланс всех пользователей: {total_balance} монет"
    )
   

lootbox_config = {
    'lootbox_1': {'required_keys': 25, 'min_loot': 100, 'max_loot': 200, 'name': 'гадский бокс))))'},
    'lootbox_2': {'required_keys': 50, 'min_loot': 200, 'max_loot': 400, 'name': 'п.о.д.о.н.о.к edition!'},
    'lootbox_3': {'required_keys': 100, 'min_loot': 500, 'max_loot': 1000, 'name': 'ох пидорас!'},
    'lootbox_4': {'required_keys': 300, 'min_loot': 1000, 'max_loot': 10000, 'name': 'максимальный ох пидорас!'},
    'lootbox_5': {'required_keys': 10000, 'min_loot': 1, 'max_loot': 500000, 'name': 'ебать какой ты сука подонок!'},
}
def lootbox_command(update: Update, context: CallbackContext):
    keyboard = [
        [
            InlineKeyboardButton("гадский бокс)))", callback_data='info_lootbox_1'),
            InlineKeyboardButton("п.о.д.о.н.о.к. ...", callback_data='info_lootbox_2'),
        ],
        [
            InlineKeyboardButton("ох пидорас!", callback_data='info_lootbox_3'),
            InlineKeyboardButton("максимальный ох пидорас!", callback_data='info_lootbox_4'),
        ],
        [
            InlineKeyboardButton("ебать какой ты сука подонок!", callback_data='info_lootbox_5'),
        ],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выберите лутбокс для открытия:", reply_markup=reply_markup)


def lootbox_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query_data = query.data
    user_id = str(query.from_user.id)
    data = load_user_data()
    user_items = data.get(user_id, {}).get("items", {})

    if query_data.startswith('info_'):
        lootbox_type = query_data.replace('info_', '')
        config = lootbox_config.get(lootbox_type)

        if not config:
            query.answer("Неизвестный лутбокс.")
            return

        text = (
            f"📦 <b>{config['name']}</b>\n\n"
            f"🔑 Необходимо ключей: {config['required_keys']}\n"
            f"🎁 Награда: {config['min_loot']} - {config['max_loot']} случайных предметов\n"
        )

        keyboard = [
            [
                InlineKeyboardButton("⬅️ Назад", callback_data='back_to_lootboxes'),
                InlineKeyboardButton("🗝️ Открыть", callback_data=f'open_{lootbox_type}'),
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
        query.answer()

    elif query_data == 'back_to_lootboxes':
        keyboard = [
            
                [
                    InlineKeyboardButton("гадский бокс)))", callback_data='info_lootbox_1'),
                    InlineKeyboardButton("п.о.д.о.н.о.к. ...", callback_data='info_lootbox_2'),
                ],
                [
                    InlineKeyboardButton("ох пидорас!", callback_data='info_lootbox_3'),
                    InlineKeyboardButton("максимальный ох пидорас!", callback_data='info_lootbox_4'),
                ],
                [
                    InlineKeyboardButton("ебать какой ты сука подонок!", callback_data='info_lootbox_5'),
                ],
            
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("Выберите лутбокс для открытия:", reply_markup=reply_markup)
        query.answer()
    elif query_data.startswith('open_'):
        lootbox_type = query_data.replace('open_', '')
        config = lootbox_config.get(lootbox_type)

        if not config:
            query.answer("Неизвестный лутбокс.")
            return

        key_count = user_items.get("Ключ🔑", 0)

        if key_count < config['required_keys']:
            query.edit_message_text(
                f"❌ У вас недостаточно ключей (нужно {config['required_keys']}). Сейчас у вас: {key_count}"
            )
            query.answer()
            return

        # Remove required keys
        user_items["Ключ🔑"] -= config['required_keys']
        if user_items["Ключ🔑"] <= 0:
            del user_items["Ключ🔑"]

        # Determine loot amount with curse limit
        curse_count = data.get(user_id, {}).get("curse", 0)
        max_loot = config['max_loot']
        min_loot = config['min_loot']
        luck_count = data.get(user_id, {}).get("luck", 0)

        # Determine loot amount
        if luck_count > 0:
            amount = config['max_loot']
            data[user_id]["luck"] -= 1
            if data[user_id]["luck"] <= 0:
                del data[user_id]["luck"]
        amount = random.randint(min_loot, max_loot)
        if curse_count > 0 and amount > 10:
            amount = 10  # Limit loot to max 10 if cursed
            # Optionally reduce curse count here if you want curse to expire on loot box use
            data[user_id]["curse"] -= 1
            if data[user_id]["curse"] <= 0:
                del data[user_id]["curse"]

        acquired = get_loot(amount)
        acquired = [item for item in acquired if item != "Ключ🔑"]

        for item in acquired:
            user_items[item] = user_items.get(item, 0) + 1

        data[user_id]["items"] = user_items
        save_user_data(data)

        summary = f"🎉 Вы открыли {config['name']} и получили {len(acquired)} предметов:\n"
        for item, count in Counter(acquired).items():
            summary += f"{count}x {item}\n"

        query.edit_message_text(summary)
        query.answer()



def daily_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user = data.setdefault(user_id, {})
    
    now = time.time()
    last_claim = user.get("last_daily", 0)
    cooldown = 3 * 3600  # 3 hours in seconds
    
    if now - last_claim < cooldown:
        remaining = int((cooldown - (now - last_claim)) // 60)
        update.message.reply_text(f"⏳ Подождите ещё {remaining} минут, прежде чем получать следующий подарок.")
        return
    
    # Give 5-15 random food items
    food_count = random.randint(5, 15)
    foods = random.choices(FOOD_ITEMS, k=food_count)
    
    # Give 1-50 coins
    coins = random.randint(1, 50)
    
    # Update user inventory and balance
    user_items = user.setdefault("items", {})
    for f in foods:
        user_items[f] = user_items.get(f, 0) + 1
    
    user["balance"] = user.get("balance", 0) + coins
    user["last_daily"] = now
    
    save_user_data(data)
    
    # Prepare reply
    food_summary = {}
    for f in foods:
        food_summary[f] = food_summary.get(f, 0) + 1
    
    items_text = "\n".join(f"{count}x {item}" for item, count in food_summary.items())
    
    update.message.reply_text(
        f"🎁 Вы получили ежедневный подарок!\n"
        f"🍽 Еда:\n{items_text}\n"
        f"💰 Монеты: {coins}"
    )


def sellall_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()
    user_items = data.get(user_id, {}).get("items", {})

    if not user_items:
        update.message.reply_text("❌ У вас нет предметов для продажи.")
        return

    total_items = sum(user_items.values())

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Подтвердить продажу всего", callback_data=f"confirm_sellall_{user_id}")],
        [InlineKeyboardButton("❌ Отмена", callback_data="cancel_sellall")]
    ])

    update.message.reply_text(
        f"⚠️ Вы уверены, что хотите продать все свои {total_items} предметов? "
        f"Это действие необратимо и возврат невозможен.",
        reply_markup=keyboard
    )


def sellall_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = load_user_data()

    if query.data.startswith("confirm_sellall_"):
        target_user_id = query.data.split("_")[-1]
        if user_id != target_user_id:
            query.answer("Это не ваш запрос.", show_alert=True)
            return

        user_data = data.get(user_id, {})
        user_items = user_data.get("items", {})
        if not user_items:
            query.edit_message_text("❌ У вас больше нет предметов для продажи.")
            return

        curse_count = user_data.get("curse", 0)
        luck_count = user_data.get("luck", 0)

        total_items = sum(user_items.values())

        if curse_count > 0:
            multiplier = 0
            user_data["curse"] -= 1
            if user_data["curse"] <= 0:
                del user_data["curse"]
        elif luck_count > 0:
            multiplier = 1.5  # max multiplier
            user_data["luck"] -= 1
            if user_data["luck"] <= 0:
                del user_data["luck"]
        else:
            multiplier = round(random.uniform(0.1, 1.5), 2)

        earnings = int((total_items + 5) * multiplier)

        # Remove all items
        user_data["items"] = {}
        user_data["balance"] = user_data.get("balance", 0) + earnings

        save_user_data(data)

        if multiplier > 0:
            query.edit_message_text(
                f"💰 Вы продали {total_items} предметов.\n"
                f"📈 Множитель: x{multiplier}\n"
                f"💵 Вы получили {earnings} монет."
            )
        else:
            query.edit_message_text(
                f"🏃😢 Вас обокрали, и вы потеряли все предметы."
            )

    elif query.data == "cancel_sellall":
        query.edit_message_text("❌ Продажа всех предметов отменена.")


def pvp_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    usernames = load_usernames()

    buttons = []
    temp_row = []
    for username, uid_raw in sorted(usernames.items()):
        uid = str(uid_raw)
        if uid == user_id:
            continue
        temp_row.append(
            InlineKeyboardButton(f"⚔️ {username}", callback_data=f"pvp_{uid}")
        )
        if len(temp_row) == 3:
            buttons.append(temp_row)
            temp_row = []

    if temp_row:
        buttons.append(temp_row)
    if not buttons:
        update.message.reply_text("❌ Нет доступных пользователей для PVP.")
        return

    markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text("Выберите игрока для PVP:", reply_markup=markup)

def pvp_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    challenger_id = str(query.from_user.id)
    target_id = query.data.split("_")[1]

    usernames = load_usernames()
    usernames_reversed = {str(v): k for k, v in usernames.items()}

    if target_id == challenger_id:
        query.answer("Нельзя атаковать самого себя.", show_alert=True)
        return

    if target_id not in [str(v) for v in usernames.values()]:
        query.answer("Этот пользователь не найден.", show_alert=True)
        return

    challenger_name = usernames_reversed.get(challenger_id, "Игрок")
    target_name = usernames_reversed.get(target_id, "Игрок")

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"pvp_accept_{challenger_id}_{target_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"pvp_decline_{challenger_id}_{target_id}")
        ]
    ])

    context.bot.send_message(
        chat_id=int(target_id),
        text=f"⚔️ Игрок @{challenger_name} хочет сразиться с вами в PVP.\nВы принимаете вызов?",
        reply_markup=keyboard
    )
    query.edit_message_text(f"⚔️ Запрос на PVP отправлен игроку @{target_name}. Ожидание подтверждения...")

def pvp_accept_decline_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    action, challenger_id, target_id = query.data.split("_")[1:]

    usernames = load_usernames()
    usernames_reversed = {str(v): k for k, v in usernames.items()}

    clicker_id = str(query.from_user.id)
    if clicker_id != target_id:
        query.answer("Это не ваш запрос на подтверждение.", show_alert=True)
        return

    if action == "decline":
        query.edit_message_text("❌ Вы отклонили PVP вызов.")
        context.bot.send_message(int(challenger_id), "❌ Игрок отклонил ваш PVP вызов.")
        return

    # Setup initial battle state
    battle_state = {
        "challenger_hp": 100,
        "target_hp": 100,
        "turn": challenger_id,  # actual user_id for clean validation
        "block": {challenger_id: False, target_id: False}
    }
    

    data = load_user_data()
    if challenger_id not in data:
        data[challenger_id] = {}
    if target_id not in data:
        data[target_id] = {}

    data[challenger_id]["pvp"] = {"opponent": target_id, "state": battle_state}
    data[target_id]["pvp"] = {"opponent": challenger_id, "state": battle_state}
    save_user_data(data)

    query.edit_message_text("✅ Вы приняли вызов. Битва начинается!")

    send_pvp_turn(context, challenger_id, target_id, battle_state, usernames_reversed)

def send_pvp_turn(context, challenger_id, target_id, state, usernames_reversed):
    def hp_bar(hp):
        total_slots = 15
        filled_slots = round((hp / 100) * total_slots)
        empty_slots = total_slots - filled_slots
        return "❤️" * filled_slots + "🤍" * empty_slots + f" ({hp}/100)"


    turn_id = state["turn"]

    challenger_name = usernames_reversed.get(challenger_id, "Игрок")
    target_name = usernames_reversed.get(target_id, "Игрок")
    last_action = state.get("last_action_text", "")

    text = (
        f"{challenger_name} {hp_bar(state['challenger_hp'])}\n"
        f"{target_name} {hp_bar(state['target_hp'])}\n\n"   
    )
    text += "ℹ️ "+last_action
    text += "\n\nВыберите действие:"

    buttons = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🗡️ АТАКОВАТЬ", callback_data=f"pvp_turn_{challenger_id}_{target_id}_attack"),
            InlineKeyboardButton("🛡️ ЗАЩИТИТЬСЯ", callback_data=f"pvp_turn_{challenger_id}_{target_id}_defend")
        ],
        [
            InlineKeyboardButton("💊 ПОДХИЛИТЬСЯ", callback_data=f"pvp_turn_{challenger_id}_{target_id}_heal"),
                InlineKeyboardButton("🪑 Ничего не делать", callback_data=f"pvp_turn_{challenger_id}_{target_id}_nothing")
        ]
    ])


    data = load_user_data()
    inventory = data.get(turn_id, {}).get("items", {})
    crit_used = state.get("crit_uses", {}).get(str(turn_id), 0)
    if "🏹 ЛУК." in inventory and inventory["🏹 ЛУК."] > 0 and crit_used < 3:
        buttons.inline_keyboard.append([
            InlineKeyboardButton(f"⚔️ КРИТ. УДАР. ({crit_used}/3)", callback_data=f"pvp_turn_{challenger_id}_{target_id}_crit")
        ])

    potion_used = state.get("potion_uses", {}).get(str(turn_id), 0)
    if "🧪 Зелье здоровья" in inventory and inventory["🧪 Зелье здоровья"] > 0 and potion_used < 3:
        buttons.inline_keyboard.append([
            InlineKeyboardButton(f"🧪 Зелье здоровья ({potion_used}/3)", callback_data=f"pvp_turn_{challenger_id}_{target_id}_potion")
        ])


    print(f"[DEBUG] Sending PVP turn UI to {turn_id}")
    context.bot.send_message(chat_id=int(turn_id), text=text, reply_markup=buttons)

def pvp_turn_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    print("CALLBACK DATA : " + query.data)
    parts = query.data.split("_")
    challenger_id = parts[2]
    target_id = parts[3]
    action = parts[4]
    user_id = str(query.from_user.id)

    data = load_user_data()
    usernames_reversed = {str(v): k for k, v in load_usernames().items()}
    battle = data.get(challenger_id, {}).get("pvp", {}).get("state")

    if not battle:
        query.answer("Битва не найдена.", show_alert=True)
        return

    if user_id != battle["turn"]:
        query.answer("Сейчас не ваш ход.", show_alert=True)
        return

    opponent_id = target_id if user_id == challenger_id else challenger_id
    inventory = data.get(user_id, {}).get("items", {})

    if action == "attack":
        base_dmg = random.randint(5, 15)
        dmg = base_dmg + get_user_skill_level(user_id, "power_strike")
        if battle["block"].get(opponent_id):
            dmg = max(0, dmg - 5)
            battle["block"][opponent_id] = False

        if opponent_id == challenger_id:
            battle["challenger_hp"] -= dmg
        else:
            battle["target_hp"] -= dmg

        battle["last_action_text"] = f"{usernames_reversed[user_id]} нанёс {dmg} урона!"
        query.answer(battle["last_action_text"])

    elif action == "defend":
        battle["block"][user_id] = True
        battle["last_action_text"] = f"{usernames_reversed[user_id]} встал в защиту."
        query.answer("Вы встали в защиту.")

    elif action == "heal":
        base_heal = random.randint(5, 15)
        fast_heal_level = get_user_skill_level(user_id, "fast_heal")
        total_heal = base_heal + fast_heal_level

        if user_id == challenger_id:
            battle["challenger_hp"] = min(100, battle["challenger_hp"] + total_heal)
        else:
            battle["target_hp"] = min(100, battle["target_hp"] + total_heal)

        battle["last_action_text"] = f"{usernames_reversed[user_id]} восстановил {total_heal} HP!"
        query.answer(battle["last_action_text"])

    elif action == "crit":
        crit_uses = battle.setdefault("crit_uses", {}).get(user_id, 0)
        if crit_uses >= 3:
            query.answer("Лимит крит. ударов исчерпан.", show_alert=True)
            return

        if inventory.get("🏹 ЛУК.", 0) <= 0:
            query.answer("У вас больше нет ЛУКА для крит. удара.", show_alert=True)
            return

        inventory["🏹 ЛУК."] -= 1
        if inventory["🏹 ЛУК."] <= 0:
            del inventory["🏹 ЛУК."]

        data[user_id]["items"] = inventory
        battle["crit_uses"][user_id] = crit_uses + 1

        dmg = random.randint(30, 50)
        if opponent_id == challenger_id:
            battle["challenger_hp"] -= dmg
        else:
            battle["target_hp"] -= dmg

        battle["last_action_text"] = f"{usernames_reversed[user_id]} нанёс критический удар: {dmg} урона!"
        query.answer(battle["last_action_text"])

    elif action == "potion":
        potion_uses = battle.setdefault("potion_uses", {}).get(user_id, 0)
        if potion_uses >= 3:
            query.answer("Лимит зелий исчерпан.", show_alert=True)
            return

        if inventory.get("🧪 Зелье здоровья", 0) <= 0:
            query.answer("У вас нет зелья здоровья.", show_alert=True)
            return

        inventory["🧪 Зелье здоровья"] -= 1
        if inventory["🧪 Зелье здоровья"] <= 0:
            del inventory["🧪 Зелье здоровья"]

        data[user_id]["items"] = inventory
        battle["potion_uses"][user_id] = potion_uses + 1

        if user_id == challenger_id:
            battle["challenger_hp"] = 100
        else:
            battle["target_hp"] = 100

        battle["last_action_text"] = f"{usernames_reversed[user_id]} использовал зелье здоровья!"
        query.answer(battle["last_action_text"])

    elif action == "nothing":
        battle["last_action_text"] = f"{usernames_reversed[user_id]} ничего не сделал."
        query.answer("Вы ничего не сделали.")

    save_user_data(data)

    if battle["challenger_hp"] <= 0 or battle["target_hp"] <= 0:
        winner_id = challenger_id if battle["challenger_hp"] > 0 else target_id
        loser_id = target_id if winner_id == challenger_id else challenger_id

        loser_data = data.get(loser_id, {})
        winner_data = data.get(winner_id, {})

        loser_items = loser_data.get("items", {})
        winner_items = winner_data.setdefault("items", {})

        steal_count = random.randint(5, 10)
        stolen_items = []
        available_items = [item for item, count in loser_items.items() if count > 0]

        for _ in range(steal_count):
            if not available_items:
                break
            item = random.choice(available_items)
            loser_items[item] -= 1
            if loser_items[item] <= 0:
                del loser_items[item]
                available_items.remove(item)
            winner_items[item] = winner_items.get(item, 0) + 1
            stolen_items.append(item)

        stolen_coins = random.randint(0, 50)
        actual_stolen = min(stolen_coins, loser_data.get("balance", 0))
        loser_data["balance"] -= actual_stolen
        winner_data["balance"] += actual_stolen

        data[loser_id] = loser_data
        data[winner_id] = winner_data
        save_user_data(data)

        if stolen_items:
            item_summary = {}
            for item in stolen_items:
                item_summary[item] = item_summary.get(item, 0) + 1
            items_text = "\n".join(f"{count}x {item}" for item, count in item_summary.items())
        else:
            items_text = "Нет предметов для кражи."

        result = (
            f"⚔️ Битва завершена!\n"
            f"🏆 Победитель: @{usernames_reversed.get(winner_id, 'Игрок')}\n"
            f"💰 Украдено монет: {actual_stolen}\n"
            f"🎒 Украдено предметов:\n{items_text}"
        )

        context.bot.send_message(int(challenger_id), result)
        context.bot.send_message(int(target_id), result)

        data[challenger_id].pop("pvp", None)
        data[target_id].pop("pvp", None)
        save_user_data(data)

        query.edit_message_text("✅ Битва завершена.")
        return

    battle["turn"] = opponent_id
    save_user_data(data)

    query.edit_message_text("✅ Ваш ход завершен, теперь ход соперника.")
    send_pvp_turn(context, challenger_id, target_id, battle, usernames_reversed)


def clans_chat(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    message_text = " ".join(context.args).strip()

    if not message_text:
        update.message.reply_text(
            "❌ Вы должны ввести сообщение для отправки клану.\nИспользуйте: `/clans chat ваше сообщение`",
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # Load clans
    with open("clans.json", "r", encoding="utf-8") as f:
        clans = json.load(f)

    # Find user's clan
    user_clan = None
    for clan_name, clan_data in clans.items():
        if user_id in clan_data.get("members", []):
            user_clan = clan_name
            break

    if not user_clan:
        update.message.reply_text("❌ Вы не состоите в клане.")
        return

    # Load usernames
    with open("usernames.json", "r", encoding="utf-8") as f:
        usernames_raw = json.load(f)
    reversed_usernames = {str(v): k for k, v in usernames_raw.items()}

    sender_name = reversed_usernames.get(user_id, "Игрок")

    # Format the message
    clan_message = f"🛡️ [{user_clan}] {sender_name}: {message_text}\n(Используйте /clans chat)"

    # Send to all members
    for member_id in clans[user_clan]["members"]:
        try:
            context.bot.send_message(chat_id=int(member_id), text=clan_message)
        except Exception as e:
            print(f"[DEBUG] Failed to send clan message to {member_id}: {e}")

    update.message.reply_text("✅ Сообщение отправлено всем участникам клана.")





def clans_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    args = context.args

    clans = load_clans()
    data = load_user_data()

    if not args:
        update.message.reply_text(
            "🛡️ Команды кланов:\n"
            "/clans create <название> – создать клан\n"
            "/clans join – присоединиться к клану\n"
            "/clans leave – покинуть клан\n"
            "/clans split – разделить баланс с участниками\n"
            "/clans all - все кланы\n"
            "/clans chat <сообщение> - отправить сообщение клану"
        )
        return

    command = args[0].lower()

    if command == "create":
        if len(args) < 2:
            update.message.reply_text("❌ Укажите название клана: /clans create <название>")
            return

        clan_name = " ".join(args[1:])
        if clan_name in clans:
            update.message.reply_text("❌ Клан с таким названием уже существует.")
            return

        clans[clan_name] = {"owner": user_id, "members": [user_id]}
        save_clans(clans)
        update.message.reply_text(f"✅ Клан '{clan_name}' создан!")

    elif command == "all":
        if not clans:
            update.message.reply_text("❌ Нет доступных кланов.")
            return

        text = "🛡️ Список всех кланов:\n\n"
        for clan_name, clan_info in clans.items():
            owner_id = clan_info["owner"]
            members = clan_info["members"]
            try:
                owner_mention = f"<a href='tg://user?id={owner_id}'>👑 Владелец</a>"
            except:
                owner_mention = f"👑 {owner_id}"
            text += f"🛡️ {clan_name}\n{owner_mention}\n👥 Участники: {len(members)}\n\n"

        update.message.reply_text(text, parse_mode="HTML", disable_web_page_preview=True)


    elif command == "join":
        keyboard = []
        for clan_name, clan_info in clans.items():
            keyboard.append([
                InlineKeyboardButton(f"🛡️ {clan_name}", callback_data=f"clans join {clan_name}")
            ])

        if not keyboard:
            update.message.reply_text("❌ Нет доступных кланов для вступления.")
            return

        markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text("Выберите клан для вступления:", reply_markup=markup)

    elif command == "leave":
        for clan_name, clan_info in clans.items():
            if user_id in clan_info["members"]:
                if user_id == clan_info["owner"]:
                    update.message.reply_text("❌ Вы владелец клана, используйте удаление вручную.")
                    return
                clan_info["members"].remove(user_id)
                save_clans(clans)
                update.message.reply_text(f"✅ Вы покинули клан '{clan_name}'.")
                return
        update.message.reply_text("❌ Вы не состоите в клане.")

    elif command == "split":
        for clan_name, clan_info in clans.items():
            if user_id in clan_info["members"]:
                members = clan_info["members"]
                user_balance = data.get(user_id, {}).get("balance", 0)
                if user_balance <= 0:
                    update.message.reply_text("❌ У вас нет монет для распределения.")
                    return

                share = user_balance // len(members)
                for member_id in members:
                    if member_id != user_id:
                        data.setdefault(member_id, {}).setdefault("balance", 0)
                        data[member_id]["balance"] += share

                data[user_id]["balance"] -= share * (len(members) - 1)
                save_user_data(data)
                update.message.reply_text(
                    f"✅ Вы разделили {share * (len(members) - 1)} монет между {len(members)} участниками клана."
                )
                return
        update.message.reply_text("❌ Вы не состоите в клане.")

    
    elif command == "chat":
        # Delegate to clans_chat
        # Remove the first argument 'chat' and pass remaining
        context.args = args[1:]
        clans_chat(update, context)

    else:
        update.message.reply_text("❌ Неизвестная команда. Используйте /clans для справки.")

def clans_join_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = load_user_data()
    clans = load_clans()

    _, _, clan_name = query.data.partition("clans join ")

    if clan_name not in clans:
        query.answer("❌ Клан не найден.", show_alert=True)
        return

    clan_info = clans[clan_name]
    owner_id = clan_info["owner"]

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Принять", callback_data=f"clans accept {clan_name} {user_id}"),
            InlineKeyboardButton("❌ Отклонить", callback_data=f"clans decline {clan_name} {user_id}")
        ]
    ])

    context.bot.send_message(
        chat_id=int(owner_id),
        text=f"⚔️ Игрок {query.from_user.full_name} хочет вступить в ваш клан '{clan_name}'. Принять?",
        reply_markup=keyboard
    )

    query.edit_message_text(f"⏳ Запрос отправлен владельцу клана '{clan_name}'. Ожидайте подтверждения.")

def clans_accept_decline_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    clans = load_clans()

    _, action, clan_name, target_id = query.data.split(" ", 3)

    if clan_name not in clans:
        query.answer("❌ Клан не найден.", show_alert=True)
        return

    clan_info = clans[clan_name]
    owner_id = clan_info["owner"]

    if str(query.from_user.id) != owner_id:
        query.answer("❌ Вы не владелец клана.", show_alert=True)
        return

    if action == "accept":
        if target_id in clan_info["members"]:
            query.answer("✅ Этот пользователь уже в клане.", show_alert=True)
            return
        clan_info["members"].append(target_id)
        save_clans(clans)
        context.bot.send_message(chat_id=int(target_id), text=f"✅ Вы были приняты в клан '{clan_name}'.")
        query.edit_message_text(f"✅ Пользователь принят в клан '{clan_name}'.")
    elif action == "decline":
        context.bot.send_message(chat_id=int(target_id), text=f"❌ Ваш запрос на вступление в клан '{clan_name}' был отклонен.")
        query.edit_message_text(f"❌ Запрос отклонён.")
    else:
        query.answer("❌ Неизвестное действие.", show_alert=True)

def gamble_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()

    if len(context.args) != 1 or not context.args[0].isdigit():
        update.message.reply_text("❌ Использование: /gamble <сумма>")
        return

    amount = int(context.args[0])

    if amount <= 0:
        update.message.reply_text("❌ Сумма должна быть больше 0.")
        return

    user_balance = data.get(user_id, {}).get("balance", 0)
    if user_balance < amount:
        update.message.reply_text("❌ У вас недостаточно монет для ставки.")
        return

    # Check for active curse
    curse_count = data.get(user_id, {}).get("curse", 0)
    luck_count = data.get(user_id, {}).get("luck", 0)

    if luck_count > 0:
        multiplier = 2.0
        data[user_id]["luck"] -= 1
        if data[user_id]["luck"] <= 0:
            del data[user_id]["luck"]
    elif curse_count > 0:
        multiplier = 0
        data[user_id]["curse"] -= 1
        if data[user_id]["curse"] <= 0:
            del data[user_id]["curse"]
    else:
        multiplier = round(random.uniform(0, 2), 1)

    winnings = int(amount * multiplier)
    profit = winnings - amount

    data.setdefault(user_id, {}).setdefault("balance", 0)
    data[user_id]["balance"] += profit
    save_user_data(data)

    if multiplier == 0:
        update.message.reply_text(f"💸 Вы потеряли все {amount} монет в азартной игре.")
    elif multiplier < 1:
        update.message.reply_text(
            f"🎲 Множитель: x{multiplier}\n"
            f"Вы проиграли {abs(profit)} монет."
        )
    else:
        update.message.reply_text(
            f"🎲 Множитель: x{multiplier}\n"
            f"Вы выиграли {winnings} монет! (+{profit})"
        )





def skill_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("🛡️"+info['name'], callback_data=f"skill_show_{skill_id}")]
        for skill_id, info in SKILL_INFO.items()
    ]

    markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("🤹Выберите навык для просмотра и улучшения:", reply_markup=markup)

def skill_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = str(query.from_user.id)

    data = query.data

    if data.startswith("skill_show_"):
        skill_id = data[len("skill_show_"):]
        if skill_id not in SKILL_INFO:
            query.answer("Навык не найден.", show_alert=True)
            return

        lvl = get_user_skill_level(user_id, skill_id)
        max_lvl = SKILL_INFO[skill_id]["max_level"]
        name = SKILL_INFO[skill_id]["name"]
        desc = SKILL_INFO[skill_id]["description"]

        if lvl >= max_lvl:
            cost_text = "Навык достиг максимального уровня."
            can_buy = False
        else:
            cost = get_upgrade_cost(lvl)
            cost_text = f"Стоимость улучшения: {cost}🪙."
            can_buy = True

        text = f"🤹**{name}**\n\n📃{desc}\n\n🎚️Уровень: {lvl}/{max_lvl}\n{cost_text}"

        buttons = []
        if can_buy:
            buttons.append(InlineKeyboardButton("🛒 Купить", callback_data=f"skill_buy_{skill_id}"))
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="skill_back"))

        markup = InlineKeyboardMarkup([buttons])

        query.edit_message_text(text=text, reply_markup=markup, parse_mode="Markdown")

    elif data == "skill_back":
        # Show skill list again
        keyboard = [
            [InlineKeyboardButton(info['name'], callback_data=f"skill_show_{skill_id}")]
            for skill_id, info in SKILL_INFO.items()
        ]
        markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text("Выберите навык для просмотра и улучшения:", reply_markup=markup)

    elif data.startswith("skill_buy_"):
        skill_id = data[len("skill_buy_"):]
        if skill_id not in SKILL_INFO:
            query.answer("Навык не найден.", show_alert=True)
            return

        # Load user balance and upgrade skill
        user_data = load_user_data()  # Your function to load user data
        if user_id not in user_data:
            query.answer("Пользователь не найден.", show_alert=True)
            return
        balance = user_data[user_id].get("balance", 0)

        success, message, new_balance = upgrade_skill(user_id, skill_id, balance)

        if success:
            user_data[user_id]["balance"] = new_balance
            save_user_data(user_data)  # Your function to save user data

        query.answer(message, show_alert=True)

        # After purchase, show skill details again with updated level & cost
        lvl = get_user_skill_level(user_id, skill_id)
        max_lvl = SKILL_INFO[skill_id]["max_level"]
        name = SKILL_INFO[skill_id]["name"]
        desc = SKILL_INFO[skill_id]["description"]

        if lvl >= max_lvl:
            cost_text = "Навык достиг максимального уровня."
            can_buy = False
        else:
            cost = get_upgrade_cost(lvl)
            cost_text = f"Стоимость улучшения: {cost}🪙."
            can_buy = True

        text = f"🤹**{name}**\n\n📃{desc}\n\n🎚️Уровень: {lvl}/{max_lvl}\n{cost_text}"

        buttons = []
        if can_buy:
            buttons.append(InlineKeyboardButton("🛒 Купить", callback_data=f"skill_buy_{skill_id}"))
        buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data="skill_back"))

        markup = InlineKeyboardMarkup([buttons])
        query.edit_message_text(text=text, reply_markup=markup, parse_mode="Markdown")



def leaderboard_command(update: Update, context: CallbackContext):
    data = load_user_data()
    usernames = load_usernames()

    leaderboard = []
    for user_id, user_data in data.items():
        username = next((name for name, uid in usernames.items() if str(uid) == user_id), "Безымянный")
        items = user_data.get("items", {})
        if isinstance(items, dict):
            items_count = sum(items.values())
        else:
            items_count = len(items)

        leaderboard.append((username, items_count))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    top = leaderboard[:10]

    text = "🏆 Топ игроков по количеству предметов:\n\n"
    for idx, (username, count) in enumerate(top, 1):
        text += f"{idx}. @{username} — {count} предметов\n"

    update.message.reply_text(text)

def leaderboard_coins_command(update: Update, context: CallbackContext):
    data = load_user_data()
    usernames = load_usernames()

    leaderboard = []
    for user_id, user_data in data.items():
        username = next((name for name, uid in usernames.items() if str(uid) == user_id), "Безымянный")
        balance = user_data.get("balance", 0)
        leaderboard.append((username, balance))

    leaderboard.sort(key=lambda x: x[1], reverse=True)
    top = leaderboard[:10]

    text = "💰 Топ игроков по количеству монет:\n\n"
    for idx, (username, balance) in enumerate(top, 1):
        text += f"{idx}. @{username} — {balance} монет\n"

    update.message.reply_text(text)

import uuid


def inline_inventory(update: Update, context: CallbackContext):
    query = update.inline_query.query  # The text after @YourBot
    user_id = str(update.inline_query.from_user.id)
    
    data = load_user_data()
    user = data.get(user_id, {})
    items = user.get("items", {})
    balance = user.get("balance", 0)

    display_items = list(items.items())[:3]
    hidden_count = max(len(items) - 3, 0)

    if not items:
        text = f"🎒 У меня нет предметов.\n🪙 Баланс: {balance} монет."
    else:
        text = "<b>Я играю в шлюшку василиску. Вот мой инвентарь сучки)))</b> \n\n"
        for item, count in display_items:
            text += f"{item} x{count}\n"
        if hidden_count > 0:
            text += f"... и ещё {hidden_count} предметов.\n"

    text += f"\n<i>@vasilisarpgbot</i>"

    results = [
        InlineQueryResultArticle(
            id=str(uuid.uuid4()),
            title="Мой рюкзак",
            input_message_content=InputTextMessageContent(text, parse_mode="HTML")
        )
    ]

    update.inline_query.answer(results, cache_time=10)


def curse_command(update: Update, context: CallbackContext):
    data = load_user_data()
    user_id = str(update.effective_user.id)

    user_items = data.get(user_id, {}).get("items", {})

    # Check for 😈 ПРОКЛЯТИЕ.
    if user_items.get("😈 ПРОКЛЯТИЕ.", 0) <= 0:
        update.message.reply_text("У тебя нет 😈 ПРОКЛЯТИЕ., чтобы использовать это.")
        return

    usernames = load_usernames()  # {username: user_id}

    buttons = []
    temp_row = []

    for username, target_user_id in sorted(usernames.items()):
        temp_row.append(
            InlineKeyboardButton(f"@{username}", callback_data=f"curse_{target_user_id}_{user_id}")
        )
        if len(temp_row) == 3:
            buttons.append(temp_row)
            temp_row = []

    # Add the last row if it has less than 2 buttons
    if temp_row:
        buttons.append(temp_row)

    reply_markup = InlineKeyboardMarkup(buttons)
    update.message.reply_text(
        "Кого хочешь проклясть? Выбери из списка:",
        reply_markup=reply_markup
    )


def curse_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    data = load_user_data()

    query_data = query.data
    if query_data.startswith("curse_"):
        _, target_user_id, caller_user_id = query_data.split("_")

        # Apply curse to target
        if target_user_id not in data:
            data[target_user_id] = {}
        data[target_user_id]["curse"] = 3

        # Remove 😈 ПРОКЛЯТИЕ. from caller
        caller_items = data.get(caller_user_id, {}).get("items", {})
        if caller_items.get("😈 ПРОКЛЯТИЕ.", 0) > 0:
            caller_items["😈 ПРОКЛЯТИЕ."] -= 1
            if caller_items["😈 ПРОКЛЯТИЕ."] <= 0:
                del caller_items["😈 ПРОКЛЯТИЕ."]
            data[caller_user_id]["items"] = caller_items
        else:
            # Edge fallback in case user tries to bypass
            query.edit_message_text("У тебя больше нет 😈 ПРОКЛЯТИЕ., чтобы использовать данную шлюшку)))))")
            query.answer()
            return

        save_user_data(data)

        query.answer()
        query.edit_message_text(f"Пользователь {target_user_id} проклят на 3 действия. 😈 ПРОКЛЯТИЕ. удалено из твоего инвентаря.")


def luck_command(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)
    data = load_user_data()

    user_items = data.get(user_id, {}).get("items", {})

    if user_items.get("🍀 ОТВАР УДАЧИ.", 0) <= 0:
        update.message.reply_text("У вас нет 🍀 ОТВАР УДАЧИ., чтобы использовать это.")
        return

    # Remove one potion
    user_items["🍀 ОТВАР УДАЧИ."] -= 1
    if user_items["🍀 ОТВАР УДАЧИ."] <= 0:
        del user_items["🍀 ОТВАР УДАЧИ."]
    data[user_id]["items"] = user_items

    # Add or increment luck count
    data.setdefault(user_id, {}).setdefault("luck", 0)
    data[user_id]["luck"] += 3

    save_user_data(data)

    update.message.reply_text(
        "🍀 Вы использовали Отвар Удачи!"
    )


def main():
    TOKEN = "7606251658:AAGxYLnSDnq5uiyvR5rlYsLOcUzBBSp67Og"
    updater = Updater(TOKEN)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("backpack", backpack_command))
    dp.add_handler(CommandHandler("travel", travel_command))
    dp.add_handler(CommandHandler("gift", gift_command))
    dp.add_handler(CallbackQueryHandler(gift_select_callback, pattern=r"^gift_select\|"))
    dp.add_handler(CommandHandler("sell", sell_command))
    dp.add_handler(CallbackQueryHandler(sell_select_callback, pattern=r"^sell_select\|"))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, text_router))
    dp.add_handler(CommandHandler("shop", shop_command))
    dp.add_handler(CallbackQueryHandler(shop_buy_callback, pattern=r"^shop_buy\|"))
    dp.add_handler(CommandHandler("lootbox", lootbox_command))
    dp.add_handler(CommandHandler("eat", eat_command))
    dp.add_handler(CallbackQueryHandler(keys_offer_callback, pattern=r'^keys_(accept|decline)\|'))  
    dp.add_handler(CommandHandler("info", info_cmd))
    dp.add_handler(CallbackQueryHandler(lootbox_button, pattern='^(info_|back_to_lootboxes|open_)'))
    dp.add_handler(CommandHandler("sellall", sellall_command))

    dp.add_handler(CallbackQueryHandler(lock_callback, pattern=r"^lock_"))
    dp.add_handler(CallbackQueryHandler(sellall_callback, pattern="^(confirm_sellall_|cancel_sellall)"))
    dp.add_handler(CommandHandler("daily", daily_command))
    dp.add_handler(CommandHandler("bonus", bonus_command))

    dp.add_handler(CommandHandler("pvp", pvp_command))
    dp.add_handler(CallbackQueryHandler(pvp_callback, pattern=r"^pvp_\d+$"))
    dp.add_handler(CallbackQueryHandler(pvp_accept_decline_callback, pattern=r"^pvp_(accept|decline)_\d+_\d+$"))
    dp.add_handler(CallbackQueryHandler(pvp_turn_callback, pattern=r"^pvp_turn_\d+_\d+_(attack|defend|heal|crit|potion|nothing)$"))


    dp.add_handler(CommandHandler("clans", clans_command))
    dp.add_handler(CallbackQueryHandler(clans_join_callback, pattern=r"^clans join "))
    dp.add_handler(CallbackQueryHandler(clans_accept_decline_callback, pattern=r"^clans (accept|decline) "))
    dp.add_handler(CommandHandler("skill", skill_command))
    dp.add_handler(CallbackQueryHandler(skill_callback, pattern=r"^skill_"))

    dp.add_handler(CommandHandler("leaderboard", leaderboard_command))
    dp.add_handler(CommandHandler("leaderboard_coins", leaderboard_coins_command))

    dp.add_handler(CommandHandler("gamble", gamble_command, pass_args=True))
    dp.add_handler(InlineQueryHandler(inline_inventory))
    dp.add_handler(CommandHandler("curse", curse_command))
    dp.add_handler(CallbackQueryHandler(curse_callback, pattern="^curse_"))

    dp.add_handler(CommandHandler("luck", luck_command))


    dp.add_handler(CallbackQueryHandler(pve_travel_callback, pattern="^pve_(start_battle|flee)$"))
    dp.add_handler(CallbackQueryHandler(pve_battle_callback, pattern="^pve_"))
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()