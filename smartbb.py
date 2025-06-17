import os # проверка файла состояния
import json #сохранение и загрузка состояния в файл.
import time # для отслеживания времени действий, возраста, проверок нужд.
from datetime import datetime, timedelta

from telegram import Update # сообщение тг
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackContext # запуск бота, для обработки команд типо /talk, /feed.
from telegram.ext import CommandHandler
from telegram.helpers import escape_markdown

import httpx # отправка запросов
from difflib import get_close_matches # для поиска похожих фраз в памяти Саши (fuzzy match).
import pymorphy2 # приведение слов к начальной форме, чтобы искать проще


# Глобальные переменные и тд

BOT_token = "7987794458:AAFoHygaSO1UtG2nOk5g7jO7ogPn-y3Z-UA"

# Апи ключ для запросов в ии
TOGETHER_key = "95912c3b996f576285bc556175fff76fcb591605ebfbe54a6266d59ca8e4ddc5"
TOGETHER_url = "https://api.together.ai/v1/chat/completions"

STATE_file = "smart_sasha.json"

NEEDS = ["talk", "feed", "hug", "play", "teach", "praise", "sleep", "iam"]

# Глобальные объекты модели
state = {
    "birth_date": None,
    "last_actions": {},  # Метки времени последнего выполнения каждой потребности
    "known_users": {},  # Словарь известных пользователей
    "chat_id": None,  # ИД группы, в которой запущен бот
    "user_memories": {},  # Словарь с контекстом по каждому пользователю
    "memory_dict": {} # Хранение знаний
}

#Загрузить состояние бота, если оно существует

def loade_state():
    global state
    if os.path.isfile(STATE_file):
        try:
            with open(STATE_file, 'r', encoding='utf-8') as f:
                state = json.load(f)

            # Конвертирую строковые метки времени обратно в календаль
            if state.get("last_actions"):
                for need, t in state["last_actions"].items():
                    if isinstance(t, str):
                        state["last_actions"][need] = datetime.fromisoformat(t)

            if "user_memories" in state:
                for user_id, data in state["user_memories"].items():
                    users[user_id] = UserProfile(
                        user_id=user_id,
                        role=data.get("role"),
                        history=data.get("history", [])
                    )

            if "roles" not in state:
                state["roles"] = {}

            if "memory_dict" not in state:
                state["memory_dict"] = {}

            # Приводим всё к строкам, чтобы читалось норм
            if "known_users" in state:
                state["known_users"] = {str(k): v for k, v in state["known_users"].items()}


        except Exception as e:
            print(f"Ошибка загрузки состояния: {e}")

            # Если файл удалила, создаю новый
            state["birth_date"] = datetime.now().isoformat()
            now = datetime.now()
            state["last_actions"] = {need: now for need in NEEDS}
            state["known_users"] = {}
            state["chat_id"] = None
            state["roles"] = {}
            state["memory_dict"] = {}
    else:

        # Если файл не найден я опять создаю новый
        state["birth_date"] = datetime.now().isoformat()
        now = datetime.now()
        state["last_actions"] = {need: now for need in NEEDS}
        state["known_users"] = {}
        state["chat_id"] = None
        state["roles"] = {}

def savee_state():
    state_to_save = state.copy()

    # Конвертирую время в строку
    if state_to_save.get("last_actions"):
        for need, t in state_to_save["last_actions"].items():
            if isinstance(t, datetime): # смотрим это дейттайм ваще или нет в ластакшон
                state_to_save["last_actions"][need] = t.isoformat()

    # Сохраняю память пользователей
    state_to_save["user_memories"] = {
        user_id: {
            "role": profile.role,
            "history": profile.history
        } for user_id, profile in users.items()
    }

    # Добавляем роли отдельно, для промпта
    state_to_save["roles"] = {
        user_id: profile.role
        for user_id, profile in users.items()
        if profile.role
    }

    try:
        with open(STATE_file, 'w', encoding='utf-8') as f:
            json.dump(state_to_save, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"Ошибка сохранения состояния: {e}")

users = {}

class UserProfile:
    def __init__(self, user_id, role=None, history=None):
        self.user_id = user_id
        self.role = role
        self.history = history if history is not None else []

    def prompt_frag(self):
        if self.role == "папа":
            return f"С тобой сейчас говорит твой папа. Ты всегда чувствуешь себя в безопасности рядом с ним."
        elif self.role == "мама":
            return f"С тобой сейчас говорит твоя мама. Ты ей доверяешь и она тебя понимает."
        elif self.role:
            return f"С тобой {self.role}. Он говорит с тобой."
        else:
            return "С тобой сейчас кто-то говорит, но ты пока не очень его знаешь."

    def display_name(self):
        return self.role.capitalize() if self.role else "Незнакомец" #приводим к норм виду блин

    def add_message(self, message):
        self.history.append(message)
        self.history = self.history[-6:]  # только последние 6

    def __str__(self):
        return f"UserProfile({self.user_id}, роль: {self.role}, история: {len(self.history)} сообщений)"

    # добавление из команд
    def add_to_history(self, message):
        self.history.append(message)
        if len(self.history) > 7:
            # сохраняем первую строку и последние 6 диалогов
            self.history = [self.history[0]] + self.history[-6:]

    def get_prompt(self):
        return "\n".join(self.history) + "\nСаша:"

    def action_phrase(self, verb_m: str, verb_f: str) -> str:
        feminine_roles = ["мама", "сестра", "няня", "подруга", "крёстная", "малина"]

        if self.role in feminine_roles:
            return f"Она тебя {verb_f}."
        else:
            return f"Он тебя {verb_m}."


async def iam_command(update: Update, context: CallbackContext):
    user = update.effective_user # тг бот вернёт нам юзера отправившего комманду
    user_id = str(user.id)
    args = context.args # тг бот нам вернёт массив со словами пользователя

    if not args:
        await update.message.reply_text("Напиши кто ты. Пример: /iam мама")
        return

    role = " ".join(args).strip().lower() # получаем роль в нижнем регистре и в строку всё

    # если пользователя ещё нет в файле, создаю его профиль
    if user_id not in users:
        users[user_id] = UserProfile(user_id)

    users[user_id].role = role
    savee_state()

    await update.message.reply_text(f"Запомнил! Ты теперь - {role}.") # шаблон тг ответа я взяла из библиотеки тг


async def talk_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    message_text = update.message.text[len("/talk "):].strip()

    # Получает или создаёт профиль пользователя
    user_profile = users.get(user_id)
    if not user_profile:
        role = state["roles"].get(user_id)
        user_profile = UserProfile(user_id, role=role)
        users[user_id] = user_profile

    # Описание пользователя в начало истории, чтобы Саша понял
    if len(user_profile.history) == 0:
        user_profile.add_to_history(user_profile.prompt_frag())

    # Добавляет в историю сообщение пользователя
    if message_text:
        user_profile.add_to_history(f"{user_profile.display_name()}: {message_text}") #имя показывает и текст
    else:
        user_profile.add_to_history(f"{user_profile.display_name()} молчит.")

    # Промпт
    prompt = user_profile.get_prompt()

    # Ответ от модели
    reply = await generate(user_profile, prompt)

    # Ответ Саши в историю
    user_profile.add_to_history(f"Саша: {reply}")
    savee_state()

    # Ответ в чат
    await update.message.reply_text(reply)

async def action(update: Update, context: CallbackContext, action_name: str):
    user = update.effective_user
    user_id = str(user.id)

    # Найдём или создадим профиль пользователя
    user_profile = users.get(user_id)
    if not user_profile:
        role = state["roles"].get(user_id)
        user_profile = UserProfile(user_id, role=role)
        users[user_id] = user_profile

    # Глаголы в м.р. и ж.р. для каждого действия, чтобы не путался бот
    verbs = {
        "feed": ("покормил", "покормила"),
        "hug": ("обнял", "обняла"),
        "play": ("позвал играть", "позвала играть"),
        "praise": ("похвалил", "похвалила"),
        "sleep": ("уложил спать", "уложила спать")
    }

    if action_name not in verbs:
        await update.message.reply_text("Это действие пока не поддерживается.")
        return

    verb_m, verb_f = verbs[action_name]

    # Персонализированное начало
    action_intro = user_profile.action_phrase(verb_m, verb_f)
    prompt = f"{action_intro} Саша, говорит в ответ:"

    # Получаем ответ от модели
    reply = await generate(user_profile, prompt)

    await update.message.reply_text(reply)

    # Обновим время действия
    state["last_actions"][action_name] = datetime.now()
    savee_state()

async def feed_command(update: Update, context: CallbackContext):
    await action(update, context, "feed")

async def hug_command(update: Update, context: CallbackContext):
    await action(update, context, "hug")

async def play_command(update: Update, context: CallbackContext):
    await action(update, context, "play")

async def praise_command(update: Update, context: CallbackContext):
    await action(update, context, "praise")

async def sleep_command(update: Update, context: CallbackContext):
    await action(update, context, "sleep")


from pymorphy2 import MorphAnalyzer
morph = MorphAnalyzer()

def lemmatize(text):
    words = text.lower().split()
    return [morph.parse(w)[0].normal_form for w in words if any(c.isalnum() for c in w)]

class MemoryEntity:
    def __init__(self, key, text, author):
        self.key = key
        self.text = text
        self.author = author
        self.key_lemmas = set(lemmatize(self.normalize_text(key)))

    @staticmethod
    def normalize_text(text: str) -> str:
        import re
        return re.sub(r"[^\w\s\+\-\*/=]", "", text.lower().replace("ё", "е"))

    def as_prompt(self) -> str:
        return f"{self.author} сказал, что '{self.key}' - это {self.text}."

class MemoryManager:
    def __init__(self):
        self.entries = []

    def add(self, key, text, author):
        self.entries.append(MemoryEntity(key, text, author))

    def find_best_fact(self, query):
        query_lemmas = set(lemmatize(query))
        best_entry = None
        best_score = 0

        for entry in self.entries:
            common = query_lemmas & entry.key_lemmas
            score = len(common) / (len(entry.key_lemmas) + 1)
            if score > best_score:
                best_score = score
                best_entry = entry

        if best_score >= 0.3 and best_entry:
            return best_entry
        return None

memory_manager = MemoryManager()

# При загрузке состояния загружаю все записи
for norm_key, entry in state["memory_dict"].items():
    memory_manager.add(entry["original_key"], entry["text"], entry["from"])

async def teach_command(update: Update, context: CallbackContext):
    user = update.effective_user
    user_id = str(user.id)
    message_text = update.message.text.partition(" ")[2].strip()

    if ":" not in message_text:
        await update.message.reply_text("Формат: /teach <ключ>: <объяснение>\nПример: /teach луна: это большая лампа в небе")
        return

    key, value = map(str.strip, message_text.split(":", 1))

    if len(value.split()) > 20:
        await update.message.reply_text("Слишком сложно. Объясни проще, как для Саши.")
        return

    user_profile = users.get(user_id)
    if not user_profile:
        name = state["known_users"].get(user_id)
        role = state["roles"].get(user_id)
        user_profile = UserProfile(user_id, role=role)
        users[user_id] = user_profile

    normalized_key = MemoryEntity.normalize_text(key)
    who = user_profile.display_name()

    # Добавим в память
    memory_manager.add(key, value, who)

    # Сохраним в state
    state["memory_dict"][normalized_key] = {
        "original_key": key,
        "text": value,
        "from": who
    }

    savee_state()

    await update.message.reply_text(
        f"Саша запомнил, что {key} - это: {value} (от {who})"
    )




async def generate(user_profile: UserProfile, prompt_text: str) -> str:
    headers = {
        "Authorization": f"Bearer {TOGETHER_key}",
        "Content-Type": "application/json"
    }

    def buildpeople_prompt(current_user: UserProfile):
        lines = []

        for profile in users.values():
            # Пропускаем текущего собеседника
            if profile.user_id == current_user.user_id:
                continue

            # Пропускаем маму и папу
            if profile.role in ["мама", "папа"]:
                continue

            if profile.role:
                lines.append(profile.role)

        if lines:
            return "Так же ты знаешь этих людей: " + ", ".join(lines) + "."
        return ""

    known_people = buildpeople_prompt(user_profile)
    parent_info = user_profile.prompt_frag()

    # Базовый системный промпт
    system_prompt = (
        "Ты - Саша, маленький ребёнок 6 лет. Ты сын папы Миши и мамы Люды.\n"
        "Ты не говоришь и не додумываешь, что сказал пользователь. Только свои мысли и эмоции. Отвечаешь только от своего имени - от Саши. \n" 
        "Папа Миша - большой, добрый, сильный, любит еду и защищает семью.\n"
        "Мама Люда - умная, немного странная, строптивая, но очень любит тебя.\n"
        "Никаких технических фраз, извинений, примечаний или перевода. Только детская речь от Саши.\n"
        
        "Ты не любишь учиться слишком долго - быстро устаёшь, отвлекаешься, иногда лениваясь. Но если тебя хвалят - ты стараешься.\n"
        "Ты обожаешь играть. Ты можешь баловаться, шалить, обижаться. \n"
        "Ты сильно привязан к родителям. Хочешь быть храбрым, но иногда боишься.\n"
        "Если тебя любят - ты счастлив. Если тебя долго не кормят или не обнимают - ты начинаешь грустить.\n"
        f"{known_people}\n",
        f"{parent_info}\n",

        "!!! Важно: ты должен говорить ТОЛЬКО на русском языке. Это строгое правило.\n"
        "Если ты используешь английский - это ошибка. Ты всегда отвечаешь на ЧИСТОМ русском языке.\n"
    )

    # Получаем профиль пользователя
    prompt_history = user_profile.get_prompt()
    fact = memory_manager.find_best_fact(prompt_text)

    if fact:
        print(f"Использовано знание: '{fact.key}' от {fact.author}")
        prompt_history += f"\nСаша это помнит:\n{fact.as_prompt()}"



    # Собираем запрос к Тугезер АИ
    full_prompt = prompt_history + "\n" + prompt_text

    # Собираем запрос и задаём параметры
    data = {
        "model": "mistralai/Mixtral-8x7B-Instruct-v0.1",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": full_prompt}
        ],
        "max_tokens": 100,
        "temperature": 0.9,
        "top_p": 0.95,
        "stop": ["</s>"]
    }
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(TOGETHER_url, headers=headers, json=data)
            response_data = response.json()
            if response.status_code == 200:
                return response_data["choices"][0]["message"]["content"].strip()

            elif response.status_code == 500:
                print("Mixtral вернул 500 :(((((. Пробуем Mistral-7B")
                data["model"] = "mistralai/Mistral-7B-Instruct-v0.2"
                try:
                    response = await client.post(TOGETHER_url, headers=headers, json=data)
                    response_data = response.json()
                    if response.status_code == 200:
                        return response_data["choices"][0]["message"]["content"].strip()
                    else:
                        print(f" Ответ от Mistral тоже не получен: {response.text}")
                        return "Саша задумался... Попробуй ещё раз позже."
                except Exception as e2:
                    print(f" Ошибка при повторном запросе: {e2}")
                    return "Саша не может ответить - что-то сломалось."

            else:
                print(f"Ошибка от Together AI: {response.text}")
                return "Прости, я не смог ответить."
    except Exception as e:
        print(f"Ошибка при запросе: {e}")
        return "У Саши что-то сломалось :("


# старт - база

async def start_command(update: Update, context: CallbackContext):
    chat_id = update.effective_chat.id
    if state["chat_id"] is None:
        state["chat_id"] = chat_id
    elif state["chat_id"] != chat_id:
        state["chat_id"] = chat_id

    user = update.effective_user
    if user:
        state["known_users"][str(user.id)] = user.first_name

    commands_info = (
        "/talk – поговорить\n"
        "/feed – покормить\n"
        "/hug – обнять\n"
        "/play – поиграть\n"
        "/teach – чему-то научить\n"
        "/memory – показывает всё, чему Саша научился.\n"
        "/praise – похвалить\n"
        "/sleep – уложить спать\n"
        "/iam – Представиться ребёнку"

    )
    welcome_text = f"Привет! Меня зовут Саша. Мой возраст 6 лет. Я ещё маленький, я люблю играть :)\n" \
                   f"Доступные команды:\n{commands_info}"
    await update.message.reply_text(welcome_text)
    savee_state()

async def status_command(update: Update, context: CallbackContext):
    now = datetime.now()
    status_lines = []

    thresholds = {
        "feed": 6,
        "hug": 6,
        "play": 12,
        "praise": 12,
        "sleep": 18
    }

    for need in ["feed", "hug", "play", "praise", "sleep"]:
        last_time = state["last_actions"].get(need)
        if not last_time:
            status = "!!! не выполнялось"
        else:
            if isinstance(last_time, str):
                last_time = datetime.fromisoformat(last_time)
            hours_passed = (now - last_time).total_seconds() / 3600

            if hours_passed >= thresholds[need]:
                status = f"! давно не выполнялось ({int(hours_passed)} ч)"
            else:
                status = f"OK! в порядке ({int(hours_passed)} ч назад)"

        status_lines.append(f"{need.capitalize()}: {status}")

    await update.message.reply_text(" Состояние Саши:\n" + "\n".join(status_lines))

async def check_needs(application):
    now = datetime.now()
    warnings = []

    critical_needs = {
        "feed": 6,   # если не кормили больше 6 часов
        "hug": 6     # если не обнимали больше 6 часов
    }

    user_id = "system"
    role = "система"
    user_profile = users.get(user_id)

    if not user_profile:
        user_profile = UserProfile(user_id, role)
        users[user_id] = user_profile

    for need, threshold in critical_needs.items():
        last_time = state["last_actions"].get(need)
        if not last_time:
            last_time = now - timedelta(hours=threshold + 1)
        elif isinstance(last_time, str):
            last_time = datetime.fromisoformat(last_time)

        hours_passed = (now - last_time).total_seconds() / 3600
        if hours_passed >= threshold:
            warnings.append(need)

    if warnings and state.get("chat_id"):
        prompt = "Саша грустит. Он чувствует, что:"
        if "feed" in warnings:
            prompt += " его давно не кормили"
        if "hug" in warnings:
            if "feed" in warnings:
                prompt += " и"
            prompt += " его давно не обнимали"
        prompt += ". Что он скажет?"

        reply = await generate(user_profile, prompt)
        await application.bot.send_message(chat_id=state["chat_id"], text=reply)


from telegram.ext import Application

async def periodic_check(app: Application):
    while True:
        await check_needs(app)
        await asyncio.sleep(1800)  # 30 минут

# Всё собрали, теперь запуск бота
async def main():
    loade_state()
    app = ApplicationBuilder().token(BOT_token).build()

    app.add_handler(CommandHandler("iam", iam_command))
    app.add_handler(CommandHandler("start", start_command))

    # Зарегистрировать хендлеры для команд

    app.add_handler(CommandHandler("talk", talk_command))

    app.add_handler(CommandHandler("feed", feed_command))
    app.add_handler(CommandHandler("hug", hug_command))
    app.add_handler(CommandHandler("play", play_command))
    app.add_handler(CommandHandler("praise", praise_command))
    app.add_handler(CommandHandler("sleep", sleep_command))


    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("teach", teach_command))
    #app.add_handler(CommandHandler("memory", memory_command))
    #app.add_handler(CommandHandler("help_teach", help_teach_command))

    app.job_queue.run_once(lambda _: asyncio.create_task(periodic_check(app)), when=1)

    print("Бот запущен. Ожидание команд...")

    await app.run_polling()


if __name__ == "__main__":
    import asyncio
    import nest_asyncio

    nest_asyncio.apply()
    asyncio.get_event_loop().run_until_complete(main())
