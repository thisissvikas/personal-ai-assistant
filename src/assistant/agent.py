from typing import Any

from . import config as cfg_module
from . import llm
from .tools import registry

_SYSTEM_PROMPT = """You are a personal AI assistant running on the user's computer.
You have access to tools for:
- Reading and scheduling Outlook calendar events
- Sending Microsoft Teams messages (DM, group chat, channel)
- Creating notes in Apple Notes
- Searching the web
- Reading local documents (PDF, markdown, text)

Always be concise and direct. When the user asks you to take an action, use the appropriate tool.
For brainstorming or general questions, just respond — no tool needed.
When using tools, confirm what you did with a short summary.
"""

MAX_TOOL_ROUNDS = 8


class Agent:
    def __init__(self, model: str | None = None) -> None:
        self._cfg = cfg_module.load()
        self._model: str = model or self._cfg["model"]
        self._host: str = self._cfg["ollama_host"]
        self._history: list[dict[str, Any]] = [{"role": "system", "content": _SYSTEM_PROMPT}]

    def reset(self) -> None:
        self._history = [{"role": "system", "content": _SYSTEM_PROMPT}]

    def chat(self, user_input: str) -> str:
        self._history.append({"role": "user", "content": user_input})
        tools = registry.schemas()

        for _ in range(MAX_TOOL_ROUNDS):
            response = llm.chat(
                model=self._model,
                messages=self._history,
                tools=tools or None,
                host=self._host,
            )
            msg = response.message

            if msg.tool_calls:
                self._history.append(
                    {
                        "role": "assistant",
                        "content": msg.content or "",
                        "tool_calls": [
                            {
                                "id": tc.id if hasattr(tc, "id") else f"call_{i}",
                                "type": "function",
                                "function": {
                                    "name": tc.function.name,
                                    "arguments": tc.function.arguments,
                                },
                            }
                            for i, tc in enumerate(msg.tool_calls)
                        ],
                    }
                )

                for i, tc in enumerate(msg.tool_calls):
                    result = registry.execute(tc.function.name, dict(tc.function.arguments))
                    tool_id = tc.id if hasattr(tc, "id") else f"call_{i}"
                    self._history.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": str(result),
                        }
                    )
            else:
                text = msg.content or ""
                self._history.append({"role": "assistant", "content": text})
                return text

        return "Reached maximum tool-call rounds without a final answer."

    @property
    def model(self) -> str:
        return self._model

    @property
    def host(self) -> str:
        return self._host
