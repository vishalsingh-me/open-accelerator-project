"""Risk scoring and policy decisions for IncidentIQ+ command plans."""

from __future__ import annotations

from typing import Any, Dict, List


DANGEROUS_PATTERNS = ["kubectl delete", " rm -rf", "rm -rf", "chmod 777", "secret", "secrets", "kubectl exec"]
SAFE_PREFIXES = ["kubectl get", "kubectl describe", "kubectl logs", "kubectl top", "journalctl", "docker ps"]
APPROVAL_PREFIXES = ["kubectl rollout restart", "kubectl set resources", "kubectl set image", "kubectl cordon"]


def _classify(command: str, requires_approval: bool) -> str:
    normalized = command.strip().lower()
    if any(pattern in normalized for pattern in DANGEROUS_PATTERNS):
        return "Dangerous"
    if any(normalized.startswith(prefix) for prefix in APPROVAL_PREFIXES):
        return "Needs Approval"
    if requires_approval:
        return "Needs Approval"
    if any(normalized.startswith(prefix) for prefix in SAFE_PREFIXES):
        return "Safe"
    return "Needs Approval"


def score(commands: Dict[str, Any]) -> Dict[str, Any]:
    command_risks: List[Dict[str, Any]] = []
    all_commands = commands.get("diagnostic_commands", []) + commands.get("remediation_commands", [])

    for item in all_commands:
        risk = _classify(item.get("command", ""), bool(item.get("requires_approval")))
        command_risks.append({
            "command": item.get("command", ""),
            "risk": risk,
            "reason": item.get("purpose", ""),
            "category": item.get("category", "unknown"),
        })

    has_dangerous = any(item["risk"] == "Dangerous" for item in command_risks)
    has_approval = any(item["risk"] == "Needs Approval" for item in command_risks)

    if has_dangerous:
        overall, decision = "High", "Blocked"
        explanation = "At least one command violates the safety policy and must not be executed."
    elif has_approval:
        overall, decision = "Medium", "Human approval required"
        explanation = "Read-only diagnostics are safe, but remediation changes require human approval."
    else:
        overall, decision = "Low", "Auto-allowed"
        explanation = "All commands are read-only diagnostics or non-mutating review actions."

    return {
        "overall_risk": overall,
        "command_risks": command_risks,
        "policy_decision": decision,
        "explanation": explanation,
    }

