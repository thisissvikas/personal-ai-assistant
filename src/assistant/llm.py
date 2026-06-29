import ollama
from langchain_ollama import ChatOllama


def get_chat_model(model: str, host: str = "http://localhost:11434") -> ChatOllama:
    return ChatOllama(model=model, base_url=host)


def is_available(model: str, host: str = "http://localhost:11434") -> bool:
    try:
        client = ollama.Client(host=host)
        models = client.list()
        names = [m.model for m in models.models]
        return any(n.startswith(model.split(":")[0]) for n in names)
    except Exception:
        return False
