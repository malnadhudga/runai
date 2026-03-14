import argparse
import os
import sys
import time

from dotenv import load_dotenv
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from crew.core.llm_client import LLMClient
from crew.master.orchestrator import Orchestrator

console = Console()

STATUS_STYLE = {
    "pending": "dim",
    "running": "bold yellow",
    "reviewing": "bold cyan",
    "done": "bold green",
    "failed": "bold red",
    "superseded": "dim strikethrough",
}


def resolve_provider() -> tuple[str, str, str]:
    """Pick provider/model/key based on what's in .env.

    Returns:
        (provider, model, api_key)

    Raises:
        SystemExit if no key is found.
    """
    gemini_key = os.getenv("GEMINI_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    if gemini_key:
        return ("gemini", "gemma-3-4b-it", gemini_key)
    if openai_key:
        return ("openai", "gpt-4o-mini", openai_key)

    console.print("[red]No API key found.[/red] Set GEMINI_API_KEY or OPENAI_API_KEY in .env")
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


def main():
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="crew",
        description="Run a crew of AI coding agents on a goal.",
    )
    parser.add_argument("goal", nargs="?", help="The coding goal to accomplish.")
    args = parser.parse_args()

    goal = args.goal
    if not goal and not sys.stdin.isatty():
        goal = sys.stdin.read().strip()
    if not goal:
        parser.print_usage()
        sys.exit(1)

    console.print(Panel("[bold]crew[/bold]  —  multi-agent coding system", style="blue"))
    console.print(f"[bold]Goal:[/bold] {goal}\n")

    provider, model, api_key = resolve_provider()
    llm_client = LLMClient(provider=provider, model=model, api_key=api_key)

    task_rows: dict[str, dict] = {}
    live: Live | None = None

    def on_status_change(task_id: str, status: str, **kwargs) -> None:
        if task_id not in task_rows:
            description = kwargs.get("description", "")
            depends_on = kwargs.get("depends_on", [])
            if description:
                task_rows[task_id] = {
                    "description": description,
                    "status": status,
                    "depends_on": depends_on or [],
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
                "depends_on": t.depends_on,
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
        sys.exit(130)
    except RuntimeError as e:
        console.print(f"\n[red]Error:[/red] {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
