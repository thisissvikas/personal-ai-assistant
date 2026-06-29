from typing import Any

import ollama


def chat(
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]] | None = None,
    host: str = "http://localhost:11434",
) -> ollama.ChatResponse:
    client = ollama.Client(host=host)
    kwargs: dict[str, Any] = {"model": model, "messages": messages}
    if tools:
        kwargs["tools"] = tools
    return client.chat(**kwargs)


def is_available(model: str, host: str = "http://localhost:11434") -> bool:
    try:
        client = ollama.Client(host=host)
        models = client.list()
        names = [m.model for m in models.models]
        return any(n.startswith(model.split(":")[0]) for n in names)
    except Exception:
        return False
