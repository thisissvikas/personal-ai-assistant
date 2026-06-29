"""Tests for config loading from .env file and environment variables."""

from pathlib import Path

import assistant.config as conf_mod


def test_defaults_when_no_env_vars(tmp_path, monkeypatch):
    monkeypatch.setattr(conf_mod, "_ENV_PATH", tmp_path / "nonexistent.env")
    for var in [
        "PAI_MODEL",
        "PAI_OLLAMA_HOST",
        "PAI_NOTES_FOLDER",
        "PAI_SEARCH_MAX_RESULTS",
        "MICROSOFT_CLIENT_ID",
        "MICROSOFT_TENANT_ID",
    ]:
        monkeypatch.delenv(var, raising=False)

    cfg = conf_mod.load()
    assert cfg["model"] == "qwen2.5:7b"
    assert cfg["ollama_host"] == "http://localhost:11434"
    assert cfg["notes"]["folder"] == "Personal"
    assert cfg["search"]["max_results"] == 5


def test_env_vars_override_defaults(tmp_path, monkeypatch):
    monkeypatch.setattr(conf_mod, "_ENV_PATH", tmp_path / "nonexistent.env")
    monkeypatch.setenv("PAI_MODEL", "llama3.1:latest")
    monkeypatch.setenv("PAI_SEARCH_MAX_RESULTS", "10")

    cfg = conf_mod.load()
    assert cfg["model"] == "llama3.1:latest"
    assert cfg["search"]["max_results"] == 10
    assert cfg["ollama_host"] == "http://localhost:11434"


def test_env_file_is_loaded(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("PAI_MODEL=llama3.1:latest\nPAI_NOTES_FOLDER=Work\n")
    monkeypatch.setattr(conf_mod, "_ENV_PATH", env_file)
    monkeypatch.delenv("PAI_MODEL", raising=False)
    monkeypatch.delenv("PAI_NOTES_FOLDER", raising=False)

    cfg = conf_mod.load()
    assert cfg["model"] == "llama3.1:latest"
    assert cfg["notes"]["folder"] == "Work"


def test_env_var_takes_precedence_over_file(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("PAI_MODEL=from-file\n")
    monkeypatch.setattr(conf_mod, "_ENV_PATH", env_file)
    monkeypatch.setenv("PAI_MODEL", "from-env")

    cfg = conf_mod.load()
    assert cfg["model"] == "from-env"


def test_microsoft_defaults_to_empty_string(tmp_path, monkeypatch):
    monkeypatch.setattr(conf_mod, "_ENV_PATH", tmp_path / "nonexistent.env")
    monkeypatch.delenv("MICROSOFT_CLIENT_ID", raising=False)
    monkeypatch.delenv("MICROSOFT_TENANT_ID", raising=False)

    cfg = conf_mod.load()
    assert cfg["microsoft"]["client_id"] == ""
    assert cfg["microsoft"]["tenant_id"] == ""


def test_config_path_returns_path_object():
    assert isinstance(conf_mod.config_path(), Path)
