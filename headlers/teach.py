
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
