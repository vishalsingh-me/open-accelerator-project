"""Run the IncidentIQ+ hackathon demo scenarios."""

from pathlib import Path
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent.loop import IncidentLoop

console = Console()


def _shorten(text: str, max_len: int = 72) -> str:
    text = str(text or "").strip()
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _count_speculative(result: dict) -> tuple[int, int]:
    specs = result.get("speculative", [])
    total = len(specs)
    correct = sum(1 for item in specs if bool(item.get("draft_was_correct", False)))
    return correct, total


def _render_summary(scenario: str, result: dict) -> None:
    severity = result.get("severity", {}).get("severity", "unknown")
    root = _shorten(result.get("root_cause", {}).get("root_cause", ""))
    commands_count = len(result.get("commands", []))
    tier1_count = len(result.get("tier1_auto", []))
    tier2_count = len(result.get("tier2_review", []))
    total_time_ms = int(result.get("total_latency_ms", 0))
    correct, total = _count_speculative(result)
    spec_pct = (correct / total * 100.0) if total else 0.0

    table = Table(title=f"Scenario Summary: {scenario}", expand=True)
    table.add_column("Scenario")
    table.add_column("Severity", justify="center")
    table.add_column("Root cause (short)")
    table.add_column("Commands", justify="right")
    table.add_column("Tier1 auto", justify="right")
    table.add_column("Tier2 review", justify="right")
    table.add_column("Spec accuracy", justify="right")
    table.add_column("Total time", justify="right")
    table.add_row(
        scenario,
        severity,
        root,
        str(commands_count),
        str(tier1_count),
        str(tier2_count),
        f"{correct}/{total} ({spec_pct:.1f}%)",
        f"{total_time_ms} ms",
    )
    console.print(table)


def main() -> None:
    """Run all demo scenarios sequentially and print headline metrics."""
    sample_dir = Path(__file__).parent / "sample_logs"
    scenarios = [
        ("pod_crash_oom", sample_dir / "pod_crash_oom.log"),
        ("service_latency_spike", sample_dir / "service_latency_spike.log"),
        ("node_disk_pressure", sample_dir / "node_disk_pressure.log"),
    ]

    loop = IncidentLoop()
    aggregate_correct = 0
    aggregate_total = 0

    console.print(
        Panel(
            "IncidentIQ+ Hackathon Demo\nRunning 3 incident scenarios sequentially",
            title="Demo Runner",
            border_style="bright_blue",
        )
    )

    for scenario_name, path in scenarios:
        logs = path.read_text(encoding="utf-8") if path.exists() else ""
        console.print(f"\n[bold cyan]Running scenario:[/bold cyan] {scenario_name}")
        result = loop.run_incident(logs)
        _render_summary(scenario_name, result)

        correct, total = _count_speculative(result)
        aggregate_correct += correct
        aggregate_total += total

    aggregate_pct = (aggregate_correct / aggregate_total * 100.0) if aggregate_total else 0.0
    headline = Table(title="Headline Stat", expand=True)
    headline.add_column("Metric")
    headline.add_column("Value", justify="right")
    headline.add_row(
        "Aggregate speculative accuracy",
        f"{aggregate_correct}/{aggregate_total} ({aggregate_pct:.1f}%)",
    )
    console.print("\n")
    console.print(headline)


if __name__ == "__main__":
    main()
