from collections.abc import Callable
from typing import Any

_tools: dict[str, tuple[dict, Callable]] = {}


def register(schema: dict, fn: Callable) -> None:
    name = schema["function"]["name"]
    _tools[name] = (schema, fn)


def schemas() -> list[dict]:
    return [schema for schema, _ in _tools.values()]


def execute(name: str, arguments: dict[str, Any]) -> Any:
    if name not in _tools:
        return f"Unknown tool: {name}"
    _, fn = _tools[name]
    try:
        return fn(**arguments)
    except Exception as e:
        return f"Tool error ({name}): {e}"


def available_names() -> list[str]:
    return list(_tools.keys())
