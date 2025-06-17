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

users = {}
