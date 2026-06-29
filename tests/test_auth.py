"""Tests for auth.py — MSAL token acquisition and cache file handling."""

import os
import stat
from unittest.mock import MagicMock, patch

import pytest

import assistant.auth as auth_mod


def test_get_token_uses_silent_cache(tmp_path, monkeypatch):
    """Returns cached token without triggering device flow when a cached account exists."""
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", tmp_path / "cache.json")

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = [{"username": "user@example.com"}]
    mock_app.acquire_token_silent.return_value = {"access_token": "cached-token"}

    with patch("msal.PublicClientApplication", return_value=mock_app):
        token = auth_mod.get_token("client-id", "tenant-id")

    assert token == "cached-token"
    mock_app.acquire_token_silent.assert_called_once()
    mock_app.initiate_device_flow.assert_not_called()


def test_get_token_falls_back_to_device_flow(tmp_path, monkeypatch):
    """Triggers interactive device flow when no cached accounts exist."""
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", tmp_path / "cache.json")

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = []
    mock_app.initiate_device_flow.return_value = {
        "user_code": "ABC123",
        "message": "Visit https://example.com and enter code ABC123",
    }
    mock_app.acquire_token_by_device_flow.return_value = {"access_token": "fresh-token"}

    with patch("msal.PublicClientApplication", return_value=mock_app), patch("builtins.print"):
        token = auth_mod.get_token("client-id", "tenant-id")

    assert token == "fresh-token"
    mock_app.initiate_device_flow.assert_called_once()


def test_get_token_raises_on_auth_failure(tmp_path, monkeypatch):
    """Raises RuntimeError when the auth result contains no access_token."""
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", tmp_path / "cache.json")

    mock_app = MagicMock()
    mock_app.get_accounts.return_value = []
    mock_app.initiate_device_flow.return_value = {"user_code": "X", "message": "..."}
    mock_app.acquire_token_by_device_flow.return_value = {
        "error": "access_denied",
        "error_description": "User denied access",
    }

    with (
        patch("msal.PublicClientApplication", return_value=mock_app),
        patch("builtins.print"),
        pytest.raises(RuntimeError, match="Authentication failed"),
    ):
        auth_mod.get_token("client-id", "tenant-id")


def test_save_cache_writes_with_owner_only_permissions(tmp_path, monkeypatch):
    """Token cache file is written with 0o600 (owner read/write only)."""
    cache_path = tmp_path / "token_cache.json"
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", cache_path)

    mock_cache = MagicMock()
    mock_cache.has_state_changed = True
    mock_cache.serialize.return_value = '{"tokens": []}'

    auth_mod._save_cache(mock_cache)

    assert cache_path.exists()
    assert stat.S_IMODE(os.stat(cache_path).st_mode) == 0o600


def test_save_cache_skips_when_unchanged(tmp_path, monkeypatch):
    """_save_cache() does not write to disk when has_state_changed is False."""
    cache_path = tmp_path / "token_cache.json"
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", cache_path)

    mock_cache = MagicMock()
    mock_cache.has_state_changed = False

    auth_mod._save_cache(mock_cache)

    assert not cache_path.exists()


def test_get_graph_token_reads_credentials_from_config(tmp_path, monkeypatch):
    """get_graph_token() extracts client_id/tenant_id from config and calls get_token."""
    monkeypatch.setattr(auth_mod, "_TOKEN_CACHE_PATH", tmp_path / "cache.json")

    cfg = {
        "microsoft": {"client_id": "my-client", "tenant_id": "my-tenant"},
        "model": "x",
        "ollama_host": "http://localhost:11434",
        "timezone": "",
    }
    with (
        patch("assistant.auth.get_token", return_value="graph-token") as mock_get_token,
        patch("assistant.config.load", return_value=cfg),
    ):
        token = auth_mod.get_graph_token()

    assert token == "graph-token"
    mock_get_token.assert_called_once_with("my-client", "my-tenant")
