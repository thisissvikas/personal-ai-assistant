from langchain_core.tools import BaseTool

_tools: dict[str, BaseTool] = {}


def register(tool: BaseTool) -> None:
    """Add a tool to the registry, keyed by its name.

    Called at module level in each tool file so the tool is available as soon
    as the module is imported.
    """
    _tools[tool.name] = tool


def tools() -> list[BaseTool]:
    """Return all registered tools for binding to the LLM and ToolNode."""
    return list(_tools.values())


def available_names() -> list[str]:
    """Return the names of all currently registered tools."""
    return list(_tools.keys())


def clear() -> None:
    """Remove all registered tools. Used in tests to reset registry state between runs."""
    _tools.clear()
