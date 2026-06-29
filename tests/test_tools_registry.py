"""Tests for the tool registry."""

import sys


def _fresh_registry():
    """Reload registry to get a clean slate between tests."""
    mods_to_remove = [k for k in sys.modules if k.startswith("assistant.tools")]
    for mod in mods_to_remove:
        del sys.modules[mod]
    from assistant.tools import registry

    return registry


def test_register_and_retrieve():
    registry = _fresh_registry()

    schema = {"type": "function", "function": {"name": "noop", "description": "test"}}
    registry.register(schema, lambda: "ok")

    assert "noop" in registry.available_names()
    assert any(s["function"]["name"] == "noop" for s in registry.schemas())


def test_execute_known_tool():
    registry = _fresh_registry()

    schema = {"type": "function", "function": {"name": "add", "description": "add two numbers"}}
    registry.register(schema, lambda x, y: x + y)

    result = registry.execute("add", {"x": 2, "y": 3})
    assert result == 5


def test_execute_unknown_tool_returns_error_string():
    registry = _fresh_registry()
    result = registry.execute("nonexistent_tool", {})
    assert "Unknown tool" in str(result)


def test_execute_catches_tool_exceptions():
    registry = _fresh_registry()

    schema = {"type": "function", "function": {"name": "boom", "description": ""}}
    registry.register(schema, lambda: 1 / 0)

    result = registry.execute("boom", {})
    assert "Tool error" in str(result)


def test_schemas_returns_all_registered():
    registry = _fresh_registry()
    for i in range(3):
        schema = {"type": "function", "function": {"name": f"tool_{i}", "description": ""}}
        registry.register(schema, lambda: None)

    names = [s["function"]["name"] for s in registry.schemas()]
    assert "tool_0" in names
    assert "tool_1" in names
    assert "tool_2" in names


def test_tool_modules_register_on_import():
    registry = _fresh_registry()
    from assistant.tools import documents, notes, search  # noqa: F401

    names = registry.available_names()
    assert "web_search" in names
    assert "create_note" in names
    assert "search_notes" in names
    assert "read_document" in names
