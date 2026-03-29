import argparse
import os
import sys
import time

from dotenv import load_dotenv
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory

try:
    from prompt_toolkit.output.win32 import NoConsoleScreenBufferError
except ImportError:

    class NoConsoleScreenBufferError(BaseException):
        """Placeholder when win32 output is not available (e.g. non-Windows)."""

        pass
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from runai.core.llm_client import DEFAULT_GEMINI_MODEL, LLMClient
from runai.master.orchestrator import Orchestrator
from runai.tools.read_file import read_file
from runai.tools.list_dir import list_dir

console = Console()

STATUS_STYLE = {
    "pending": "dim",
    "running": "bold yellow",
    "reviewing": "bold cyan",
    "done": "bold green",
    "failed": "bold red",
    "superseded": "dim strikethrough",
}

MODEL_TO_PROVIDER = {
    DEFAULT_GEMINI_MODEL: "gemini",
    "gpt-4o-mini": "openai",
    "gpt-4o": "openai",
}


def resolve_provider() -> tuple[str, str, str]:
    """Pick provider/model/key from the environment.

    Gemini: local ``GEMINI_API_KEY`` wins — calls Google directly. The proxy is
    used only when that key is absent and ``RUNAI_GEMINI_PROXY_URL`` is set
    (platform key on the server).

    Returns:
        (provider, model, api_key) — ``api_key`` empty string for proxy-only
        Gemini mode.

    Raises:
        SystemExit if nothing is configured.
    """
    gemini_key = (os.getenv("GEMINI_API_KEY") or "").strip()
    gemini_proxy = (os.getenv("RUNAI_GEMINI_PROXY_URL") or "").strip()
    openai_key = (os.getenv("OPENAI_API_KEY") or "").strip()

    if gemini_key:
        return ("gemini", DEFAULT_GEMINI_MODEL, gemini_key)
    if gemini_proxy:
        return ("gemini", DEFAULT_GEMINI_MODEL, "")
    if openai_key:
        return ("openai", "gpt-4o-mini", openai_key)

    console.print(
        "[red]No API config found.[/red] Set GEMINI_API_KEY, RUNAI_GEMINI_PROXY_URL, "
        "or OPENAI_API_KEY (see .env.example)."
    )
    sys.exit(1)


def build_table(task_rows: dict[str, dict]) -> Table:
    """Build a Rich Table from current task state."""
    table = Table(title="Tasks", expand=True)
    table.add_column("ID", style="bold", width=8)
    table.add_column("Description", ratio=3)
    table.add_column("Status", width=14, justify="center")
    table.add_column("Depends On", width=14)

    for tid, info in task_rows.items():
        status = info["status"]
        style = STATUS_STYLE.get(status, "")
        table.add_row(
            tid,
            info["description"],
            f"[{style}]{status}[/{style}]",
            ", ".join(info["depends_on"]) or "—",
        )
    return table


def run_goal(llm_client: LLMClient, goal: str, console: Console) -> dict[str, dict] | None:
    """Run the full plan–dispatch–review–assemble pipeline for a goal.

    Does not sys.exit on error; returns so the REPL can continue.
    Returns the task_rows dict on success (for /status), None on error or interrupt.
    """
    task_rows: dict[str, dict] = {}
    live: Live | None = None

    def on_status_change(task_id: str, status: str, **kwargs: object) -> None:
        if task_id not in task_rows:
            description = kwargs.get("description", "")
            depends_on = kwargs.get("depends_on", [])
            if description:
                task_rows[task_id] = {
                    "description": description,
                    "status": status,
                    "depends_on": list(depends_on) if depends_on else [],
                }
            else:
                return
        else:
            task_rows[task_id]["status"] = status
        if live is not None:
            live.update(build_table(task_rows))

    orchestrator = Orchestrator(llm_client, on_status_change=on_status_change)

    try:
        with console.status("[bold cyan]Planning tasks...", spinner="dots"):
            tasks = orchestrator.planner.plan(goal)

        for t in tasks:
            task_rows[t.task_id] = {
                "description": t.description,
                "status": "pending",
                "depends_on": getattr(t, "depends_on", []) or [],
            }
        console.print(build_table(task_rows))
        console.print()

        start = time.time()

        with Live(build_table(task_rows), console=console, refresh_per_second=4) as live_ctx:
            live = live_ctx
            summary = orchestrator.run(goal, tasks=tasks)

        elapsed = time.time() - start
        console.print()
        console.print(Panel(summary, title="[bold green]Summary", expand=False))
        console.print(f"\n[dim]Completed in {elapsed:.1f}s[/dim]")

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted.[/yellow]")
        return None
    except RuntimeError as e:
        console.print(f"[red]Error:[/red] {e}")
        return None
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        return None

    return task_rows


def handle_command(
    command: str,
    console: Console,
    config: dict[str, str],
    last_task_table: Table | None,
    llm_client_ref: list[LLMClient],
) -> str | None:
    """Handle a slash command. Returns 'quit' to exit the REPL, None otherwise."""
    parts = command.strip().split()
    cmd = parts[0].lower() if parts else ""

    if cmd in ("/quit", "/exit"):
        console.print("[dim]Bye.[/dim]")
        return "quit"

    if cmd == "/clear":
        console.clear()
        return None

    if cmd == "/files":
        result = list_dir("")
        console.print(Panel(result, title="workspace/src/", expand=False))
        return None

    if cmd == "/read":
        if len(parts) < 2:
            console.print("[red]Usage:[/red] /read <file>")
            return None
        filepath = parts[1]
        content = read_file(filepath)
        if content.startswith("error:"):
            console.print(f"[red]{content}[/red]")
            return None
        ext = os.path.splitext(filepath)[1].lower()
        lang = "python" if ext == ".py" else "text"
        syntax = Syntax(content, lang, theme="monokai", line_numbers=True)
        console.print(syntax)
        return None

    if cmd == "/status":
        if last_task_table is None:
            console.print("[dim]No run yet. Run a goal first.[/dim]")
        else:
            console.print(last_task_table)
        return None

    if cmd == "/model":
        if len(parts) < 2:
            console.print(f"[green]Using {config['provider']} / {config['model']}[/green]")
            return None
        name = parts[1].strip()
        if name not in MODEL_TO_PROVIDER:
            console.print(
                f"[red]Unknown model.[/red] Supported: "
                + ", ".join(MODEL_TO_PROVIDER)
            )
            return None
        provider = MODEL_TO_PROVIDER[name]
        if provider == "gemini":
            api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
            proxy = (os.getenv("RUNAI_GEMINI_PROXY_URL") or "").strip()
            if not api_key and not proxy:
                console.print(
                    "[red]No Gemini config.[/red] Set GEMINI_API_KEY or RUNAI_GEMINI_PROXY_URL."
                )
                return None
            if not api_key:
                api_key = ""
        else:
            api_key = (os.getenv("OPENAI_API_KEY") or "").strip()
            if not api_key:
                console.print("[red]No API key for openai. Set OPENAI_API_KEY in .env.[/red]")
                return None
        config["provider"] = provider
        config["model"] = name
        config["api_key"] = api_key
        llm_client_ref[0] = LLMClient(
            provider=config["provider"],
            model=config["model"],
            api_key=config["api_key"],
        )
        console.print(f"[green]Switched to {config['provider']} / {config['model']}[/green]")
        return None

    if cmd == "/help":
        console.print(
            Panel(
                " /quit, /exit  — exit the REPL\n"
                " /clear        — clear the terminal\n"
                " /files        — list workspace/src/\n"
                " /read <file>  — show file contents\n"
                " /status       — show last task table\n"
                " /model        — show current provider/model\n"
                " /model <name> — switch model\n"
                " /help         — this message",
                title="Commands",
                expand=False,
            )
        )
        return None

    console.print(f"[red]Unknown command:[/red] {cmd}")
    return None


def _read_multiline_fallback() -> str | None:
    """Fallback multiline input using input() when prompt_toolkit has no console."""
    lines: list[str] = []
    first = True
    while True:
        try:
            prompt = "runai> " if first else "...   "
            line = input(prompt)
        except (KeyboardInterrupt, EOFError):
            return None

        if first and line.strip().startswith("/"):
            return line.strip()

        if line.strip() == "/run":
            if not lines:
                continue
            return "\n".join(lines)

        if line.strip() == "" and lines:
            return "\n".join(lines)

        if line.strip() == "/clear":
            lines.clear()
            first = True
            continue

        if line.strip() != "" or lines:
            lines.append(line)
        first = False


def read_multiline_input(session: PromptSession | None) -> str | None:
    """Read multiline input until empty line or /run. Returns None on quit/Ctrl+C/Ctrl+D."""
    if session is None:
        return _read_multiline_fallback()

    lines: list[str] = []
    first = True

    while True:
        try:
            prompt = "runai> " if first else "...   "
            line = session.prompt(prompt)
        except (KeyboardInterrupt, EOFError):
            return None

        if first and line.strip().startswith("/"):
            return line.strip()

        if line.strip() == "/run":
            if not lines:
                continue
            return "\n".join(lines)

        if line.strip() == "" and lines:
            return "\n".join(lines)

        if line.strip() == "/clear":
            lines.clear()
            first = True
            continue

        if line.strip() != "" or lines:
            lines.append(line)
        first = False


def interactive_mode(console: Console) -> None:
    """Run the interactive REPL loop."""
    console.print(
        Panel(
            "[bold]runai[/bold]  —  multi-agent coding system",
            style="blue",
            expand=False,
        )
    )
    console.print(
        "Type your goal. Press Enter twice to submit.\n"
        "Commands: /run  /clear  /files  /read <file>  /status  /model  /quit\n"
    )

    try:
        provider, model, api_key = resolve_provider()
    except SystemExit:
        return

    config: dict[str, str] = {
        "provider": provider,
        "model": model,
        "api_key": api_key,
    }
    llm_client = LLMClient(provider=provider, model=model, api_key=api_key)
    llm_client_ref: list[LLMClient] = [llm_client]

    history_path = os.path.expanduser("~/.runai_history")
    try:
        session: PromptSession | None = PromptSession(history=FileHistory(history_path))
    except NoConsoleScreenBufferError:
        session = None

    last_task_table: Table | None = None

    while True:
        try:
            raw = read_multiline_input(session)
        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Bye.[/dim]")
            break

        if raw is None:
            console.print("[dim]Bye.[/dim]")
            break

        line = raw.strip()
        if not line:
            continue

        if line.startswith("/"):
            result = handle_command(
                line, console, config, last_task_table, llm_client_ref
            )
            if result == "quit":
                break
            continue

        task_rows = run_goal(llm_client_ref[0], line, console)
        if task_rows is not None:
            last_task_table = build_table(task_rows)
        console.print("[dim]Ready for next goal.[/dim]")


def main() -> None:
    """Entry point: one-shot if args or piped stdin, else interactive REPL."""
    load_dotenv()

    if len(sys.argv) > 1 or not sys.stdin.isatty():
        parser = argparse.ArgumentParser(
            prog="runai",
            description="Run multi-agent AI coding on a goal.",
        )
        parser.add_argument("goal", nargs="?", help="The coding goal to accomplish.")
        args = parser.parse_args()

        goal = args.goal
        if not goal and not sys.stdin.isatty():
            goal = sys.stdin.read().strip()
        if not goal:
            parser.print_usage()
            sys.exit(1)

        console.print(
            Panel("[bold]runai[/bold]  —  multi-agent coding system", style="blue")
        )
        console.print(f"[bold]Goal:[/bold] {goal}\n")

        try:
            provider, model, api_key = resolve_provider()
        except SystemExit:
            raise

        llm_client = LLMClient(provider=provider, model=model, api_key=api_key)
        result = run_goal(llm_client, goal, console)
        if result is None:
            sys.exit(1)
        return

    interactive_mode(console)


if __name__ == "__main__":
    main()
