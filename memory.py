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
