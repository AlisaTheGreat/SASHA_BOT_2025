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
