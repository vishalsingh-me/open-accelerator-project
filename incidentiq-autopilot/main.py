from __future__ import annotations

import argparse
import os

from rich.console import Console
from rich.panel import Panel

from agent import IncidentIQAgent


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IncidentIQ Autopilot")
    parser.add_argument(
        "--scenario",
        choices=["oom", "crashloop", "db_timeout", "instance_stopped"],
        help="Run one scenario workflow and exit.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=int(os.getenv("MONITOR_INTERVAL", "3")),
        help="Monitor loop poll interval seconds.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    console = Console()

    console.print(
        Panel.fit(
            "[bold cyan]IncidentIQ Autopilot[/bold cyan]\n"
            "Enterprise CloudOps/SRE Agentic Control Plane",
            border_style="cyan",
        )
    )

    agent = IncidentIQAgent(monitor_interval=args.interval)

    if args.scenario:
        console.print(f"[yellow]Running scenario mode: {args.scenario}[/yellow]")
        agent.handle_scenario(args.scenario)
        return

    console.print("[green]Starting continuous monitor loop...[/green]")
    agent.monitor_loop()


if __name__ == "__main__":
    main()
