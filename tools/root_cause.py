"""LLM-driven root cause detection."""

import json

from vllm_client.client import VLLMClient


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object from model response text."""
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


def detect_root_cause(analysis: dict, severity: dict) -> dict:
    """Detect root cause from analysis and severity context."""
    client = VLLMClient()

    prompt = (
        "System: You are an SRE expert. Determine the most likely root cause. "
        "Return JSON only: {root_cause: str, contributing_factors: [str], "
        "affected_services: [str], confidence: 0-1}\n\n"
        f"Analysis:\n{json.dumps(analysis, ensure_ascii=True)}\n\n"
        f"Severity:\n{json.dumps(severity, ensure_ascii=True)}"
    )
    response_text = client.complete_large(prompt)
    parsed = _parse_json_object(response_text)

    confidence = parsed.get("confidence", 0.0)
    try:
        confidence = float(confidence)
    except (TypeError, ValueError):
        confidence = 0.0
    confidence = max(0.0, min(1.0, confidence))

    return {
        "root_cause": parsed.get("root_cause", ""),
        "contributing_factors": parsed.get("contributing_factors", []),
        "affected_services": parsed.get("affected_services", []),
        "confidence": confidence,
    }
