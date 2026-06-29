from langchain_core.tools import StructuredTool

from .. import config as cfg_module
from .registry import register


def _web_search(query: str, max_results: int = 5) -> str:
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        return "duckduckgo-search package not installed. Run: pip install duckduckgo-search"

    cfg = cfg_module.load()
    max_r = max_results or cfg.get("search", {}).get("max_results", 5)

    results = []
    with DDGS() as ddgs:
        for r in ddgs.text(query, max_results=max_r):
            results.append(f"**{r['title']}**\n{r['body']}\nURL: {r['href']}")

    if not results:
        return "No results found."

    return "\n\n---\n\n".join(results)


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
