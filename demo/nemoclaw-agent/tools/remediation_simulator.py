"""Shadow remediation simulation for IncidentIQ+."""

from __future__ import annotations

from typing import Any, Dict


def simulate(analysis: Dict[str, Any], root_cause: Dict[str, Any], commands: Dict[str, Any], risk: Dict[str, Any]) -> Dict[str, Any]:
    category = root_cause.get("category", "unknown")

    if risk.get("policy_decision") == "Blocked":
        return {
            "simulation_mode": "shadow",
            "status": "Failed",
            "predicted_outcome": "Plan blocked by governance policy before any production action.",
            "validation_checks": ["Remove dangerous commands", "Regenerate a read-only diagnostic plan"],
            "rollback_plan": "No rollback required because no command is executed.",
            "notes": "IncidentIQ+ never executes blocked commands.",
        }

    if category == "memory_limit_exceeded":
        status = "Passed"
        outcome = "Expected pod restart loop stops if memory usage remains below the proposed 1Gi limit."
        checks = [
            "Confirm memory usage is below new limit after restart",
            "Verify restart count stops increasing",
            "Check readiness returns to true",
        ]
        rollback = "Restore the previous deployment resource requests and limits if memory usage remains unstable."
    elif category == "image_not_found":
        status = "Needs Review"
        outcome = "Fix likely succeeds only after the correct image repository and tag are verified."
        checks = ["Verify image exists in registry", "Confirm pull secret access", "Watch rollout status"]
        rollback = "Revert deployment image to the last known good tag."
    elif category == "container_crash_loop":
        status = "Needs Review"
        outcome = "Restart may clear transient state, but logs must confirm the crash cause first."
        checks = ["Inspect previous container logs", "Validate config and dependencies", "Watch rollout status"]
        rollback = "Undo the deployment rollout or restore the last known good configuration."
    elif category in {"readiness_probe_failed", "service_unavailable"}:
        status = "Needs Review"
        outcome = "Service recovery is expected if endpoints become ready after restart or probe correction."
        checks = ["Confirm endpoints are populated", "Verify readiness probes pass", "Check HTTP 2xx responses"]
        rollback = "Revert probe or deployment changes and route traffic to the previous healthy revision."
    elif category == "node_resource_pressure":
        status = "Needs Review"
        outcome = "Cordoning the node can reduce further pressure, but workload movement requires operator approval."
        checks = ["Confirm node pressure condition clears", "Check evicted pods", "Verify cluster capacity"]
        rollback = "Uncordon the node after pressure clears and capacity is confirmed."
    elif category == "permission_or_auth_error":
        status = "Needs Review"
        outcome = "Access correction should restore failed operations after credentials or RBAC are verified."
        checks = ["Run can-i checks", "Validate service account bindings", "Confirm audit logs stop showing denials"]
        rollback = "Revert RBAC or credential changes to the previous approved policy."
    else:
        status = "Needs Review"
        outcome = "Unknown incident should remain in diagnostic mode until stronger evidence is available."
        checks = ["Collect logs", "Collect metrics", "Review recent events"]
        rollback = "No production change recommended."

    return {
        "simulation_mode": "shadow",
        "status": status,
        "predicted_outcome": outcome,
        "validation_checks": checks,
        "rollback_plan": rollback,
        "notes": "Simulation only. No production command was executed.",
    }

