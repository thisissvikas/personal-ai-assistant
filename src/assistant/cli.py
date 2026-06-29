import typer
from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.text import Text

from . import config as cfg_module
from . import llm
from .agent import Agent

# Tool imports — each module calls registry.register() at import time.
# These must be imported BEFORE Agent() is constructed: _build_graph() captures
# registry.tools() once at compile time, so any tool imported after that point
# will not be visible to the LLM.
from .tools import documents, notes, registry, search  # noqa: F401

app = typer.Typer(add_completion=False)
console = Console()


def _ensure_config() -> None:
    """Warn the user when no .env config file is found and continue with defaults."""
    config_file_path = cfg_module.config_path()
    if not config_file_path.exists():
        console.print(
            Panel(
                f"[yellow]Config file not found.[/yellow]\n\n"
                f"Copy [bold].env.example[/bold] to [cyan]{config_file_path}[/cyan] "
                f"and fill in your values. Running with defaults for now.",
                title="Setup",
                border_style="yellow",
            )
        )


def _check_ollama(agent: Agent) -> None:
    """Abort with a helpful message if the configured model is not available in Ollama."""
    if not llm.is_available(agent.model, agent.host):
        console.print(
            f"[red]Model [bold]{agent.model}[/bold] not found in Ollama at {agent.host}.[/red]\n"
            f"Run: [cyan]ollama pull {agent.model}[/cyan]",
        )
        raise typer.Exit(1)


def _run_query(agent: Agent, query: str) -> str:
    """Send a query to the agent, showing a spinner while waiting for the response."""
    with Live(
        Spinner("dots", text=Text("Thinking…", style="dim")),
        console=console,
        transient=True,
    ):
        return agent.chat(query)


@app.command()
def main(
    query: str = typer.Argument(None, help="Single query (omit to enter interactive REPL)"),
    model: str = typer.Option(None, "--model", "-m", help="Override model from config"),
    reset: bool = typer.Option(False, "--reset", help="Clear conversation history"),
) -> None:
    """Personal AI assistant — powered by local LLMs via Ollama."""
    _ensure_config()

    # Lazy-import MS tools only if config is present (they may need auth)
    cfg = cfg_module.load()
    if cfg.get("microsoft", {}).get("client_id") not in (None, "<your-azure-app-client-id>", ""):
        from .tools import calendar, teams  # noqa: F401

    agent = Agent(model=model)

    _check_ollama(agent)

    loaded_tool_names = registry.available_names()
    tools_summary = ", ".join(loaded_tool_names) if loaded_tool_names else "none"

    # Single-shot mode
    if query:
        response = _run_query(agent, query)
        console.print(Markdown(response))
        return

    # Interactive REPL
    console.print(
        Panel(
            f"[bold green]Personal AI Assistant[/bold green]\n"
            f"Model: [cyan]{agent.model}[/cyan]  |  Tools: [cyan]{tools_summary}[/cyan]\n\n"
            f"Type [bold]/help[/bold] for commands, [bold]/quit[/bold] or Ctrl+D to exit.",
            border_style="green",
        )
    )

    while True:
        try:
            user_input = Prompt.ask("[bold blue]>[/bold blue]", console=console)
        except (EOFError, KeyboardInterrupt):
            console.print("\n[dim]Goodbye.[/dim]")
            break

        user_input = user_input.strip()
        if not user_input:
            continue

        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if user_input.lower() == "/reset":
            agent.reset()
            console.print("[dim]Conversation history cleared.[/dim]")
            continue
        if user_input.lower() == "/tools":
            tool_names = registry.available_names()
            console.print("Available tools: " + (", ".join(tool_names) if tool_names else "none"))
            continue
        if user_input.lower() == "/help":
            console.print(
                "[bold]Commands:[/bold]\n"
                "  /reset   — clear conversation history\n"
                "  /tools   — list loaded tools\n"
                "  /quit    — exit\n"
            )
            continue

        response = _run_query(agent, user_input)
        console.print(Markdown(response))
        console.print()
