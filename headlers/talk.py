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
