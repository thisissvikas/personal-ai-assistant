# Personal AI Assistant (`pai`)

A command-line AI assistant powered by **local LLMs via Ollama**. It automates everyday productivity tasks — scheduling Outlook meetings, sending Teams messages, taking notes in Apple Notes, searching the web, and reading documents — all from your terminal, with no data leaving your machine.

```
> what's on my calendar today?
• **Standup** [Teams]  09:00–09:15
  With: Alice, Bob, Carol

> send Alice a Teams message: I'll be 5 minutes late
Message sent to alice@company.com on Teams.

> take a note: project ideas — async search, MCP document store
Note "project ideas" created in Apple Notes (folder: Personal).
```

---

## Features

| Feature | How it works |
|---|---|
| Schedule Outlook meetings | Microsoft Graph API |
| Read today's calendar | Microsoft Graph API |
| Send Teams DMs / group / channel | Microsoft Graph API |
| Create & search Apple Notes | macOS AppleScript |
| Web search + AI summary | DuckDuckGo (no API key) |
| Brainstorm ideas | Pure LLM |
| Read local documents (PDF, md, txt) | Local file reading |

---

## Prerequisites

| Tool | Purpose | Install |
|---|---|---|
| [Ollama](https://ollama.com) | Run local LLMs | `brew install ollama` |
| [uv](https://docs.astral.sh/uv/) | Python package manager | `brew install uv` |
| Python 3.12+ | Runtime | via uv (auto-managed) |
| macOS | Apple Notes integration | Required for notes tool |

### Recommended model

```bash
ollama pull qwen2.5:7b   # best tool-calling reliability for <8B models
```

`llama3.1:latest` also works but has weaker multi-step tool chaining.

---

## Installation

```bash
# 1. Clone
git clone https://github.com/your-username/personal-ai-assistant.git
cd personal-ai-assistant

# 2. Install with uv (creates .venv automatically)
uv sync

# 3. Copy and edit config
cp .env.example .env
# → edit .env with your settings
```

### Verify installation

```bash
uv run pai --help
```

---

## Configuration

Config lives at `.env` in the project root. Copy the example and fill in your values:

```bash
cp .env.example .env
```

```ini
PAI_MODEL=qwen2.5:7b
PAI_OLLAMA_HOST=http://localhost:11434

MICROSOFT_CLIENT_ID=<your-azure-app-client-id>
MICROSOFT_TENANT_ID=<your-azure-tenant-id>

PAI_NOTES_FOLDER=Personal
PAI_SEARCH_MAX_RESULTS=5
```

All values have sensible defaults — for local-only usage (no Outlook/Teams) you can skip the `MICROSOFT_*` vars entirely. You can also override any setting with a shell environment variable, which takes precedence over `.env`. To use a different file location, set `PAI_ENV_FILE=/path/to/.env`.

### Microsoft 365 setup (Outlook + Teams)

Outlook and Teams use the **Microsoft Graph API**. You need a free Azure AD app registration (one-time, ~10 minutes):

1. Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**
2. Name: `Personal AI Assistant`, account type: *Single tenant*, redirect URI: none
3. Under **Authentication** → enable **Allow public client flows** (device code flow)
4. Under **API permissions** → **Add a permission** → **Microsoft Graph** → **Delegated** → add:
   - `Calendars.ReadWrite`
   - `Chat.ReadWrite`
   - `ChannelMessage.Send`
   - `Team.ReadBasic.All`
   - `User.Read`
   - `User.ReadBasic.All`
   - `MailboxSettings.Read`
5. Copy **Application (client) ID** and **Directory (tenant) ID** into `.env`

**First run with Microsoft tools:** `pai` will print a device-code URL. Open it, log in with your work account once — the token is cached at `~/.config/pai/token_cache.json`.

---

## Usage

### Interactive REPL (recommended)

```bash
uv run pai
```

```
> what does my day look like?
> schedule a 30-min call with bob@company.com tomorrow at 2pm, subject: Q3 planning
> send the engineering channel a message: deployment is live
> take a note: async ideas — batch search, streaming output
> search the web for best practices for Python async generators
> read ~/Downloads/spec.pdf and summarise the key risks
> brainstorm names for a new feature that does X
```

### Single-shot mode

```bash
uv run pai "what's on my calendar today?"
uv run pai --model llama3.1:latest "summarise ~/Desktop/report.pdf"
```

### REPL commands

| Command | Action |
|---|---|
| `/reset` | Clear conversation history |
| `/tools` | List currently loaded tools |
| `/help` | Show available commands |
| `/quit` | Exit |

---

## Development

### Setup

```bash
git clone https://github.com/your-username/personal-ai-assistant.git
cd personal-ai-assistant
uv sync --dev           # installs all deps including dev group
```

### Run linter / formatter

```bash
uv run ruff check .         # lint
uv run ruff check --fix .   # lint + auto-fix
uv run ruff format .        # format
uv run ruff format --check . # format check only (CI mode)
```

### Run tests

```bash
uv run pytest               # run all tests with coverage
uv run pytest -x            # stop on first failure
uv run pytest tests/test_tools_documents.py  # single file
```

Coverage report is printed to terminal and written to `coverage.xml`. The build fails if coverage drops below **50%**.

### Project structure

```
personal-ai-assistant/
├── src/
│   └── assistant/
│       ├── cli.py          # Typer CLI + interactive REPL
│       ├── agent.py        # Agent loop (LLM ↔ tools)
│       ├── llm.py          # Ollama wrapper
│       ├── config.py       # Config loader (~/.config/pai/.env)
│       ├── auth.py         # MSAL device-code OAuth for Microsoft
│       └── tools/
│           ├── registry.py     # Tool registration & dispatch
│           ├── calendar.py     # Outlook: schedule + list events
│           ├── teams.py        # Teams: DM, group chat, channel
│           ├── notes.py        # Apple Notes via AppleScript
│           ├── search.py       # DuckDuckGo web search
│           └── documents.py    # Local PDF / md / txt reader
├── tests/
├── .github/workflows/ci.yml
├── pyproject.toml          # uv + ruff + pytest + coverage config
├── .env.example
└── CLAUDE.md               # AI assistant coding conventions
```

### Adding a new tool

1. Create `src/assistant/tools/my_tool.py`
2. Define a schema dict (`TOOL_SCHEMA`) and an implementation function
3. Call `registry.register(TOOL_SCHEMA, my_function)` at module level
4. Import it in `cli.py` alongside the other tool imports

The agent loop automatically picks up any registered tool on the next run.

### CI

GitHub Actions runs on every push and pull request to `main`:

- **lint** — `ruff check` + `ruff format --check`
- **test** — `pytest` with coverage gate (50% minimum)

See `.github/workflows/ci.yml`.

---

## Privacy

- **All LLM inference is local** — no prompts leave your machine
- **Microsoft data** is fetched on-demand and never stored or logged
- **Token cache** lives at `~/.config/pai/token_cache.json` (local only)

---

## License

MIT
