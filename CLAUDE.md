# CLAUDE.md — AI coding conventions for this project

This file is read by Claude Code at the start of every session. Follow every rule here unless the user explicitly overrides one.

---

## Project overview

`pai` is a personal CLI AI assistant built in Python 3.12+ using Ollama for local LLM inference via **LangGraph** and **langchain-ollama**. The agent graph is in `src/assistant/agent.py`. Tools live in `src/assistant/tools/` and self-register on import via `registry.register()`.

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
| Private functions/attrs | `_snake_case` | `_history`, `_build_graph` |
| Module-level constants | `UPPER_SNAKE_CASE` | `MAX_TOOL_ROUNDS`, `_GRAPH` |
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

The registry (`registry.py`) stores `BaseTool` objects keyed by name. `registry.clear()` removes all tools — used in tests. The agent binds all registered tools to the LLM via `.bind_tools()` and passes them to `ToolNode` for automatic execution.

**To add a new tool:**
1. Create `src/assistant/tools/my_tool.py` following the pattern above
2. Import it in `src/assistant/cli.py` alongside the other tool imports **before** `Agent()` is constructed
3. Add tests in `tests/test_tools_my_tool.py`

Do not modify the registry or agent graph when adding a tool.

**Tool registration ordering constraint**: `Agent._build_graph()` captures `registry.tools()` at compile time. Any tool module imported after `Agent()` is constructed will not be visible to the LLM.

---

## Agent graph (LangGraph)

`Agent.chat(user_input)` invokes a compiled `StateGraph` (with recursion limit `MAX_TOOL_ROUNDS = 16`) with two nodes:
1. `call_model` — calls `ChatOllama` with tools bound; returns an `AIMessage`
2. `tools` — `ToolNode` executes any tool calls in the last message

A conditional edge routes `call_model` → `tools` (when `tool_calls` are present) or → `END` (text-only response). The graph loops until the LLM produces a text response.

The `Agent` class is stateful: it keeps `_history` (a list of `BaseMessage`) in memory for the session. `Agent.reset()` clears it back to the system prompt. `chat()` passes an immutable snapshot `[*self._history, HumanMessage(...)]` to the graph so a failed invocation cannot corrupt history.

Never mutate `Agent._model` or `Agent._host` directly from outside the class. Pass `model=` to the constructor.

---

## Config (`config.py`)

`config.load()` is decorated with `@functools.lru_cache(maxsize=1)` — it reads `.env` once per process. Resolution order (highest priority first):
1. Shell environment variables
2. `.env` file at `_ENV_PATH` (default: project root `.env`, overridable via `PAI_ENV_FILE`)
3. Built-in defaults

`_resolve(key, default)` uses `is not None` comparisons so an explicitly set empty string (`KEY=`) overrides the default rather than falling through to it.

Config keys: `model`, `ollama_host`, `timezone` (`PAI_TIMEZONE` — IANA name, e.g. `Europe/London`; empty = auto-detect from OS), `microsoft.client_id`, `microsoft.tenant_id`, `notes.folder`, `search.max_results`.

---

## Auth (`auth.py`)

`get_token(client_id, tenant_id)` — full MSAL device-code flow, caches result in `~/.config/pai/token_cache.json` (written with `0o600` permissions). `get_graph_token()` — convenience wrapper that reads credentials from config; used by `calendar.py` and `teams.py` so they don't duplicate the config-loading logic.

---

## Microsoft Graph tools

`calendar.py` and `teams.py` require Microsoft authentication and are only loaded when `.env` has a valid `MICROSOFT_CLIENT_ID`. Both call `auth.get_graph_token()` — never duplicate this logic locally.

`calendar.py` uses `tzlocal.get_localzone_name()` to obtain the IANA timezone name (e.g. `"Europe/London"`, not an abbreviation like `"BST"`). `PAI_TIMEZONE` overrides this. Datetimes passed to Graph are always timezone-aware (`zoneinfo.ZoneInfo`).

Never hardcode credentials — they come from `.env` in the project root.

---

## Tests

Run with: `uv run pytest`

Coverage minimum: **60%**. The build fails below this.

**Rules:**
- Use `pytest` (not `unittest.TestCase`)
- `tests/conftest.py` has an `autouse` fixture that clears the `config.load` lru_cache before/after every test — this ensures monkeypatched `_ENV_PATH` changes take effect
- Mock all external calls: `llm.get_chat_model` (agent tests), `auth.get_graph_token` (calendar/teams), Microsoft Graph (`httpx`), subprocess (`osascript`), DuckDuckGo (`DDGS`)
- Do not make real network calls in tests
- Use `registry.clear()` to reset registry state in tests; only use `sys.modules` surgery when you need module-level registration code to re-run (e.g. `test_tool_modules_register_on_import`)
- Test file names: `tests/test_<module_name>.py`
- Test function names: `test_<what_is_being_tested>()`

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:
1. **lint** — `ruff check` + `ruff format --check`
2. **test** — `pytest` on Python 3.12 with coverage gate (60% minimum)

All CI checks must pass before merging.

---

## What NOT to do

- Do not install packages with `pip` — always use `uv add`
- Do not use `Optional[X]` or `Union[X, Y]` — use `X | None` and `X | Y`
- Do not access `agent._model` from outside the class — pass `model=` to the constructor
- Do not add `from __future__ import annotations` — we target Python 3.12+ which doesn't need it
- Do not add error handling for scenarios that can't happen
- Do not add backwards-compatibility shims
- Do not add `LlamaIndex` or other heavy agent frameworks — the project uses LangGraph; adding more frameworks creates unnecessary complexity
- Do not duplicate `_token()` logic in tool modules — call `auth.get_graph_token()` instead
- Do not use `pip install` hints in tool error messages — use `uv sync`
