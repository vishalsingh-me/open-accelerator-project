"""Safe command plan generation for IncidentIQ+."""

from __future__ import annotations

from typing import Any, Dict, List


def _cmd(command: str, purpose: str, requires_approval: bool, category: str) -> Dict[str, Any]:
    return {
        "command": command,
        "purpose": purpose,
        "requires_approval": requires_approval,
        "category": category,
    }


def _resource_names(analysis: Dict[str, Any]) -> Dict[str, str]:
    pod = analysis.get("pod_name") or analysis.get("affected_resource") or "<pod-name>"
    if pod == "unknown":
        pod = "<pod-name>"
    deployment = analysis.get("deployment_name") or pod.replace("-pod", "") or "<deployment-name>"
    node = analysis.get("node_name") or "<node-name>"
    container = analysis.get("container_name") or "app"
    image = analysis.get("image_name") or "<correct-image>"
    return {"pod": pod, "deployment": deployment, "node": node, "container": container, "image": image}


def generate(analysis: Dict[str, Any], root_cause: Dict[str, Any], severity: Dict[str, Any]) -> Dict[str, Any]:
    names = _resource_names(analysis)
    platform = analysis.get("possible_platform", "unknown")
    category = root_cause.get("category", "unknown")
    diagnostic: List[Dict[str, Any]] = []
    remediation: List[Dict[str, Any]] = []

    if platform == "kubernetes" and category == "node_resource_pressure":
        diagnostic.extend([
            _cmd("kubectl get pods -o wide", "Check pod placement, readiness, restarts, and node assignment.", False, "diagnostic"),
            _cmd("kubectl get events --sort-by=.lastTimestamp", "Review recent cluster events in chronological order.", False, "diagnostic"),
            _cmd(f"kubectl describe node {names['node']}", "Inspect node pressure conditions, allocatable resources, and eviction signals.", False, "diagnostic"),
            _cmd(f"kubectl top node {names['node']}", "Measure current node resource pressure.", False, "diagnostic"),
        ])
    elif platform == "kubernetes":
        diagnostic.extend([
            _cmd(f"kubectl describe pod {names['pod']}", "Inspect pod status, events, limits, and recent state transitions.", False, "diagnostic"),
            _cmd(f"kubectl logs {names['pod']} --previous", "Review logs from the previously terminated container instance.", False, "diagnostic"),
            _cmd("kubectl get events --sort-by=.lastTimestamp", "Review recent cluster events in chronological order.", False, "diagnostic"),
            _cmd(f"kubectl get pods -o wide", "Check pod placement, readiness, restarts, and node assignment.", False, "diagnostic"),
        ])
    else:
        diagnostic.extend([
            _cmd("journalctl -u <service-name> --since '30 minutes ago'", "Inspect recent service logs.", False, "diagnostic"),
            _cmd("docker ps -a", "List containers and exit states.", False, "diagnostic"),
        ])

    if category == "memory_limit_exceeded":
        if platform == "kubernetes":
            diagnostic.append(_cmd(f"kubectl top pod {names['pod']}", "Compare current memory usage against configured limits.", False, "diagnostic"))
            remediation.append(_cmd(
                f"kubectl set resources deployment/{names['deployment']} --limits=memory=1Gi --requests=memory=512Mi",
                "Increase memory request and limit after human approval.",
                True,
                "remediation",
            ))
    elif category == "image_not_found":
        remediation.append(_cmd(
            f"kubectl set image deployment/{names['deployment']} {names['container']}=<correct-image>",
            "Update the deployment to a verified image tag after registry validation.",
            True,
            "remediation",
        ))
    elif category == "container_crash_loop":
        remediation.append(_cmd(
            f"kubectl rollout restart deployment/{names['deployment']}",
            "Restart the deployment after configuration or dependency validation.",
            True,
            "remediation",
        ))
    elif category in {"readiness_probe_failed", "service_unavailable"}:
        diagnostic.append(_cmd(f"kubectl describe endpoints {names['deployment']}", "Verify whether the service has healthy ready endpoints.", False, "diagnostic"))
        remediation.append(_cmd(
            f"kubectl rollout restart deployment/{names['deployment']}",
            "Restart the deployment if readiness failure is caused by a transient process state.",
            True,
            "remediation",
        ))
    elif category == "node_resource_pressure":
        remediation.append(_cmd(
            f"kubectl cordon {names['node']}",
            "Stop scheduling new workloads on the pressured node after human approval.",
            True,
            "remediation",
        ))
    elif category == "permission_or_auth_error":
        diagnostic.append(_cmd("kubectl auth can-i --list", "Review effective permissions for the current identity.", False, "diagnostic"))
        remediation.append(_cmd("Rotate or correct the affected service account credentials.", "Fix the access path after owner approval.", True, "remediation"))
    else:
        remediation.append(_cmd("Collect additional logs and metrics before making changes.", "Unknown incidents should not trigger automatic remediation.", False, "remediation"))

    return {
        "diagnostic_commands": diagnostic,
        "remediation_commands": remediation,
        "notes": "Commands are generated for review only. IncidentIQ+ never executes remediation commands.",
    }
