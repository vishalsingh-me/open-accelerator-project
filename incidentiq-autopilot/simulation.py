from __future__ import annotations

from datetime import datetime
from typing import Any


def shadow_simulate(action: str, service: str, root_cause: str) -> dict[str, Any]:
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%SZ")
    action_lower = action.lower()

    if "set resources" in action_lower or "change memory" in action_lower:
        expected = "Memory pressure likely reduced, but throughput/latency shifts are possible."
    elif "restart database" in action_lower:
        expected = "DB connectivity may recover, but risk of transient outage is high."
    else:
        expected = "Action impact appears moderate in shadow environment."

    fake_logs = (
        f"[{ts}] SHADOW ACTION: {action}\n"
        f"service={service}, root_cause={root_cause}\n"
        "No production mutation performed\n"
        "Synthetic KPI estimate: error rate down 18%, latency up 4% for 2 minutes\n"
    )

    return {
        "status": "shadow_complete",
        "expected_result": expected,
        "safety_note": "Simulation only. Production system remains unchanged.",
        "fake_logs": fake_logs,
    }
