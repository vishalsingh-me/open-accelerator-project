"""Incident report generation for IncidentIQ+."""

from __future__ import annotations

from typing import Any, Dict, List


def _commands_as_lines(commands: Dict[str, Any]) -> List[str]:
    lines = []
    for item in commands.get("diagnostic_commands", []):
        lines.append(f"- `{item['command']}` - {item['purpose']} (Safe diagnostic)")
    for item in commands.get("remediation_commands", []):
        approval = "Requires approval" if item.get("requires_approval") else "Review action"
        lines.append(f"- `{item['command']}` - {item['purpose']} ({approval})")
    return lines


def _final_status(risk: Dict[str, Any], simulation: Dict[str, Any]) -> str:
    if risk.get("policy_decision") == "Blocked" or simulation.get("status") == "Failed":
        return "Blocked by policy"
    if risk.get("policy_decision") == "Human approval required":
        if simulation.get("status") == "Passed":
            return "Safe to execute after approval"
        return "Needs human review before execution"
    return "Safe for diagnostic execution"


def generate_report(
    analysis: Dict[str, Any],
    root_cause: Dict[str, Any],
    severity: Dict[str, Any],
    commands: Dict[str, Any],
    risk: Dict[str, Any],
    simulation: Dict[str, Any],
) -> Dict[str, Any]:
    title = f"IncidentIQ+ Report: {root_cause.get('root_cause', 'Unknown Incident')}"
    evidence = root_cause.get("evidence") or analysis.get("error_signals") or ["No strong evidence detected"]
    recommended_actions = [
        "Run safe diagnostic commands first.",
        "Review risk policy before applying remediation.",
        "Use shadow simulation results to validate expected outcome.",
    ]
    final_status = _final_status(risk, simulation)
    command_lines = _commands_as_lines(commands)

    markdown = "\n".join([
        f"# {title}",
        "",
        "## Executive Summary",
        f"IncidentIQ+ classified this incident as **{severity['severity']}** with root cause **{root_cause['root_cause']}**.",
        f"{root_cause['explanation']} {severity['user_impact']}",
        "",
        "## Severity",
        f"- Level: **{severity['severity']}**",
        f"- Score: **{severity['score']}/10**",
        f"- Reason: {severity['reason']}",
        "",
        "## Evidence",
        *[f"- {item}" for item in evidence],
        "",
        "## Recommended Commands",
        *command_lines,
        "",
        "## Risk Governance",
        f"- Overall risk: **{risk['overall_risk']}**",
        f"- Policy decision: **{risk['policy_decision']}**",
        f"- Explanation: {risk['explanation']}",
        "",
        "## Shadow Simulation",
        f"- Mode: **{simulation['simulation_mode']}**",
        f"- Status: **{simulation['status']}**",
        f"- Predicted outcome: {simulation['predicted_outcome']}",
        "- Validation checks:",
        *[f"  - {check}" for check in simulation.get("validation_checks", [])],
        f"- Rollback plan: {simulation['rollback_plan']}",
        "",
        "## Final Status",
        f"**{final_status}**",
        "",
        "_IncidentIQ+ generated this report without executing remediation commands._",
    ])

    return {
        "title": title,
        "executive_summary": f"{severity['severity']} incident caused by {root_cause['root_cause']}.",
        "severity": severity,
        "root_cause": root_cause,
        "evidence": evidence,
        "recommended_actions": recommended_actions,
        "commands": commands,
        "risk_summary": risk,
        "simulation_summary": simulation,
        "final_status": final_status,
        "markdown_report": markdown,
    }
