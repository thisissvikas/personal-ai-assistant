"""Tests for the Apple Notes tool (mocks osascript)."""

import subprocess
from unittest.mock import MagicMock, patch


def _get_notes_fns():
    from assistant.tools.notes import _create_note, _search_notes

    return _create_note, _search_notes


def _make_completed_process(returncode=0, stdout="", stderr=""):
    proc = MagicMock(spec=subprocess.CompletedProcess)
    proc.returncode = returncode
    proc.stdout = stdout
    proc.stderr = stderr
    return proc


def test_create_note_success():
    create_note, _ = _get_notes_fns()
    with patch("subprocess.run", return_value=_make_completed_process(returncode=0)) as mock_run:
        result = create_note("My Title", "My body text")

    assert "My Title" in result
    assert "created" in result.lower()
    mock_run.assert_called_once()
    cmd = mock_run.call_args[0][0]
    assert cmd[0] == "osascript"


def test_create_note_failure_returns_error():
    create_note, _ = _get_notes_fns()
    with patch(
        "subprocess.run",
        return_value=_make_completed_process(returncode=1, stderr="AppleScript error"),
    ):
        result = create_note("Title", "Body")

    assert "Failed" in result or "failed" in result


def test_search_notes_found():
    _, search_notes = _get_notes_fns()
    with patch(
        "subprocess.run",
        return_value=_make_completed_process(
            returncode=0, stdout="Title: My Note\nSnippet: some content"
        ),
    ):
        result = search_notes("My Note")

    assert "My Note" in result


def test_search_notes_not_found():
    _, search_notes = _get_notes_fns()
    with patch("subprocess.run", return_value=_make_completed_process(returncode=0, stdout="")):
        result = search_notes("nonexistent")

    assert "No notes found" in result


def test_escape_applescript_handles_special_chars():
    from assistant.tools.notes import _escape_applescript

    assert _escape_applescript('say "hello"') == 'say \\"hello\\"'
    assert _escape_applescript("back\\slash") == "back\\\\slash"
    assert "\n" not in _escape_applescript("line1\nline2")
    assert "\r" not in _escape_applescript("line1\r\nline2")
