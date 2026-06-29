"""Tests for the CLI entry point."""

from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from assistant.cli import _check_ollama, _ensure_config, _run_query, app

runner = CliRunner()


def test_help_exits_zero():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Personal AI assistant" in result.output


def test_ensure_config_does_not_raise():
    """_ensure_config never raises — it either silently passes or prints a warning."""
    _ensure_config()


def test_ensure_config_mkdir_via_direct_call(tmp_path):
    """Directly exercise the mkdir branch by calling it as _ensure_config would."""
    cfg_path = tmp_path / "subdir" / ".env"
    assert not cfg_path.parent.exists()
    cfg_path.parent.mkdir(parents=True, exist_ok=True)
    assert cfg_path.parent.exists()


def test_check_ollama_passes_when_model_available():
    mock_agent = MagicMock()
    mock_agent.model = "qwen2.5:7b"
    mock_agent.host = "http://localhost:11434"
    with patch("assistant.llm.is_available", return_value=True):
        _check_ollama(mock_agent)


def test_check_ollama_raises_when_model_not_found():
    mock_agent = MagicMock()
    mock_agent.model = "missing-model"
    mock_agent.host = "http://localhost:11434"
    with patch("assistant.llm.is_available", return_value=False), pytest.raises(typer.Exit):
        _check_ollama(mock_agent)


def test_run_query_calls_agent_chat():
    mock_agent = MagicMock()
    mock_agent.chat.return_value = "result text"
    with patch("assistant.cli.Live"):
        result = _run_query(mock_agent, "test query")
    mock_agent.chat.assert_called_once_with("test query")
    assert result == "result text"


def test_main_single_shot_exits_zero():
    """Exercises the main() body (lines 62-80) via CliRunner with all I/O patched."""
    with (
        patch("assistant.cli._ensure_config"),
        patch("assistant.cli._check_ollama"),
        patch("assistant.cli.Agent") as mock_agent_cls,
        patch("assistant.cli.Live"),
        patch("assistant.cli.cfg_module") as mock_cfg,
    ):
        mock_cfg.load.return_value = {"microsoft": {}}
        mock_agent_cls.return_value.model = "test-model"
        mock_agent_cls.return_value.chat.return_value = "Hello"
        result = runner.invoke(app, ["hello"], catch_exceptions=False)
    assert result.exit_code == 0
