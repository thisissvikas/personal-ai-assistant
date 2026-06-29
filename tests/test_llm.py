"""Tests for the LLM wrapper."""

from unittest.mock import MagicMock, patch

from langchain_ollama import ChatOllama


def test_get_chat_model_returns_chat_ollama():
    from assistant.llm import get_chat_model

    model = get_chat_model("qwen2.5:7b", "http://localhost:11434")
    assert isinstance(model, ChatOllama)
    assert model.model == "qwen2.5:7b"


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
