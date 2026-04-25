from __future__ import annotations

import argparse
import json
from pathlib import Path

from rich.console import Console
from rich.table import Table

from tools import is_container_running, restart_container

STATE_PATH = Path(__file__).resolve().parent / "state.json"
SERVICES = ["payment-service", "order-service"]
MODES = ["normal", "chaos", "maintenance"]


def _default_state() -> dict:
    return {service: {"mode": "normal", "pending_approval": False} for service in SERVICES}


def load_state() -> dict:
    if not STATE_PATH.exists():
        state = _default_state()
        save_state(state)
        return state

    with STATE_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_state(state: dict) -> None:
    with STATE_PATH.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)


def set_mode(service: str, mode: str) -> None:
    state = load_state()
    state.setdefault(service, {"mode": "normal", "pending_approval": False})
    state[service]["mode"] = mode
    state[service]["pending_approval"] = False
    save_state(state)


def approve(service: str) -> str:
    state = load_state()
    state.setdefault(service, {"mode": "normal", "pending_approval": False})

    ok, detail = restart_container(service)
    if ok:
        state[service]["mode"] = "normal"
        state[service]["pending_approval"] = False
        save_state(state)
        return f"Approved and restarted {service}. Mode reset to normal."

    return f"Approval recorded but restart failed for {service}: {detail}"


def show_status() -> None:
    state = load_state()
    console = Console()
    table = Table(title="IncidentIQ Control State")
    table.add_column("Service", style="cyan")
    table.add_column("Mode", style="yellow")
    table.add_column("Pending Approval", style="magenta")
    table.add_column("Container Running", style="green")

    for service in SERVICES:
        entry = state.get(service, {"mode": "normal", "pending_approval": False})
        table.add_row(
            service,
            entry.get("mode", "normal"),
            str(entry.get("pending_approval", False)),
            str(is_container_running(service)),
        )
    console.print(table)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="IncidentIQ control plane commands")
    sub = parser.add_subparsers(dest="command", required=True)

    for mode in MODES:
        cmd = sub.add_parser(mode)
        cmd.add_argument("service", choices=SERVICES)

    approve_cmd = sub.add_parser("approve")
    approve_cmd.add_argument("service", choices=SERVICES)

    sub.add_parser("status")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    console = Console()

    if args.command == "status":
        show_status()
        return

    if args.command == "approve":
        message = approve(args.service)
        console.print(message)
        return

    set_mode(args.service, args.command)
    console.print(f"Set {args.service} mode -> {args.command}")


if __name__ == "__main__":
    main()
