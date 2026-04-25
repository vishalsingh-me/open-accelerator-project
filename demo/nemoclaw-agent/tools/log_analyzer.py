"""Deterministic log analysis for IncidentIQ+."""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional


KEYWORDS = [
    "oomkilled",
    "exit code 137",
    "imagepullbackoff",
    "errimagepull",
    "crashloopbackoff",
    "readiness probe failed",
    "liveness probe failed",
    "http 503",
    "503 service unavailable",
    "memorypressure",
    "diskpressure",
    "node pressure",
    "unauthorized",
    "forbidden",
    "permission denied",
]


def _first_match(patterns: List[str], text: str, flags: int = re.IGNORECASE) -> Optional[str]:
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            return next((group for group in match.groups() if group), match.group(0)).strip()
    return None


def _int_match(patterns: List[str], text: str) -> Optional[int]:
    value = _first_match(patterns, text)
    if value is None:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _detect_platform(logs_lower: str) -> str:
    if any(term in logs_lower for term in ["kubectl", "pod/", "deployment/", "namespace", "kubelet", "openshift"]):
        return "kubernetes"
    if any(term in logs_lower for term in ["docker", "containerd", "container "]):
        return "docker"
    if any(term in logs_lower for term in ["systemd", "journalctl", "kernel:"]):
        return "linux"
    return "unknown"


def _detect_keywords(logs_lower: str) -> List[str]:
    return sorted({keyword for keyword in KEYWORDS if keyword in logs_lower})


def _detect_error_signals(logs_lower: str) -> List[str]:
    signals = []
    checks = {
        "OOMKilled": ["oomkilled", "out of memory", "memory cgroup out of memory"],
        "ExitCode137": ["exit code 137", "exitcode: 137", "exit code: 137"],
        "ImagePullBackOff": ["imagepullbackoff", "errimagepull"],
        "CrashLoopBackOff": ["crashloopbackoff", "back-off restarting failed container"],
        "ReadinessProbeFailed": ["readiness probe failed", "readiness probe"],
        "ServiceUnavailable": ["http 503", "503 service unavailable", "status=503"],
        "NodePressure": ["memorypressure", "diskpressure", "node pressure"],
        "AuthPermission": ["unauthorized", "forbidden", "permission denied"],
    }
    for signal, terms in checks.items():
        if any(term in logs_lower for term in terms):
            signals.append(signal)
    return signals


def analyze(logs: str) -> Dict[str, Any]:
    """Extract incident facts from raw infrastructure logs."""
    logs = logs or ""
    logs_lower = logs.lower()

    pod_name = _first_match([
        r"\bpod[/: ]+([a-z0-9][a-z0-9.-]+)",
        r"\bpod[=:]\s*([a-z0-9][a-z0-9.-]+)",
        r"\bname:\s*([a-z0-9][a-z0-9.-]+)",
    ], logs)
    deployment_name = _first_match([
        r"\bdeployment[/: ]+([a-z0-9][a-z0-9.-]+)",
        r"\bdeployment[=:]\s*([a-z0-9][a-z0-9.-]+)",
    ], logs)
    node_name = _first_match([
        r"\bnode[/: ]+([a-zA-Z0-9][a-zA-Z0-9.-]+)",
        r"\bnode[=:]\s*([a-zA-Z0-9][a-zA-Z0-9.-]+)",
    ], logs)
    container_name = _first_match([
        r"\bcontainer[/: ]+([a-z0-9][a-z0-9.-]+)",
        r"\bcontainer[=:]\s*([a-z0-9][a-z0-9.-]+)",
    ], logs)
    image_name = _first_match([
        r"\bimage[=:]\s*([^\s,]+)",
        r'Failed to pull image "([^"]+)"',
        r'pulling image "([^"]+)"',
    ], logs)

    restart_count = _int_match([
        r"\brestart count[:= ]+(\d+)",
        r"\brestarts?[:= ]+(\d+)",
        r"\bRestart Count:\s*(\d+)",
        r"\bRESTARTS\s+(\d+)",
    ], logs)
    exit_code = _int_match([
        r"\bexit code[:= ]+(\d+)",
        r"\bexitcode[:= ]+(\d+)",
        r"\bExit Code:\s*(\d+)",
    ], logs)
    memory_limit = _first_match([
        r"\bmemory limit[:= ]+([0-9.]+\s*[KMGT]i?B?)",
        r"\blimits\.memory[:= ]+([0-9.]+\s*[KMGT]i?B?)",
        r"\blimit[:= ]+([0-9.]+\s*[KMGT]i?B?)",
    ], logs)
    memory_usage = _first_match([
        r"\bmemory usage[:= ]+([0-9.]+\s*[KMGT]i?B?)",
        r"\busage[:= ]+([0-9.]+\s*[KMGT]i?B?)",
        r"\bused[:= ]+([0-9.]+\s*[KMGT]i?B?)",
    ], logs)
    port = _int_match([
        r"\bport[:= ]+(\d+)",
        r":(\d{2,5})/(?:tcp|udp)",
        r"http://[^:\s]+:(\d+)",
    ], logs)

    platform = _detect_platform(logs_lower)
    keywords = _detect_keywords(logs_lower)
    error_signals = _detect_error_signals(logs_lower)

    affected_resource = pod_name or deployment_name or node_name or "unknown"
    if "NodePressure" in error_signals and node_name:
        affected_resource = node_name

    summary_parts = []
    if error_signals:
        summary_parts.append("Detected " + ", ".join(error_signals))
    if affected_resource != "unknown":
        summary_parts.append(f"affecting {affected_resource}")
    if restart_count is not None:
        summary_parts.append(f"with restart count {restart_count}")
    summary = "; ".join(summary_parts) if summary_parts else "No known incident signature detected."

    return {
        "detected_keywords": keywords,
        "possible_platform": platform,
        "affected_resource": affected_resource,
        "pod_name": pod_name,
        "deployment_name": deployment_name,
        "node_name": node_name,
        "container_name": container_name,
        "error_signals": error_signals,
        "restart_count": restart_count,
        "exit_code": exit_code,
        "memory_limit": memory_limit,
        "memory_usage": memory_usage,
        "image_name": image_name,
        "port": port,
        "short_summary": summary,
    }

