from langchain_core.tools import BaseTool

_tools: dict[str, BaseTool] = {}


def register(tool: BaseTool) -> None:
    _tools[tool.name] = tool


def tools() -> list[BaseTool]:
    return list(_tools.values())


def available_names() -> list[str]:
    return list(_tools.keys())
