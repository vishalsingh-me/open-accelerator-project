"""Severity classification for IncidentIQ+."""

from __future__ import annotations

from typing import Any, Dict


def classify(analysis: Dict[str, Any], root_cause: Dict[str, Any]) -> Dict[str, Any]:
    category = root_cause.get("category", "unknown")
    restart_count = analysis.get("restart_count") or 0

    if category == "memory_limit_exceeded" and restart_count >= 5:
        severity, score = "Critical", 10
        reason = "OOMKilled workload has restarted at least five times."
        impact = "Production traffic may be unstable or unavailable until the memory limit is corrected."
    elif category == "node_resource_pressure":
        severity, score = "Critical", 10
        reason = "Node pressure can trigger evictions and affect multiple workloads."
        impact = "Multiple services may degrade or fail on the impacted node."
    elif category == "container_crash_loop" and restart_count >= 3:
        severity, score = "High", 8
        reason = "CrashLoopBackOff with repeated restarts indicates an active service failure."
        impact = "The affected service may be partially or fully unavailable."
    elif category == "image_not_found":
        severity, score = "High", 8
        reason = "ImagePullBackOff prevents the workload from starting."
        impact = "New pods cannot become ready, which may block deployment or recovery."
    elif category in {"readiness_probe_failed", "service_unavailable"}:
        severity, score = "High", 8
        reason = "Readiness or HTTP 503 failures indicate unhealthy serving path."
        impact = "Users may see errors or failed requests while endpoints remain unhealthy."
    elif category == "memory_limit_exceeded":
        severity, score = "High", 8
        reason = "The container was killed due to memory pressure."
        impact = "The affected workload may restart repeatedly under load."
    elif category == "permission_or_auth_error":
        severity, score = "Medium", 5
        reason = "Permission failures usually require configuration or credential review."
        impact = "Some automation or workload actions may fail until access is corrected."
    elif category == "unknown":
        severity, score = "Medium", 5
        reason = "Unknown incident type requires safe diagnostics before remediation."
        impact = "Impact is uncertain; collect more evidence before making changes."
    else:
        severity, score = "Low", 3
        reason = "Incident appears limited and has no critical signature."
        impact = "Localized degradation is possible."

    return {
        "severity": severity,
        "score": score,
        "reason": reason,
        "user_impact": impact,
    }

