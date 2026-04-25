"""LLM-assisted risk scoring for remediation actions."""

import json

from vllm_client.client import VLLMClient


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object from model output text."""
    if not text:
        return {}

    stripped = text.strip()
    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidate = stripped[start : end + 1]
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            return {}
    return {}


def score_risk(action: str, severity: str, root_cause: dict) -> float:
    """Return a risk score in [0.0, 1.0] for a proposed action."""
    client = VLLMClient()

    prompt = (
        "System: Score the risk of this action 0.0-1.0. Consider: severity, "
        "blast radius, reversibility, affected services. Return JSON: "
        "{score: float, reasoning: str, reversible: bool}\n\n"
        f"Action: {action}\n"
        f"Severity: {severity}\n"
        f"Root cause context: {json.dumps(root_cause, ensure_ascii=True)}"
    )

    response_text = client.complete_draft(prompt)
    parsed = _parse_json_object(response_text)

    score = parsed.get("score", 1.0)
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 1.0
    return max(0.0, min(1.0, score))
