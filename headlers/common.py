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

