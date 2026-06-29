from langchain_core.tools import StructuredTool

from .. import config as cfg_module
from .registry import register


def _web_search(query: str, max_results: int = 5) -> str:
    """Search DuckDuckGo and return formatted result snippets.

    Falls back to the ``PAI_SEARCH_MAX_RESULTS`` config value when
    ``max_results`` is not explicitly provided by the LLM.
    """
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "duckduckgo-search package not installed. Run: uv sync"

    cfg = cfg_module.load()
    result_limit = max_results or cfg.get("search", {}).get("max_results", 5)

    formatted_results = []
    with DDGS() as ddgs:
        for search_hit in ddgs.text(query, max_results=result_limit):
            formatted_results.append(
                f"**{search_hit['title']}**\n{search_hit['body']}\nURL: {search_hit['href']}"
            )

    if not formatted_results:
        return "No results found."

    return "\n\n---\n\n".join(formatted_results)


register(
    StructuredTool.from_function(
        func=_web_search,
        name="web_search",
        description=(
            "Search the web for up-to-date information and return a list of results "
            "with titles, snippets, and URLs. Use this when the user asks about current "
            "events, recent news, or anything outside your training knowledge."
        ),
    )
)
