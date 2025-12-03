import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from config import TOKEN
from storage import Storage
from game_engine import GameEngine

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

storage = Storage()


# Генерация клавиатуры для сцены
def generate_keyboard(scene_id, user_data):
    actions = GameEngine.get_scene_actions(scene_id)
    keyboard = []

    action_map = {
        "shop": "🛒 Магазин",
        "street": "🚪 Выйти на улицу",
        "lab_x18": "☢️ Идти в лабораторию X18",
        "talk_stalker": "🗣️ Поговорить со сталкером",
        "search_house": "🏚️ Зайти в дом",
        "back": "🔙 Назад",
        "try_door": "🔒 Открыть дверь",
        "use_key": "🔑 Использовать ключ",
        "search": "🔍 Обыскать комнаты",
        "go_room": "Рискнуть и пойти в комнату",
        "search_doc": "Искать документы",
        "give_doc": "📄 Отдать документы",
        "to_sidr": "К Сидоровичу"
    }

    for action in actions:
        if action in action_map:
            keyboard.append([InlineKeyboardButton(
                action_map[action],
                callback_data=f"action_{action}"
            )])

    # Кнопка меню
    keyboard.append([InlineKeyboardButton(
        "📱 Меню",
        callback_data="action_menu"
    )])

    return InlineKeyboardMarkup(keyboard)


def generate_menu_keyboard():
    keyboard = [
        [
            InlineKeyboardButton("📦 Инвентарь", callback_data="action_inventory"),
            InlineKeyboardButton("👤 Статистика", callback_data="action_stats"),
        ],
        [
            InlineKeyboardButton("💼 Квесты", callback_data="action_quests"),
            InlineKeyboardButton("❓ Помощь", callback_data="action_help"),
        ] ,
        [InlineKeyboardButton("🏠 На главную", callback_data="action_main")]
    ]
    return InlineKeyboardMarkup(keyboard)


# Отправка нового сообщения вместо редактирования
async def send_new_message(update: Update, text: str, keyboard=None, parse_mode="Markdown"):
    if update.callback_query:
        # Если это callback от кнопки
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )
    elif update.message:
        # Если это текстовое сообщение или команда
        await update.message.reply_text(
            text=text,
            reply_markup=keyboard,
            parse_mode=parse_mode
        )


# Основной обработчик действий
async def handle_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    action = query.data.replace("action_", "")
    user_data = storage.get_user(user_id)

    response_text = ""
    new_scene = user_data["current_scene"]

    # Обработка меню и его подразделов
    if action == "menu":
        response_text = f"📱 *Меню игрока*\n\nВыбери раздел:"
        await send_new_message(update, response_text, generate_menu_keyboard())
        return

    elif action == "inventory":
        items = user_data.get("inventory", [])

        if items:
            item_list = []
            for item_id in items:
                item_info = GameEngine.ITEMS.get(item_id, {})
                item_name = item_info.get("name", item_id)

                if item_id == "key_x18":
                    item_list.append(f"🔑 {item_name}")
                elif item_id == "documents":
                    item_list.append(f"📄 {item_name}")
                elif item_id == "pistol":
                    item_list.append(f"🔫 {item_name}")
                elif item_id == "medkit":
                    item_list.append(f"💊 {item_name}")
                else:
                    item_list.append(f"• {item_name}")

            items_text = "\n".join(item_list)
            response_text = f"📦 *Инвентарь {user_data['user_name']}:*\n\n{items_text}\n\n*Всего предметов:* {len(items)}"
            keyboard_buttons = []

            keyboard_buttons.append([
                InlineKeyboardButton("🔙 Назад в меню", callback_data="action_menu"),
                InlineKeyboardButton("🏠 На главную", callback_data="action_main"),
            ])

            await send_new_message(update, response_text, InlineKeyboardMarkup(keyboard_buttons))
        else:
            response_text = "📦 *Инвентарь пуст*\n\nУ тебя пока нет предметов."
            keyboard = InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 Назад в меню", callback_data="action_menu"),
            ]])
            await send_new_message(update, response_text, keyboard)
        return

    elif action == "stats":
        health_status = "✅ Отличное" if user_data["health"] > 70 else \
            "⚠️  Среднее" if user_data["health"] > 30 else \
                "❌ Критическое"

        response_text = (
            f"👤 *Статистика игрока:*\n\n"
            f"🔹 *Имя:* {user_data['user_name']}\n"
            f"🔹 *Здоровье:* {user_data['health']}/100 {health_status}\n"
            f"🔹 *Деньги:* {user_data['money']} руб.\n"
            f"🔹 *Очки опыта:* {user_data['points']}\n"
            f"🔹 *Текущая локация:* {user_data['current_scene']}\n"
            f"🔹 *Предметов в инвентаре:* {len(user_data['inventory'])}\n"
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад в меню", callback_data="action_menu"),
        ]])

        await send_new_message(update, response_text, keyboard)
        return

    elif action == "main":
        response_text = GameEngine.get_scene_text(user_data["current_scene"], user_data["user_name"])
        keyboard = generate_keyboard(user_data["current_scene"], user_data)
        await send_new_message(update, response_text, keyboard)
        return

    elif action == "quests":
        response_text = f"📜 *Активные квесты:*\n\n"

        if "documents" not in user_data["inventory"]:
            response_text += "✅ *Квест от Сидоровича:*\nНайти документы в лаборатории X18\n\n"
        else:
            response_text += "Пока нет активных квестов.\nПоговори с Сидоровичем для получения задания."

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад в меню", callback_data="action_menu"),
        ]])

        await send_new_message(update, response_text, keyboard)
        return


    elif action == "help":
        response_text = (
            f"❓ *Помощь по игре*\n\n"
            f"*Основные команды:*\n"
            f"• Нажимай кнопки для взаимодействия\n"
            f"• Используй Меню для доступа к статистики и инвентарю\n"
            f"*Управление:*\n"
            f"• /reset - перезапуск игры\n"
            f"• /menu - открыть меню\n"
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Назад в меню", callback_data="action_menu"),
        ]])

        await send_new_message(update, response_text, keyboard)
        return



    # ОБРАБОТКА ОСНОВНЫХ ДЕЙСТВИЙ ИГРЫ
    if action == "next" and user_data["current_scene"] == "sidorovich":
        response_text = (
            "Вдруг машина резко теряет управление, её носит из стороны в сторону\n"
            "Она вылетает с дороги и переворачивается несколько раз ......\n"
            "Вы теряете сознание......"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Далее", callback_data="action_next1")]]
        )

    elif action == "next1" and user_data["current_scene"] == "sidorovich":
        response_text = (
            "Вы приходите в себя и не можете понять где вы оказались.\n"
            "В каком-то помещении, вроде это подвал, да точно!\n"
            "Напротив, за прилавком, сидит мужичок и смотрит на вас"
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Что происходит?", callback_data="action_next2")]]
        )

    elif action == "next2" and user_data["current_scene"] == "sidorovich":
        response_text = GameEngine.get_scene_text("sidorovich", user_data['user_name'])
        keyboard = generate_keyboard("sidorovich", storage.get_user(user_id))


    elif action == "street" and user_data["current_scene"] == "sidorovich":
        new_scene = "street"
        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "talk_stalker" and user_data["current_scene"] == "street":
        if not user_data.get("has_talked_stalker", False):
            response_text = (
                f"Сталкер хрипло кашляет и смотрит на тебя, {user_data['user_name']}:\n"
                "Вижу, ты новенький. В лабораторию собрался?"
                "Там жутко. Если пойдешь без пушки, то пиши пропало. \n"
                "Пистолет можешь купить у Сидоровича'"
            )
            storage.update_user(user_id, {"has_talked_stalker": True, "points": user_data["points"] + 10})
        else:
            response_text = f"Сталкер больше не хочет с тобой разговаривать, он устал и не в настроении"

        keyboard = generate_keyboard(user_data["current_scene"], user_data)

    elif action == "back" or action == "to_sidr":
        if user_data["current_scene"] == "street":
            new_scene = "sidorovich"
        elif user_data["current_scene"] == "house":
            new_scene = "street"
        elif user_data["current_scene"] == "lab_x18":
            new_scene = "street"
        elif user_data["current_scene"] == "lab_x18_in":
            new_scene = "street"
        elif user_data["current_scene"] == "shop":
            new_scene = "sidorovich"
        elif user_data["current_scene"] == "room":
            new_scene = "lab_x18_in"
        elif user_data["current_scene"] == "end":
            new_scene = "sidorovich"

        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "search_house" and user_data["current_scene"] == "street":
        new_scene = "house"
        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "search" and user_data["current_scene"] == "house":
        if not user_data.get("has_found_key", False):
            storage.add_item(user_id, "key_x18")
            storage.update_user(user_id, {"has_found_key": True, "points": user_data["points"] + 20})
            response_text = (
                "🔍 *Поиск в доме...*\n\n"
                "В старом комоде, под грудой пожелтевших газет, "
                "ты находишь ржавый ключ с гравировкой 'X18'!\n\n"
                "✅ *Ключ от лаборатории найден!*\n"
                "*+ 20 очков опыта*"
            )
        else:
            response_text = "Больше ничего интересного нет."

        keyboard = generate_keyboard(user_data["current_scene"], user_data)

    elif action == "lab_x18" and user_data["current_scene"] == "street" and user_data["has_door_open"] == False:
        new_scene = "lab_x18"
        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "lab_x18" and user_data["current_scene"] == "street" and user_data["has_door_open"] == True:
        new_scene = "lab_x18_in"
        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "try_door" and user_data["current_scene"] == "lab_x18":
        if "key_x18" in user_data["inventory"]:
            response_text = (
                "Ты пытаешься открыть дверь...\n\n"
                "Дверь заперта на ключ.\n\n"
                "💡 *У тебя есть ключ!* \n\n"
            )

            keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🔑 Использовать ключ", callback_data="action_use_key")]])
        else:
            response_text = (
                "Вы пытаетесь открыть дверь...\n\n"
                "Дверь не поддаётся. Она заперта на массивный замок.\n\n"
                "🔑 *Нужен ключ* - поищи его в заброшенном доме на улице."
            )
            keyboard = generate_keyboard(user_data["current_scene"], user_data)


    elif action == "use_key" and user_data["current_scene"] == "lab_x18":
        response_text = (
            "*Ключ подошёл!*\n"
            "*+20 опыта*\n\n"
            "Старая дверь со скрипом открывается...\n\n"
        )
        storage.update_user(user_id, {"has_door_open": True, "points": user_data["points"] + 20})
        storage.update_user(user_id, { "inventory": [item for item in user_data["inventory"] if item != "key_x18"]})
        keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("Войти", callback_data="action_lab_x18_in")]])

    elif action == "lab_x18_in" and user_data["current_scene"] == "lab_x18":
            user_data = storage.get_user(user_id)
            new_scene = "lab_x18_in"
            storage.update_user(user_id, {"current_scene": new_scene})
            response_text = GameEngine.get_scene_text(new_scene, user_data["user_name"])
            keyboard = generate_keyboard(new_scene, user_data)

    elif action == "go_room" and user_data["current_scene"] == "lab_x18_in":
        if user_data["has_killed"] == False:
            response_text = (
             "Вы идете вдоль по коридору\n"
             "Подходите к комнате, хотите зайти, *как вдруг из неё выпрыгивает монстр и бросается на вас!!!!*"
            )
            if "pistol" in user_data["inventory"]:
                keyboard = InlineKeyboardMarkup(
                    [[InlineKeyboardButton("СТРЕЛЯТЬ!", callback_data="action_shoot")]]
                )
            else:
                await send_new_message(update, "*YOU DIED*\n\n"
                    "Это было очень смело идти без оружия сюда.\n"
                    "Чтобы начать игру заново напишите /reset", None)
        else:
            new_scene = "room"
            storage.update_user(user_id, {"current_scene": new_scene})
            response_text = (
                "В этот раз вы зашли в комнату без происшествий\n\n"
                "На столе стоит сейф"
            )
            keyboard = generate_keyboard(new_scene, user_data)

    elif action == "shoot" and user_data["current_scene"] == "lab_x18_in":
        new_scene = "room"
        storage.update_user(user_id, {"current_scene": new_scene})
        response_text = (
            "*ВЫСТРЕЛ*\n\n"
            "Вы чудом успели нажать на курок и выжили\n"
            "+100 очков опыта\n\n"
            "Зайдя в комнату, вы обнаруживаете сейф на столе, "
            "скорее всего в нем те документы, которые нужны Сидоровичу"
        )
        storage.update_user(user_id, {"has_killed": True, "points": user_data["points"] + 100})
        keyboard = generate_keyboard(new_scene, user_data)

    elif action == "search_doc" and user_data["current_scene"] == "room":
        if not user_data.get("has_found_doc", False):
            storage.add_item(user_id, "documents")
            storage.update_user(user_id, {"has_found_doc": True, "points": user_data["points"] + 200})
            response_text = (
                "🔍 *Открытие сейфа...*\n\n"
                "Сейф оказался закрыт не до конца, приоткрыв дверцу  "
                "вы находите заветные документы для Сидоровича!\n\n"
                "✅ *Документы найдены!*\n"
                "*+ 200 очков опыта*"
            )
        else:
            response_text = (
                "В сейфе больше ничего нет!"
            )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="action_back")]]
        )



    elif action == "shop" and user_data["current_scene"] == "sidorovich":
        response_text = (
            "📋 *Товары Сидоровича:*\n\n"
            f"Пистолет ПМ - {GameEngine.SIDOROVICH_SHOP['pistol']} руб.\n\n"
            f"Ваш баланс: {user_data['money']} руб."
        )
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Купить пистолет", callback_data="action_buy_gun")], [InlineKeyboardButton("🔙 Назад", callback_data="action_back"),]]
        )


    elif action == "buy_gun" and user_data["current_scene"] == "sidorovich":
        price = GameEngine.SIDOROVICH_SHOP["pistol"]
        if user_data["money"] >= price:
            storage.add_item(user_id, "pistol")
            storage.update_user(user_id, {
                "money": user_data["money"] - price,
                "points": user_data["points"] + 5
            })
            response_text = (
                f"✅ Ты купил пистолет ПМ за {price} рублей!\n"
                f"💵 Осталось: {user_data['money'] - price} рублей\n\n"
                f"Теперь ты лучше вооружён для похода в лабораторию."
            )
        else:
            response_text =(
                f"❌ Недостаточно денег! Нужно {price} рублей, а у тебя только {user_data['money']}.\n\n"
                f"Выполни квест, чтобы получить больше денег."
            )

        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("🔙 Назад", callback_data="action_back")]]
        )
    elif action == "give_doc" and user_data["current_scene"] == "sidorovich":
        new_scene = "end"
        storage.update_user(user_id, {"current_scene": new_scene})

        if "documents" in user_data["inventory"]:
            response_text = (
                f"Спасибо, {user_data["user_name"]}, вот тебе награда от меня\n\n"
                f"+2000рублей\n"
                f"+500 очков опыта\n\n"
                f"Поздравляем, вы прошли игру!!!\n"
                f"Если хотите, то продолжить изучение локаций"
            )
        else:
            response_text = ("Когда будут документы, тогда и приходи\n"
                             "Нечего просто так беспокоить"
            )
        keyboard = generate_keyboard(new_scene, user_data)




    else:
        # Если действие не распознано, показываем текущую сцену
        response_text = GameEngine.get_scene_text(user_data["current_scene"], user_data["user_name"])
        keyboard = generate_keyboard(user_data["current_scene"], user_data)

    await send_new_message(update, response_text, keyboard)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # СОЗДАЕМ НОВОГО ПОЛЬЗОВАТЕЛЯ С НАЧАЛЬНЫМИ ДАННЫМИ
    user_data = {
        "user_id": user_id,
        "user_name": "",
        "current_scene": "start",
        "inventory": [],
        "money": 1500,
        "health": 100,
        "points": 0,
        "has_talked_stalker": False,
        "has_found_key": False,
        "has_door_open": False,
        "has_killed": False,
        "has_found_doc": False,
    }

    storage.update_user(user_id, user_data)

    response_text = GameEngine.get_scene_text("start", "")

    await update.message.reply_text(
        response_text,
        parse_mode="Markdown",
        reply_markup=None  # Важно: без кнопок!
    )


async def reset_game(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    # Полностью сбрасываем данные
    storage.update_user(user_id, {
        "user_id": user_id,
        "user_name": "",
        "current_scene": "start",
        "inventory": [],
        "money": 1500,
        "health": 100,
        "points": 0,
        "has_talked_stalker": False,
        "has_found_key": False,
        "has_door_open": False,
        "has_killed": False,
        "has_found_doc": False,
    })

    await update.message.reply_text(
        "✅ Игра полностью сброшена!\n\n"
        "Добро пожаловать в Зону, сталкер. Введи своё имя:",
        parse_mode="Markdown",
        reply_markup=None
    )


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()
    user_data = storage.get_user(user_id)

    if user_data["current_scene"] == "start":
        # Это ввод имени
        await handle_name(update, text, user_data)
    else:
        await handle_game_text(update, text, user_data)

# Обработка имени пользователя
async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_name = update.message.text.strip()

    storage.update_user(user_id, {
        "user_name": user_name,
        "current_scene": "sidorovich"
    })

    response_text = (
        "Ночь. Вы едите на грузовике сквозь сильный ливень.\n"
        "Гремит гром, сверкает молния. Вокруг только лес и поля Чернобыльской зоны отчуждения\n"
        "Вдруг внезапно в вашу машину попадает молния"
    )
    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Далее", callback_data="action_next")]]
    )
    await update.message.reply_text(response_text, reply_markup=keyboard, parse_mode="Markdown")


async def handle_game_text(update: Update, text: str, user_data: dict):

    await update.message.reply_text(
        "ℹ️ Используй кнопки для взаимодействия с игрой.\n"
        "Если нужно открыть меню - нажми кнопку 📱 Меню.",
        reply_markup=generate_keyboard(user_data["current_scene"], user_data)
    )

# Команда инвентаря
async def inventory_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = storage.get_user(user_id)

    items = user_data.get("inventory", [])

    if items:
        item_names = []
        for item_id in items:
            item_info = GameEngine.ITEMS.get(item_id, {})
            item_names.append(f"• {item_info.get('name', item_id)}")

        items_text = "\n".join(item_names)
        response_text = f"📦 *Инвентарь:*\n\n{items_text}"
    else:
        response_text = "📦 *Инвентарь пуст*"

    await update.message.reply_text(response_text, parse_mode="Markdown")


# Команда меню
async def menu_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    response_text = f"📱 *Меню игрока*\n\nВыбери раздел:"
    keyboard = generate_menu_keyboard()
    await update.message.reply_text(response_text, reply_markup=keyboard, parse_mode="Markdown")


async def debug_state(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = storage.get_user(user_id)

    response_text = (
        f"🔧 *Отладка состояния:*\n\n"
        f"ID: {user_id}\n"
        f"Имя: {user_data['user_name']}\n"
        f"Сцена: {user_data['current_scene']}\n"
        f"Инвентарь: {user_data['inventory']}\n"
        f"Деньги: {user_data['money']}\n"
        f"Здоровье: {user_data['health']}\n"
        f"Ключ найден: {user_data.get('has_found_key', False)}\n"
        f"Говорил со сталкером: {user_data.get('has_talked_stalker', False)}"
    )

    await update.message.reply_text(response_text, parse_mode="Markdown")


async def to_sidorovich(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_data = storage.get_user(user_id)

    if not user_data["user_name"]:
        await update.message.reply_text(
            "Сначала введи своё имя в чат.",
            parse_mode="Markdown"
        )
        return

    storage.update_user(user_id, {"current_scene": "sidorovich"})
    user_data = storage.get_user(user_id)

    response_text = GameEngine.get_scene_text("sidorovich", user_data["user_name"])
    keyboard = generate_keyboard("sidorovich", user_data)

    await update.message.reply_text(
        response_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )


def main():
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("reset", reset_game))

    application.add_handler(CommandHandler("debug", debug_state))
    application.add_handler(CommandHandler("sidorovich", to_sidorovich))
    application.add_handler(CommandHandler("inventory", inventory_cmd))
    application.add_handler(CommandHandler("menu", menu_cmd))

    application.add_handler(CallbackQueryHandler(handle_action, pattern="^action_"))
    application.add_handler(CallbackQueryHandler(handle_action, pattern="^use_"))

    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()