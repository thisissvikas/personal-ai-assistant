"""Tests for the Ollama LLM wrapper."""

from unittest.mock import MagicMock, patch


def test_chat_passes_model_and_messages():
    fake_response = MagicMock()
    mock_client = MagicMock()
    mock_client.chat.return_value = fake_response

    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import chat

        result = chat(model="qwen2.5:7b", messages=[{"role": "user", "content": "hi"}])

    mock_client.chat.assert_called_once()
    call_kwargs = mock_client.chat.call_args[1]
    assert call_kwargs["model"] == "qwen2.5:7b"
    assert result is fake_response


def test_chat_passes_tools_when_provided():
    mock_client = MagicMock()
    mock_client.chat.return_value = MagicMock()

    tools = [{"type": "function", "function": {"name": "noop"}}]
    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import chat

        chat(model="qwen2.5:7b", messages=[], tools=tools)

    call_kwargs = mock_client.chat.call_args[1]
    assert "tools" in call_kwargs
    assert call_kwargs["tools"] == tools


def test_chat_omits_tools_when_none():
    mock_client = MagicMock()
    mock_client.chat.return_value = MagicMock()

    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import chat

        chat(model="qwen2.5:7b", messages=[])

    call_kwargs = mock_client.chat.call_args[1]
    assert "tools" not in call_kwargs


def test_is_available_returns_true_for_known_model():
    mock_model = MagicMock()
    mock_model.model = "qwen2.5:7b"
    mock_list = MagicMock()
    mock_list.models = [mock_model]
    mock_client = MagicMock()
    mock_client.list.return_value = mock_list

    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import is_available

        assert is_available("qwen2.5:7b") is True


def test_is_available_returns_false_for_unknown_model():
    mock_model = MagicMock()
    mock_model.model = "other-model"
    mock_list = MagicMock()
    mock_list.models = [mock_model]
    mock_client = MagicMock()
    mock_client.list.return_value = mock_list

    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import is_available

        assert is_available("qwen2.5:7b") is False


def test_is_available_returns_false_on_connection_error():
    mock_client = MagicMock()
    mock_client.list.side_effect = ConnectionError("Ollama not running")

    with patch("ollama.Client", return_value=mock_client):
        from assistant.llm import is_available

        assert is_available("qwen2.5:7b") is False
