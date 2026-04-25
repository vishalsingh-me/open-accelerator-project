"""LLM-powered incident log analysis."""

import json

from vllm_client.client import VLLMClient


def _parse_json_object(text: str) -> dict:
    """Parse a JSON object from raw model text."""
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


def analyze_logs(log_text: str) -> dict:
    """Analyze infrastructure logs and return structured JSON output."""
    client = VLLMClient()

    prompt = (
        "System: You are an SRE expert. Analyze these infrastructure logs. "
        "Return JSON only: {anomalies: [str], error_patterns: [str], "
        "affected_components: [str], timeline: [str], raw_summary: str}\n\n"
        f"Logs:\n{log_text}"
    )
    response_text = client.complete_large(prompt)
    parsed = _parse_json_object(response_text)

    return {
        "anomalies": parsed.get("anomalies", []),
        "error_patterns": parsed.get("error_patterns", []),
        "affected_components": parsed.get("affected_components", []),
        "timeline": parsed.get("timeline", []),
        "raw_summary": parsed.get("raw_summary", ""),
    }
