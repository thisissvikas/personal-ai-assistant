"""Tests for config loading and merging."""

from pathlib import Path
from unittest.mock import patch

import yaml


def test_defaults_returned_when_no_file(tmp_path):
    """Returns hardcoded defaults when config file is absent."""
    missing = tmp_path / "nonexistent.yaml"
    with patch("assistant.config._CONFIG_PATH", missing):
        from assistant.config import load

        cfg = load()

    assert cfg["model"] == "qwen2.5:7b"
    assert cfg["ollama_host"] == "http://localhost:11434"
    assert cfg["notes"]["folder"] == "Personal"
    assert cfg["search"]["max_results"] == 5


def test_user_values_override_defaults(tmp_path):
    """User config values take precedence over defaults."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"model": "llama3.1:latest", "search": {"max_results": 10}}))

    with patch("assistant.config._CONFIG_PATH", config_file):
        from assistant.config import load

        cfg = load()

    assert cfg["model"] == "llama3.1:latest"
    assert cfg["search"]["max_results"] == 10
    assert cfg["ollama_host"] == "http://localhost:11434"


def test_deep_merge_preserves_nested_defaults(tmp_path):
    """Partial nested override keeps unspecified nested keys."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(yaml.dump({"notes": {"folder": "Work"}}))

    with patch("assistant.config._CONFIG_PATH", config_file):
        from assistant.config import load

        cfg = load()

    assert cfg["notes"]["folder"] == "Work"
    assert cfg["model"] == "qwen2.5:7b"


def test_config_path_returns_path_object():
    from assistant.config import config_path

    assert isinstance(config_path(), Path)


def test_empty_yaml_file_uses_defaults(tmp_path):
    """Empty YAML file is treated the same as no file."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("")

    with patch("assistant.config._CONFIG_PATH", config_file):
        from assistant.config import load

        cfg = load()

    assert cfg["model"] == "qwen2.5:7b"
