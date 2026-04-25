"""Terminal UI for IncidentIQ+."""

from pathlib import Path

import typer
from rich.align import Align
from rich.console import Console, Group
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.spinner import Spinner
from rich.table import Table
from rich.text import Text

from agent.loop import IncidentLoop

console = Console()


def _severity_badge(severity: str) -> Text:
    value = str(severity).lower()
    style_map = {
        "critical": "bold white on red",
        "high": "bold black on orange3",
        "medium": "bold black on yellow",
        "low": "bold white on green",
    }
    style = style_map.get(value, "bold white on grey35")
    return Text(f" {value.upper()} ", style=style)


def _read_log_input(log_file_path: str | None, log_text: str | None) -> str:
    if log_text:
        return log_text
    if log_file_path:
        return Path(log_file_path).read_text(encoding="utf-8")

    console.print(
        Panel(
            "Paste incident logs below. Submit an empty line to finish.",
            title="Log Input",
            border_style="cyan",
        )
    )
    lines: list[str] = []
    while True:
        line = Prompt.ask("")
        if not line:
            break
        lines.append(line)
    return "\n".join(lines)


def _build_results_table(
    governed_commands: list[dict], simulations: list[dict], tier1_auto: list[dict], tier2_review: list[dict], blocked: list[dict]
) -> Table:
    sim_by_command = {str(sim.get("command", "")): sim for sim in simulations}
    tier1_commands = {str(cmd.get("command", "")) for cmd in tier1_auto}
    tier2_commands = {str(cmd.get("command", "")) for cmd in tier2_review}
    blocked_commands = {str(cmd.get("command", "")) for cmd in blocked}

    table = Table(title="Remediation Commands", expand=True)
    table.add_column("Command", overflow="fold")
    table.add_column("Tier", justify="center")
    table.add_column("Risk Score", justify="right")
    table.add_column("Sim Result", justify="center")
    table.add_column("Action", justify="center")

    for cmd in governed_commands:
        command_text = str(cmd.get("command", ""))
        tier = str(cmd.get("tier", "unknown"))
        risk = float(cmd.get("risk_score", 1.0))

        sim = sim_by_command.get(command_text)
        if sim is None:
            sim_text = "[dim]-[/dim]"
        else:
            sim_text = (
                "[green]PASSED[/green]"
                if bool(sim.get("safe", False))
                else "[red]FAILED[/red]"
            )

        if command_text in blocked_commands or tier == "blocked":
            action = "[bold white on red] Blocked by policy [/bold white on red]"
        elif command_text in tier1_commands:
            action = "[bold white on green] Auto-executing [/bold white on green]"
        elif command_text in tier2_commands:
            action = "[bold black on yellow] Awaiting approval [/bold black on yellow]"
        else:
            action = "[dim]Review[/dim]"

        table.add_row(command_text, tier, f"{risk:.3f}", sim_text, action)

    return table


def run_cli(log_file_path: str = None, log_text: str = None) -> dict:
    """Run IncidentIQ+ pipeline with Rich terminal UI."""
    console.print(
        Panel(
            Align.center(
                Text("IncidentIQ+ — Agentic Incident Response", style="bold cyan")
                + Text("\n[NemoClaw] [vLLM]", style="bold magenta")
            ),
            border_style="bright_blue",
        )
    )

    logs = _read_log_input(log_file_path, log_text)
    source = f"File: {log_file_path}" if log_file_path else "Inline/pasted logs"
    console.print(Panel(source, title="Log Input", border_style="cyan"))

    step_logs: list[str] = []
    current_step = "Starting pipeline..."

    def stream_callback(message: str) -> None:
        nonlocal current_step
        current_step = message
        step_logs.append(message)

    def render_live() -> Panel:
        body = Group(
            Spinner("dots", text=f" {current_step}"),
            Text("\n".join(step_logs[-12:]) if step_logs else "Waiting for updates..."),
        )
        return Panel(body, title="Live Progress", border_style="blue")

    loop = IncidentLoop()
    with Live(render_live(), console=console, refresh_per_second=8) as live:
        result = loop.run_incident(logs, stream_callback=stream_callback)
        live.update(render_live())

    severity = result.get("severity", {})
    root = result.get("root_cause", {})
    governed = result.get("commands", [])
    tier1_auto = result.get("tier1_auto", [])
    tier2_review = result.get("tier2_review", [])
    blocked = result.get("blocked", [])
    simulations = result.get("simulations", [])
    report = str(result.get("report", ""))
    speculative = result.get("speculative", [])

    draft_correct = sum(1 for item in speculative if bool(item.get("draft_was_correct", False)))
    total_specs = len(speculative)

    console.print(Panel(_severity_badge(severity.get("severity", "unknown")), title="Severity"))
    console.print(
        Panel(
            str(root.get("root_cause", "Unknown")),
            title="Root Cause",
            border_style="magenta",
        )
    )
    console.print(_build_results_table(governed, simulations, tier1_auto, tier2_review, blocked))
    console.print(
        Panel(
            f"Draft correct {draft_correct}/{total_specs} times",
            title="Speculative Accuracy",
            border_style="green",
        )
    )
    console.print(Panel(report, title="Incident Report", border_style="bright_blue"))

    return result


def main(
    log_file: str = typer.Option(None, "--log-file", help="Path to incident log file."),
    text: str = typer.Option(None, "--text", help="Inline incident log text."),
) -> None:
    """Run IncidentIQ+ terminal UI."""
    run_cli(log_file_path=log_file, log_text=text)


if __name__ == "__main__":
    typer.run(main)
