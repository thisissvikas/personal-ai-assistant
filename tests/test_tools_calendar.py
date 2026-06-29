"""Tests for the Microsoft Calendar tools."""

from unittest.mock import MagicMock, patch

import assistant.tools.calendar as cal_mod


def _mock_token():
    return patch("assistant.tools.calendar.auth.get_graph_token", return_value="test-token")


def _mock_tz(tz: str = "UTC"):
    return patch("assistant.tools.calendar._local_timezone", return_value=tz)


def _httpx_response(data: dict, status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = data
    resp.raise_for_status.return_value = None
    return resp


def test_get_today_schedule_formats_events():
    events = [
        {
            "subject": "Team Standup",
            "start": {"dateTime": "2024-07-15T09:00:00"},
            "end": {"dateTime": "2024-07-15T09:30:00"},
            "location": {"displayName": "Zoom"},
            "isOnlineMeeting": False,
            "attendees": [{"emailAddress": {"name": "Alice"}}],
        }
    ]
    with (
        _mock_token(),
        _mock_tz(),
        patch("httpx.get", return_value=_httpx_response({"value": events})),
    ):
        result = cal_mod._get_today_schedule(date="2024-07-15")

    assert "Team Standup" in result
    assert "Alice" in result
    assert "Zoom" in result


def test_get_today_schedule_no_events():
    with _mock_token(), _mock_tz(), patch("httpx.get", return_value=_httpx_response({"value": []})):
        result = cal_mod._get_today_schedule(date="2024-07-15")

    assert "No events" in result


def test_create_meeting_returns_summary():
    created_event = {"id": "ev1", "webLink": "https://outlook.office.com/calendar/event/ev1"}
    with (
        _mock_token(),
        _mock_tz(),
        patch("httpx.post", return_value=_httpx_response(created_event)),
    ):
        result = cal_mod._create_meeting(
            subject="Q3 Review",
            start="2024-07-15T14:00:00",
            end="2024-07-15T15:00:00",
            attendees=["alice@example.com"],
        )

    assert "Q3 Review" in result
    assert "outlook.office.com" in result


def test_create_meeting_warns_on_placeholder_attendees():
    created_event = {"id": "ev2", "webLink": ""}
    with (
        _mock_token(),
        _mock_tz(),
        patch("httpx.post", return_value=_httpx_response(created_event)),
    ):
        result = cal_mod._create_meeting(
            subject="Sync",
            start="2024-07-15T10:00:00",
            attendees=["Alice"],
        )

    assert "Warning" in result
    assert "Alice" in result


def test_create_meeting_no_warning_for_real_emails():
    created_event = {"id": "ev3", "webLink": ""}
    with (
        _mock_token(),
        _mock_tz(),
        patch("httpx.post", return_value=_httpx_response(created_event)),
    ):
        result = cal_mod._create_meeting(
            subject="Demo",
            start="2024-07-15T11:00:00",
            attendees=["bob@example.com"],
        )

    assert "Warning" not in result


def test_local_timezone_uses_config_value(tmp_path, monkeypatch):
    import assistant.config as conf_mod

    env_file = tmp_path / ".env"
    env_file.write_text("PAI_TIMEZONE=America/New_York\n")
    monkeypatch.setattr(conf_mod, "_ENV_PATH", env_file)
    monkeypatch.delenv("PAI_TIMEZONE", raising=False)

    result = cal_mod._local_timezone()
    assert result == "America/New_York"


def test_local_timezone_falls_back_to_system():
    with (
        patch("assistant.tools.calendar.get_localzone_name", return_value="Europe/London"),
        patch(
            "assistant.config.load", return_value={"timezone": "", "model": "x", "ollama_host": "h"}
        ),
    ):
        result = cal_mod._local_timezone()
    assert result == "Europe/London"


def test_local_timezone_falls_back_to_utc_when_system_unavailable():
    with (
        patch("assistant.tools.calendar.get_localzone_name", return_value=None),
        patch(
            "assistant.config.load", return_value={"timezone": "", "model": "x", "ollama_host": "h"}
        ),
    ):
        result = cal_mod._local_timezone()
    assert result == "UTC"
