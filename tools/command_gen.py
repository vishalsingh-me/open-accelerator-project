"""LLM-powered command generation for incident remediation."""

import json
from typing import Any

from vllm_client.client import VLLMClient


def _parse_json_array(text: str) -> list[dict[str, Any]]:
    """Parse a JSON array of objects from model output text."""
    if not text:
        return []

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, list):
            return [item for item in parsed if isinstance(item, dict)]
    except json.JSONDecodeError:
        pass

    start = stripped.find("[")
    end = stripped.rfind("]")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, list):
                return [item for item in parsed if isinstance(item, dict)]
        except json.JSONDecodeError:
            return []
    return []


def _risk_level_rank(risk_level: str) -> int:
    """Return sorting rank (lower is safer)."""
    mapping = {"low": 0, "medium": 1, "high": 2}
    return mapping.get(str(risk_level).lower(), 3)


def generate_commands(root_cause: dict, severity: str) -> list[dict]:
    """Generate up to five remediation commands ordered by safety."""
    client = VLLMClient()
    prompt = (
        "System: You are a Kubernetes/Linux SRE. Generate ordered remediation "
        "commands. Return JSON array: [{command: str, description: str, "
        "expected_outcome: str, reversible: bool, risk_level: "
        "'low|medium|high'}]\n\n"
        f"Severity: {severity}\n"
        f"Root cause context: {json.dumps(root_cause, ensure_ascii=True)}"
    )

    response_text = client.complete_large(prompt)
    commands_raw = _parse_json_array(response_text)

    normalized: list[dict] = []
    for item in commands_raw:
        risk_level = str(item.get("risk_level", "medium")).lower()
        if risk_level not in {"low", "medium", "high"}:
            risk_level = "medium"

        normalized.append(
            {
                "command": str(item.get("command", "")),
                "description": str(item.get("description", "")),
                "expected_outcome": str(item.get("expected_outcome", "")),
                "reversible": bool(item.get("reversible", False)),
                "risk_level": risk_level,
            }
        )

    normalized.sort(key=lambda cmd: (_risk_level_rank(cmd["risk_level"]), not cmd["reversible"]))
    return normalized[:5]
