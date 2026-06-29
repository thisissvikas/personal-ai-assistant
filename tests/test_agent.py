"""Tests for the LangGraph-based Agent class."""

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.tools import StructuredTool


def _noop_tool():
    def _noop() -> str:
        return "tool ran"

    return StructuredTool.from_function(func=_noop, name="noop", description="does nothing")


def _make_agent(model="test-model"):
    mock_bound_llm = MagicMock()
    mock_bound_llm.invoke.return_value = AIMessage(content="Hello!")

    with (
        patch(
            "assistant.config.load",
            return_value={"model": model, "ollama_host": "http://localhost:11434"},
        ),
        patch("assistant.llm.get_chat_model") as mock_get_model,
        patch("assistant.tools.registry.tools", return_value=[]),
    ):
        mock_get_model.return_value.bind_tools.return_value = mock_bound_llm
        from assistant.agent import Agent

        return Agent(), mock_bound_llm


def test_agent_uses_configured_model():
    agent, _ = _make_agent(model="qwen2.5:7b")
    assert agent.model == "qwen2.5:7b"


def test_agent_host_property():
    agent, _ = _make_agent()
    assert agent.host == "http://localhost:11434"


def test_agent_uses_explicit_model_override():
    mock_bound_llm = MagicMock()
    mock_bound_llm.invoke.return_value = AIMessage(content="Hi!")

    with (
        patch(
            "assistant.config.load",
            return_value={"model": "default-model", "ollama_host": "http://localhost:11434"},
        ),
        patch("assistant.llm.get_chat_model") as mock_get_model,
        patch("assistant.tools.registry.tools", return_value=[]),
    ):
        mock_get_model.return_value.bind_tools.return_value = mock_bound_llm
        from assistant.agent import Agent

        agent = Agent(model="override-model")

    assert agent.model == "override-model"


def test_agent_reset_clears_history():
    agent, _ = _make_agent()
    agent._history.append(HumanMessage(content="hello"))
    agent._history.append(AIMessage(content="hi"))
    assert len(agent._history) > 1

    agent.reset()
    assert len(agent._history) == 1
    assert isinstance(agent._history[0], SystemMessage)


def test_agent_chat_returns_text_response():
    agent, mock_llm = _make_agent()
    mock_llm.invoke.return_value = AIMessage(content="The answer is 42.")
    result = agent.chat("What is the meaning of life?")
    assert result == "The answer is 42."


def test_agent_appends_to_history():
    agent, mock_llm = _make_agent()
    mock_llm.invoke.return_value = AIMessage(content="Hello!")
    agent.chat("Hi there")

    types = [type(m).__name__ for m in agent._history]
    assert "HumanMessage" in types
    assert "AIMessage" in types


def test_agent_executes_tool_and_continues():
    tool = _noop_tool()

    ai_with_tool = AIMessage(
        content="",
        tool_calls=[{"id": "call1", "name": "noop", "args": {}, "type": "tool_call"}],
    )
    final_ai = AIMessage(content="Done!")

    call_count = 0

    def _fake_invoke(messages):
        nonlocal call_count
        call_count += 1
        return ai_with_tool if call_count == 1 else final_ai

    mock_bound_llm = MagicMock()
    mock_bound_llm.invoke.side_effect = _fake_invoke

    with (
        patch(
            "assistant.config.load",
            return_value={"model": "test", "ollama_host": "http://localhost:11434"},
        ),
        patch("assistant.llm.get_chat_model") as mock_get_model,
        patch("assistant.tools.registry.tools", return_value=[tool]),
    ):
        mock_get_model.return_value.bind_tools.return_value = mock_bound_llm
        from assistant.agent import Agent

        agent = Agent()

    result = agent.chat("do the thing")
    assert result == "Done!"
    assert call_count == 2
