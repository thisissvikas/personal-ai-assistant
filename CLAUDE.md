# CLAUDE.md — AI coding conventions for this project

This file is read by Claude Code at the start of every session. Follow every rule here unless the user explicitly overrides one.

---

## Project overview

`pai` is a personal CLI AI assistant built in Python 3.12+ using Ollama for local LLM inference via **LangGraph** and **LangChain Ollama**. The agent graph is in `src/assistant/agent.py`. Tools live in `src/assistant/tools/` and self-register on import via `registry.register()`.

---

## Package manager

**Always use `uv`.** Never use `pip` directly.

```bash
uv sync --dev          # install all deps (runtime + dev group)
uv add <package>       # add a runtime dependency
uv add --dev <package> # add a dev dependency
uv run pai             # run the CLI
uv run pytest          # run tests
uv run ruff check .    # lint
uv run ruff format .   # format
```

Do **not** run `pip install` or activate the virtualenv manually — uv manages it.

---

## Python version

Minimum: **Python 3.12**. Use modern syntax:
- `X | Y` union types (not `Optional[X]` or `Union[X, Y]`)
- `list[str]`, `dict[str, Any]` (not `List`, `Dict` from `typing`)
- `match` statements where appropriate

---

## Naming conventions (PEP 8)

| Kind | Convention | Example |
|---|---|---|
| Classes | `CapWords` | `Agent`, `ToolRegistry` |
| Functions & methods | `snake_case` | `get_today_schedule` |
| Private functions/attrs | `_snake_case` | `_token`, `_history` |
| Module-level constants | `UPPER_SNAKE_CASE` | `_GRAPH` |
| Module-level private vars | `_snake_case` | `_tools` |

**All class names must be `CapWords`.** There are no exceptions.

---

## Code style

This project uses **ruff** for linting and formatting. Always run before committing:

```bash
uv run ruff check --fix .
uv run ruff format .
```

Active ruff rules: `E, W, F, I, N, UP, B, C4, SIM, RUF`. Key rules to keep in mind:
- **F401**: Remove unused imports — never leave them in.
- **N8xx**: Naming — classes CapWords, functions snake_case.
- **B**: Bugbear — no mutable default args, no broad `except Exception` in critical paths.
- **I**: isort — imports auto-sorted by ruff.
- **UP**: pyupgrade — use modern Python syntax.

Line length is **100**. Strings use **double quotes**.

---

## Comments and documentation

Default to writing **no comments**. Add a comment only when the *why* is non-obvious:
- A hidden constraint or subtle invariant
- A workaround for a specific library bug
- Behaviour that would surprise a future reader

**Do not** write comments that describe what the code does — well-named identifiers already do that. **Do not** write multi-line docstrings unless the user explicitly asks for API documentation.

---

## Architecture — how tools work

Each tool module (`src/assistant/tools/*.py`) follows this pattern:

1. Implement the tool as a private function (`_my_tool(...)`) with type-annotated arguments
2. Wrap it with `StructuredTool.from_function()` from `langchain_core.tools`
3. Call `registry.register(tool)` at module level

The registry stores `BaseTool` objects. The agent binds them to the LLM via `.bind_tools()` and passes them to `ToolNode` for execution.

**To add a new tool:**
1. Create `src/assistant/tools/my_tool.py` following the pattern above
2. Import it in `src/assistant/cli.py` alongside the other tool imports
3. Add tests in `tests/test_tools_my_tool.py`

Do not modify the registry or agent graph when adding a tool.

---

## Agent graph (LangGraph)

`Agent.chat(user_input)` invokes a compiled `StateGraph` with two nodes:
1. `call_model` — calls `ChatOllama` with tools bound; returns an `AIMessage`
2. `tools` — `ToolNode` executes any tool calls in the last message

A conditional edge routes from `call_model` → `tools` (if `tool_calls` present) or → `END` (text response). The graph loops until the LLM produces a response with no tool calls.

The `Agent` class is stateful: it keeps `_history` (a list of `BaseMessage`) in memory for the session. `Agent.reset()` clears it back to the system prompt.

Never mutate `Agent._model` or `Agent._host` directly from outside the class. Pass `model=` to the constructor.

---

## Tests

Run with: `uv run pytest`

Coverage minimum: **50%**. The build fails below this.

**Rules:**
- Use `pytest` (not `unittest.TestCase`)
- Mock all external calls: `llm.get_chat_model` (for agent tests), Microsoft Graph (`httpx`), subprocess (`osascript`), DuckDuckGo (`DDGS`)
- Do not make real network calls in tests
- When a tool module needs a fresh registry, delete `sys.modules` entries for `assistant.tools.*` at the start of the test
- Test file names: `tests/test_<module_name>.py`
- Test function names: `test_<what_is_being_tested>()`

---

## Microsoft Graph tools

`calendar.py` and `teams.py` require Microsoft authentication. They are only loaded when `.env` has a valid `MICROSOFT_CLIENT_ID`. Auth uses MSAL device code flow (`auth.py`). Never hardcode credentials — they come from `.env` in the project root.

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:
1. **lint** — `ruff check` + `ruff format --check`
2. **test** — `pytest` on Python 3.12 with coverage gate (50% minimum)

All CI checks must pass before merging.

---

## What NOT to do

- Do not install packages with `pip` — always use `uv add`
- Do not use `Optional[X]` or `Union[X, Y]` — use `X | None` and `X | Y`
- Do not access `agent._model` from outside the class — pass `model=` to the constructor
- Do not add `from __future__ import annotations` — we target Python 3.12+ which doesn't need it
- Do not add error handling for scenarios that can't happen
- Do not add backwards-compatibility shims
- Do not add `LlamaIndex` or other heavy agent frameworks — we use LangGraph directly
