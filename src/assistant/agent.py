from typing import Annotated, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from . import config as cfg_module
from . import llm
from .tools import registry

MAX_TOOL_ROUNDS = 16

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
        """Load config, set up the LLM + tools, and compile the LangGraph agent graph."""
        cfg = cfg_module.load()
        self._model: str = model or cfg["model"]
        self._host: str = cfg["ollama_host"]
        self._history: list = [SystemMessage(content=_SYSTEM_PROMPT)]
        self._graph = self._build_graph()

    def _build_graph(self):
        """Build and compile the two-node ReAct graph: call_model ↔ tools.

        The graph loops until the LLM produces a response with no tool calls,
        at which point the conditional edge routes to END.
        """
        tool_list = registry.tools()
        bound_llm = llm.get_chat_model(self._model, self._host).bind_tools(tool_list)
        tool_node = ToolNode(tool_list)

        def call_model(state: _State):
            return {"messages": [bound_llm.invoke(state["messages"])]}

        def should_continue(state: _State):
            return "tools" if state["messages"][-1].tool_calls else END

        graph_builder = StateGraph(_State)
        graph_builder.add_node("call_model", call_model)
        graph_builder.add_node("tools", tool_node)
        graph_builder.set_entry_point("call_model")
        graph_builder.add_conditional_edges("call_model", should_continue)
        graph_builder.add_edge("tools", "call_model")
        return graph_builder.compile()

    def chat(self, user_input: str) -> str:
        """Send a message and return the assistant's reply.

        Builds an immutable message snapshot before invoking the graph so that
        a failed invocation cannot leave ``_history`` in a partially-mutated
        state. Stores the full updated list only on success.
        """
        result = self._graph.invoke(
            {"messages": [*self._history, HumanMessage(content=user_input)]},
            config={"recursion_limit": MAX_TOOL_ROUNDS},
        )
        self._history = result["messages"]
        return self._history[-1].content or ""

    def reset(self) -> None:
        """Clear conversation history, keeping only the system prompt."""
        self._history = [SystemMessage(content=_SYSTEM_PROMPT)]

    @property
    def model(self) -> str:
        return self._model

    @property
    def host(self) -> str:
        return self._host
