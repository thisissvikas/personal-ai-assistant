# CLAUDE.md — AI coding conventions for this project

This file is read by Claude Code at the start of every session. Follow every rule here unless the user explicitly overrides one.

---

## Project overview

`pai` is a personal CLI AI assistant built in Python 3.12+ using Ollama for local LLM inference. The assistant's tool-calling loop is in `src/assistant/agent.py`. Tools live in `src/assistant/tools/` and self-register on import via `registry.register()`.

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

1. Define a schema dict (`_SCHEMA`) in OpenAI function-calling format
2. Implement the tool as a private function (`_my_tool(...)`)
3. Call `registry.register(_SCHEMA, _my_tool)` at module level

The agent loop (`agent.py`) calls `registry.schemas()` to pass tool schemas to Ollama, and `registry.execute(name, args)` to invoke tools.

**To add a new tool:**
1. Create `src/assistant/tools/my_tool.py` following the pattern above
2. Import it in `src/assistant/cli.py` alongside the other tool imports
3. Add tests in `tests/test_tools_my_tool.py`

Do not modify the registry or agent loop when adding a tool.

---

## Agent loop

`Agent.chat(user_input)` runs up to `MAX_TOOL_ROUNDS` (8) iterations of:
1. Send messages + tool schemas to Ollama
2. If response has tool calls → execute them, append results, repeat
3. If response has text only → return it

The `Agent` class is stateful: it keeps `_history` in memory for the session. `Agent.reset()` clears it.

Never mutate `Agent._model` or `Agent._host` directly from outside the class. Pass `model=` to the constructor.

---

## Tests

Run with: `uv run pytest`

Coverage minimum: **60%**. The build fails below this.

**Rules:**
- Use `pytest` (not `unittest.TestCase`)
- Mock all external calls: Ollama (`llm.chat`), Microsoft Graph (`httpx`), subprocess (`osascript`), DuckDuckGo (`DDGS`)
- Do not make real network calls in tests
- When a tool module needs a fresh registry, delete `sys.modules` entries for `assistant.tools.*` at the start of the test
- Test file names: `tests/test_<module_name>.py`
- Test function names: `test_<what_is_being_tested>()`

---

## Microsoft Graph tools

`calendar.py` and `teams.py` require Microsoft authentication. They are only loaded when `config.yaml` has a valid `client_id`. Auth uses MSAL device code flow (`auth.py`). Never hardcode credentials — they come from `~/.config/pai/config.yaml`.

---

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on every push/PR to `main`:
1. **lint** — `ruff check` + `ruff format --check`
2. **test** — `pytest` on Python 3.12 and 3.13 with coverage gate

All CI checks must pass before merging.

---

## What NOT to do

- Do not install packages with `pip` — always use `uv add`
- Do not use `Optional[X]` or `Union[X, Y]` — use `X | None` and `X | Y`
- Do not access `agent._model` from outside the class — pass `model=` to the constructor
- Do not add `from __future__ import annotations` — we target Python 3.12+ which doesn't need it
- Do not add error handling for scenarios that can't happen
- Do not add backwards-compatibility shims
- Do not introduce LangChain, LlamaIndex, or other heavy agent frameworks — the agent loop is intentionally simple and direct
