import os # проверка файла состояния
import json #сохранение и загрузка состояния в файл.
import time # для отслеживания времени действий, возраста, проверок нужд.
from datetime import datetime, timedelta

from config import STATE_file, state, users
from user_profile import UserProfile

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
