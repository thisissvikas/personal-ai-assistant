"""Tests for the web-search tool."""

from unittest.mock import patch


def _get_web_search():
    from assistant.tools.search import _web_search

    return _web_search


def test_returns_formatted_results():
    web_search = _get_web_search()
    fake_results = [
        {"title": "Result One", "body": "First snippet.", "href": "https://example.com/1"},
        {"title": "Result Two", "body": "Second snippet.", "href": "https://example.com/2"},
    ]

    with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:
        instance = mock_ddgs_cls.return_value.__enter__.return_value
        instance.text.return_value = fake_results
        result = web_search("python best practices", max_results=2)

    assert "Result One" in result
    assert "First snippet." in result
    assert "https://example.com/1" in result


def test_no_results_returns_message():
    web_search = _get_web_search()

    with patch("duckduckgo_search.DDGS") as mock_ddgs_cls:
        instance = mock_ddgs_cls.return_value.__enter__.return_value
        instance.text.return_value = []
        result = web_search("query with no results")

    assert "No results found" in result
