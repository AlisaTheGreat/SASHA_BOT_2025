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
