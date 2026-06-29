import ollama
from langchain_ollama import ChatOllama


def get_chat_model(model: str, host: str = "http://localhost:11434") -> ChatOllama:
    """Return a ChatOllama instance configured for the given model and Ollama host."""
    return ChatOllama(model=model, base_url=host)


def is_available(model: str, host: str = "http://localhost:11434") -> bool:
    """Return True if the model is present in the local Ollama instance.

    Matches by prefix so that 'qwen2.5' matches 'qwen2.5:7b'. Returns False
    on any connection error (e.g. Ollama not running).
    """
    try:
        client = ollama.Client(host=host)
        available_models = client.list()
        model_names = [entry.model for entry in available_models.models]
        return any(name.startswith(model.split(":")[0]) for name in model_names)
    except Exception:
        return False
