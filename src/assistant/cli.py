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

# Tool imports — each registers itself on import
from .tools import documents, notes, registry, search  # noqa: F401

app = typer.Typer(add_completion=False)
console = Console()


def _ensure_config() -> None:
    cfg_path = cfg_module.config_path()
    if not cfg_path.exists():
        console.print(
            Panel(
                f"[yellow]Config file not found.[/yellow]\n\n"
                f"Copy [bold].env.example[/bold] to:\n"
                f"  [cyan]{cfg_path}[/cyan]\n\n"
                f"and fill in your values. Running with defaults for now.",
                title="Setup",
                border_style="yellow",
            )
        )
        cfg_path.parent.mkdir(parents=True, exist_ok=True)


def _check_ollama(agent: Agent) -> None:
    if not llm.is_available(agent.model, agent.host):
        console.print(
            f"[red]Model [bold]{agent.model}[/bold] not found in Ollama at {agent.host}.[/red]\n"
            f"Run: [cyan]ollama pull {agent.model}[/cyan]",
        )
        raise typer.Exit(1)


def _run_query(agent: Agent, query: str) -> str:
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

    tools_loaded = registry.available_names()
    tool_str = ", ".join(tools_loaded) if tools_loaded else "none"

    # Single-shot mode
    if query:
        response = _run_query(agent, query)
        console.print(Markdown(response))
        return

    # Interactive REPL
    console.print(
        Panel(
            f"[bold green]Personal AI Assistant[/bold green]\n"
            f"Model: [cyan]{agent.model}[/cyan]  |  Tools: [cyan]{tool_str}[/cyan]\n\n"
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

        # Built-in REPL commands
        if user_input.lower() in ("/quit", "/exit", "/q"):
            console.print("[dim]Goodbye.[/dim]")
            break
        if user_input.lower() == "/reset":
            agent.reset()
            console.print("[dim]Conversation history cleared.[/dim]")
            continue
        if user_input.lower() == "/tools":
            names = registry.available_names()
            console.print("Available tools: " + (", ".join(names) if names else "none"))
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
