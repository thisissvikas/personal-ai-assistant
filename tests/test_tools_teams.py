"""Tests for the Microsoft Teams tools."""

from unittest.mock import MagicMock, patch

import assistant.tools.teams as teams_mod


def _mock_token():
    return patch("assistant.tools.teams.auth.get_graph_token", return_value="test-token")


def _httpx_response(data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


def test_find_teams_user_returns_results():
    users = [{"displayName": "Alice Smith", "mail": "alice@example.com", "id": "u-1"}]
    with _mock_token(), patch("httpx.get", return_value=_httpx_response({"value": users})):
        result = teams_mod._find_teams_user("Alice")

    assert "Alice Smith" in result
    assert "alice@example.com" in result


def test_find_teams_user_not_found():
    with _mock_token(), patch("httpx.get", return_value=_httpx_response({"value": []})):
        result = teams_mod._find_teams_user("Unknown")

    assert "No users found" in result


def test_find_teams_user_sanitizes_odata_injection():
    """Single-quote in name must be stripped before it reaches the OData $filter."""
    with _mock_token(), patch("httpx.get", return_value=_httpx_response({"value": []})) as mock_get:
        teams_mod._find_teams_user("O'Brien")

    call_params = mock_get.call_args.kwargs.get("params") or mock_get.call_args[1].get("params", {})
    assert "O'Brien" not in call_params.get("$filter", "")


def test_send_teams_dm_success():
    chat_resp = _httpx_response({"id": "chat-1"})
    msg_resp = _httpx_response({"id": "msg-1"})

    with _mock_token(), patch("httpx.post", side_effect=[chat_resp, msg_resp]):
        result = teams_mod._send_teams_dm("alice@example.com", "Hello!")

    assert "alice@example.com" in result


def test_send_channel_message_team_not_found():
    teams_data = [{"displayName": "Engineering", "id": "team-1"}]
    with _mock_token(), patch("httpx.get", return_value=_httpx_response({"value": teams_data})):
        result = teams_mod._send_channel_message("Marketing", "general", "Hi")

    assert "not found" in result.lower()
    assert "Marketing" in result


def test_send_channel_message_channel_not_found():
    teams_resp = _httpx_response({"value": [{"displayName": "Engineering", "id": "team-1"}]})
    channels_resp = _httpx_response({"value": [{"displayName": "random", "id": "ch-2"}]})

    with _mock_token(), patch("httpx.get", side_effect=[teams_resp, channels_resp]):
        result = teams_mod._send_channel_message("Engineering", "general", "Hi")

    assert "not found" in result.lower()


def test_send_channel_message_success():
    teams_resp = _httpx_response({"value": [{"displayName": "Engineering", "id": "team-1"}]})
    channels_resp = _httpx_response({"value": [{"displayName": "general", "id": "ch-1"}]})
    post_resp = _httpx_response({"id": "msg-1"})

    with (
        _mock_token(),
        patch("httpx.get", side_effect=[teams_resp, channels_resp]),
        patch("httpx.post", return_value=post_resp),
    ):
        result = teams_mod._send_channel_message("Engineering", "general", "Deploy done!")

    assert "general" in result
    assert "Engineering" in result
