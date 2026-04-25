"""Root cause detection for IncidentIQ+."""

from __future__ import annotations

from typing import Any, Dict, List


def _has(analysis: Dict[str, Any], signal: str) -> bool:
    return signal in analysis.get("error_signals", [])


def detect(analysis: Dict[str, Any], logs: str) -> Dict[str, Any]:
    logs_lower = (logs or "").lower()
    evidence: List[str] = []

    def add(value: str) -> None:
        if value and value not in evidence:
            evidence.append(value)

    if _has(analysis, "OOMKilled") or analysis.get("exit_code") == 137:
        add("OOMKilled" if _has(analysis, "OOMKilled") else "")
        add("Exit code 137" if analysis.get("exit_code") == 137 else "")
        add(f"restart count {analysis['restart_count']}" if analysis.get("restart_count") is not None else "")
        add(f"memory limit {analysis['memory_limit']}" if analysis.get("memory_limit") else "")
        return {
            "category": "memory_limit_exceeded",
            "root_cause": "Memory Limit Exceeded",
            "confidence": "high",
            "evidence": evidence,
            "explanation": "The workload was terminated after exceeding its configured memory limit.",
        }

    if _has(analysis, "ImagePullBackOff") or "manifest unknown" in logs_lower or "not found" in logs_lower:
        add("ImagePullBackOff")
        add(analysis.get("image_name") or "")
        add("registry/image not found" if "not found" in logs_lower or "manifest unknown" in logs_lower else "")
        return {
            "category": "image_not_found",
            "root_cause": "Image Not Found or Pull Failure",
            "confidence": "high",
            "evidence": evidence,
            "explanation": "The platform cannot pull the configured container image or tag.",
        }

    if _has(analysis, "CrashLoopBackOff"):
        add("CrashLoopBackOff")
        add(f"restart count {analysis['restart_count']}" if analysis.get("restart_count") is not None else "")
        add(f"exit code {analysis['exit_code']}" if analysis.get("exit_code") is not None else "")
        return {
            "category": "container_crash_loop",
            "root_cause": "Container Crash Loop",
            "confidence": "high",
            "evidence": evidence,
            "explanation": "The container repeatedly exits and Kubernetes is backing off restarts.",
        }

    if _has(analysis, "ReadinessProbeFailed"):
        add("Readiness probe failed")
        add(f"port {analysis['port']}" if analysis.get("port") else "")
        return {
            "category": "readiness_probe_failed",
            "root_cause": "Readiness Probe Failed",
            "confidence": "high",
            "evidence": evidence,
            "explanation": "The service is not passing readiness checks, so traffic may not be routed correctly.",
        }

    if _has(analysis, "ServiceUnavailable"):
        add("HTTP 503")
        add(f"port {analysis['port']}" if analysis.get("port") else "")
        return {
            "category": "service_unavailable",
            "root_cause": "Service Unavailable",
            "confidence": "medium",
            "evidence": evidence,
            "explanation": "The service is returning 503 responses, likely because no healthy backend is available.",
        }

    if _has(analysis, "NodePressure"):
        add("Node pressure condition")
        add(analysis.get("node_name") or "")
        return {
            "category": "node_resource_pressure",
            "root_cause": "Node Resource Pressure",
            "confidence": "high",
            "evidence": evidence,
            "explanation": "The node is reporting memory or disk pressure and may evict workloads.",
        }

    if _has(analysis, "AuthPermission"):
        add("Authorization or permission error")
        return {
            "category": "permission_or_auth_error",
            "root_cause": "Permission or Authentication Error",
            "confidence": "medium",
            "evidence": evidence,
            "explanation": "The incident contains authorization, authentication, or permission failure signals.",
        }

    return {
        "category": "unknown",
        "root_cause": "Unknown",
        "confidence": "low",
        "evidence": analysis.get("detected_keywords", []),
        "explanation": "No supported incident signature was detected. Use safe diagnostics to gather more context.",
    }

