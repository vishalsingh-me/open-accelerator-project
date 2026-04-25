from __future__ import annotations

from datetime import datetime

from rich.console import Console
from rich.panel import Panel


def notify_team(report: str) -> None:
    console = Console()
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    message = (
        f"IncidentIQ Autopilot Notification ({timestamp})\n"
        "Channel: #incident-response\n"
        f"{report}"
    )
    console.print(Panel(message, title="Slack-style Notification", border_style="magenta"))
