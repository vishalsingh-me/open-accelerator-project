from __future__ import annotations

import json
import subprocess
from datetime import datetime
from typing import Any


def _run_command(cmd: list[str], timeout: int = 8) -> tuple[bool, str]:
    try:
        result = subprocess.run(
            cmd,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        stderr = result.stderr.strip() or result.stdout.strip()
        return False, stderr or "command failed"
    except FileNotFoundError:
        return False, "docker CLI not found"
    except subprocess.TimeoutExpired:
        return False, f"timeout running: {' '.join(cmd)}"


def inspect_container(service: str) -> dict[str, Any]:
    ok, output = _run_command(["docker", "inspect", service])
    if not ok:
        return {"ok": False, "error": output, "service": service}

    try:
        payload = json.loads(output)[0]
    except Exception:
        return {"ok": False, "error": "unable to parse docker inspect output", "service": service}

    state = payload.get("State", {})
    return {
        "ok": True,
        "service": service,
        "running": state.get("Running", False),
        "status": state.get("Status", "unknown"),
        "exit_code": state.get("ExitCode"),
        "started_at": state.get("StartedAt"),
        "finished_at": state.get("FinishedAt"),
    }


def is_container_running(service: str) -> bool:
    ok, output = _run_command(["docker", "inspect", "-f", "{{.State.Running}}", service])
    if not ok:
        return False
    return output.strip().lower() == "true"


def restart_container(service: str) -> tuple[bool, str]:
    return _run_command(["docker", "restart", service], timeout=15)


def fetch_container_logs(service: str, tail: int = 80) -> str:
    ok, output = _run_command(["docker", "logs", "--tail", str(tail), service], timeout=12)
    if ok and output:
        return output
    return f"{datetime.utcnow().isoformat()}Z log fetch fallback for {service}: {output}"


def analyze_log_text(log_text: str) -> dict[str, Any]:
    text = log_text.lower()
    matched = []
    checks = [
        ("oomkilled", "OOMKilled"),
        ("crashloopbackoff", "CrashLoopBackOff"),
        ("database connection timeout", "database connection timeout"),
        ("imagepullbackoff", "ImagePullBackOff"),
        ("memory usage high", "memory pressure"),
        ("instance stopped", "instance stopped"),
    ]

    for token, label in checks:
        if token in text:
            matched.append(label)

    if not matched:
        matched.append("unknown issue")

    return {
        "signals": matched,
        "signal_count": len(matched),
        "analysis_note": "Pattern scan over service logs completed.",
    }


def detect_root_cause(log_text: str) -> str:
    text = log_text.lower()

    if "oomkilled" in text or "memory pressure" in text:
        return "OOMKilled"
    if "crashloopbackoff" in text:
        return "CrashLoopBackOff"
    if "database connection timeout" in text:
        return "database connection timeout"
    if "imagepullbackoff" in text:
        return "ImagePullBackOff"
    if "instance stopped" in text:
        return "instance stopped"

    return "unknown issue"


def classify_severity(root_cause: str) -> str:
    mapping = {
        "OOMKilled": "SEV-2",
        "CrashLoopBackOff": "SEV-1",
        "database connection timeout": "SEV-1",
        "ImagePullBackOff": "SEV-2",
        "instance stopped": "SEV-2",
        "unknown issue": "SEV-3",
    }
    return mapping.get(root_cause, "SEV-3")
