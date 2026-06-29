"""Tests for the tool registry."""

import sys

from langchain_core.tools import StructuredTool


def _fresh_registry():
    mods_to_remove = [k for k in sys.modules if k.startswith("assistant.tools")]
    for mod in mods_to_remove:
        del sys.modules[mod]
    from assistant.tools import registry

    return registry


def _make_tool(name: str) -> StructuredTool:
    fn = lambda: f"{name} ran"  # noqa: E731
    fn.__name__ = name
    return StructuredTool.from_function(func=fn, name=name, description=f"tool {name}")


def test_register_and_retrieve():
    registry = _fresh_registry()
    tool = _make_tool("noop")
    registry.register(tool)

    assert "noop" in registry.available_names()
    assert any(t.name == "noop" for t in registry.tools())


def test_tools_returns_all_registered():
    registry = _fresh_registry()
    for i in range(3):
        registry.register(_make_tool(f"tool_{i}"))

    names = [t.name for t in registry.tools()]
    assert "tool_0" in names
    assert "tool_1" in names
    assert "tool_2" in names


def test_available_names_empty_on_fresh_registry():
    registry = _fresh_registry()
    assert registry.available_names() == []


def test_tool_modules_register_on_import():
    registry = _fresh_registry()
    from assistant.tools import documents, notes, search  # noqa: F401

    names = registry.available_names()
    assert "web_search" in names
    assert "create_note" in names
    assert "search_notes" in names
    assert "read_document" in names


def test_register_overwrites_same_name():
    registry = _fresh_registry()
    registry.register(_make_tool("dup"))
    registry.register(_make_tool("dup"))

    assert registry.available_names().count("dup") == 1
