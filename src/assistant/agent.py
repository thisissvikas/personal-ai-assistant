from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

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


class _State(TypedDict):
    messages: Annotated[list, add_messages]


class Agent:
    def __init__(self, model: str | None = None) -> None:
        cfg = cfg_module.load()
        self._model: str = model or cfg["model"]
        self._host: str = cfg["ollama_host"]
        self._history: list = [SystemMessage(content=_SYSTEM_PROMPT)]
        self._graph = self._build_graph()

    def _build_graph(self):
        tool_list = registry.tools()
        bound_llm = llm.get_chat_model(self._model, self._host).bind_tools(tool_list)
        tool_node = ToolNode(tool_list)

        def call_model(state: _State):
            return {"messages": [bound_llm.invoke(state["messages"])]}

        def should_continue(state: _State):
            return "tools" if state["messages"][-1].tool_calls else END

        g = StateGraph(_State)
        g.add_node("call_model", call_model)
        g.add_node("tools", tool_node)
        g.set_entry_point("call_model")
        g.add_conditional_edges("call_model", should_continue)
        g.add_edge("tools", "call_model")
        return g.compile()

    def chat(self, user_input: str) -> str:
        self._history.append(HumanMessage(content=user_input))
        result = self._graph.invoke({"messages": self._history})
        self._history = result["messages"]
        return self._history[-1].content or ""

    def reset(self) -> None:
        self._history = [SystemMessage(content=_SYSTEM_PROMPT)]

    @property
    def model(self) -> str:
        return self._model

    @property
    def host(self) -> str:
        return self._host
