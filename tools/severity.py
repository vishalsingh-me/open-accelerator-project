"""LLM-based incident severity classification."""

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


def classify_severity(analysis: dict) -> dict:
    """Classify incident severity from analysis context."""
    client = VLLMClient()

    prompt = (
        "System: Classify incident severity. Return JSON: "
        "{severity: 'low|medium|high|critical', confidence: 0-1, "
        "reasoning: str, escalate: bool}\n\n"
        f"Analysis:\n{json.dumps(analysis, ensure_ascii=True)}"
    )
    response_text = client.complete_draft(prompt)
    parsed = _parse_json_object(response_text)

    severity_value = parsed.get("severity", "medium")
    if severity_value not in {"low", "medium", "high", "critical"}:
        severity_value = "medium"

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    escalate = parsed.get("escalate", False)
    if not isinstance(escalate, bool):
        escalate = str(escalate).strip().lower() in {"1", "true", "yes"}

    return {
        "severity": severity_value,
        "confidence": confidence,
        "reasoning": parsed.get("reasoning", ""),
        "escalate": escalate,
    }
