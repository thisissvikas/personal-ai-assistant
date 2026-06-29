"""Tests for the Agent class."""

from unittest.mock import MagicMock, patch


def _make_agent(model="test-model"):
    with patch(
        "assistant.config.load",
        return_value={
            "model": model,
            "ollama_host": "http://localhost:11434",
        },
    ):
        from assistant.agent import Agent

        return Agent()


def _make_text_response(content: str) -> MagicMock:
    msg = MagicMock()
    msg.content = content
    msg.tool_calls = None
    response = MagicMock()
    response.message = msg
    return response


def test_agent_uses_configured_model():
    agent = _make_agent(model="qwen2.5:7b")
    assert agent.model == "qwen2.5:7b"


def test_agent_uses_explicit_model_override():
    with patch(
        "assistant.config.load",
        return_value={
            "model": "default-model",
            "ollama_host": "http://localhost:11434",
        },
    ):
        from assistant.agent import Agent

        agent = Agent(model="override-model")
    assert agent.model == "override-model"


def test_agent_reset_clears_history():
    agent = _make_agent()
    # Simulate one turn of history
    agent._history.append({"role": "user", "content": "hello"})
    agent._history.append({"role": "assistant", "content": "hi"})
    assert len(agent._history) > 1

    agent.reset()
    assert len(agent._history) == 1
    assert agent._history[0]["role"] == "system"


def test_agent_chat_returns_text_response():
    agent = _make_agent()
    fake_response = _make_text_response("The answer is 42.")

    with patch("assistant.llm.chat", return_value=fake_response):
        result = agent.chat("What is the meaning of life?")

    assert result == "The answer is 42."


def test_agent_appends_to_history():
    agent = _make_agent()
    fake_response = _make_text_response("Hello!")

    with patch("assistant.llm.chat", return_value=fake_response):
        agent.chat("Hi there")

    roles = [m["role"] for m in agent._history]
    assert "user" in roles
    assert "assistant" in roles


def test_agent_executes_tool_and_continues():
    agent = _make_agent()

    tool_call = MagicMock()
    tool_call.function.name = "noop_tool"
    tool_call.function.arguments = {}
    tool_call.id = "call_1"

    tool_response = MagicMock()
    tool_response.message.content = ""
    tool_response.message.tool_calls = [tool_call]

    text_response = _make_text_response("Done!")

    call_count = 0

    def fake_llm_chat(**kwargs):
        nonlocal call_count
        call_count += 1
        return tool_response if call_count == 1 else text_response

    with (
        patch("assistant.llm.chat", side_effect=fake_llm_chat),
        patch("assistant.tools.registry.execute", return_value="tool result") as mock_exec,
    ):
        result = agent.chat("Do the thing")

    assert result == "Done!"
    mock_exec.assert_called_once_with("noop_tool", {})


def test_agent_returns_fallback_after_max_rounds():
    agent = _make_agent()

    tool_call = MagicMock()
    tool_call.function.name = "noop"
    tool_call.function.arguments = {}
    tool_call.id = "c1"

    loop_response = MagicMock()
    loop_response.message.content = ""
    loop_response.message.tool_calls = [tool_call]

    with (
        patch("assistant.llm.chat", return_value=loop_response),
        patch("assistant.tools.registry.execute", return_value="ok"),
    ):
        result = agent.chat("loop forever")

    assert "maximum" in result.lower()
